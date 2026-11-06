#!/usr/bin/env python3
"""Fase 1: ingesta. Hash, metadatos, fechas, HEIC->JPG, miniaturas y keyframes.

Lee media/ (solo lectura) y escribe en catalog/. Idempotente: salta archivos
ya ingestados con el mismo tamaño y mtime.

Uso:
  python scripts/01_ingest.py --sample 50
  python scripts/01_ingest.py            # todo
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jsonschema
import pillow_heif
from PIL import Image, ImageOps

pillow_heif.register_heif_opener()

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "asset.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())

PHOTO_EXT = {".heic", ".heif", ".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".3gp"}
THUMB_MAX = 768
MIN_YEAR = 1995

FILENAME_PATTERNS = [
    # IMG_20190812_153012.jpg, VID_20190812_153012.mp4, PXL_..., con sufijos
    (re.compile(r"(?:IMG|VID|PXL|PANO)_(\d{8})_(\d{6})"), "datetime", 0.85),
    # WhatsApp: IMG-20200101-WA0007. El sufijo WA no es hora (docs/02-reglas.md).
    (re.compile(r"(?:IMG|VID|AUD|PTT)-(\d{8})-WA\d+"), "date", 0.8),
    # WhatsApp Image 2021-03-04 at 10.23.45 (PM)
    (re.compile(r"WhatsApp (?:Image|Video) (\d{4}-\d{2}-\d{2}) at (\d{1,2})\.(\d{2})\.(\d{2})(?:\s*([AP]M))?", re.I), "wa_desktop", 0.85),
]

EXIF_DATE_KEYS = [
    "EXIF:DateTimeOriginal",
    "QuickTime:CreationDate",  # iPhone: hora local con offset
    "EXIF:CreateDate",
    "XMP:DateCreated",
    "XMP:DateTimeOriginal",
    "QuickTime:CreateDate",    # UTC por especificación
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def plausible(dt):
    now = datetime.now(timezone.utc) + timedelta(days=2)
    return MIN_YEAR <= dt.year and dt <= now


def local_aware(naive):
    return naive.astimezone()


def parse_exif_date(value, key):
    if not isinstance(value, str) or value.startswith("0000"):
        return None
    m = re.match(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?\s*(Z|[+-]\d{2}:?\d{2})?", value)
    if not m:
        return None
    try:
        naive = datetime(*map(int, m.groups()[:6]))
    except ValueError:
        return None
    tz = m.group(7)
    if tz == "Z":
        return naive.replace(tzinfo=timezone.utc)
    if tz:
        sign = 1 if tz[0] == "+" else -1
        digits = tz[1:].replace(":", "")
        offset = timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
        return naive.replace(tzinfo=timezone(sign * offset))
    if key == "QuickTime:CreateDate":
        return naive.replace(tzinfo=timezone.utc)
    return local_aware(naive)


def date_from_exif(meta):
    offset = meta.get("EXIF:OffsetTimeOriginal")
    for key in EXIF_DATE_KEYS:
        value = meta.get(key)
        if key == "EXIF:DateTimeOriginal" and isinstance(value, str) and isinstance(offset, str):
            value = value + offset
        dt = parse_exif_date(value, key)
        if dt and plausible(dt):
            return dt
    return None


def date_from_filename(name):
    for rx, kind, conf in FILENAME_PATTERNS:
        m = rx.search(name)
        if not m:
            continue
        try:
            if kind == "datetime":
                naive = datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
            elif kind == "date":
                naive = datetime.strptime(m.group(1), "%Y%m%d").replace(hour=12)
            else:
                hour = int(m.group(2)) % 12 if m.group(5) else int(m.group(2))
                if m.group(5) and m.group(5).upper() == "PM":
                    hour += 12
                naive = datetime.strptime(m.group(1), "%Y-%m-%d").replace(
                    hour=hour, minute=int(m.group(3)), second=int(m.group(4)))
        except ValueError:
            continue
        dt = local_aware(naive)
        if plausible(dt):
            return dt, conf
    return None


def date_from_fs(path):
    st = os.stat(path)
    ts = min(getattr(st, "st_birthtime", st.st_mtime), st.st_mtime)
    return datetime.fromtimestamp(ts).astimezone()


def resolve_date(path, meta):
    dt = date_from_exif(meta)
    if dt:
        return dt, "exif", 0.95
    fn = date_from_filename(path.name)
    if fn:
        return fn[0], "filename", fn[1]
    return date_from_fs(path), "filesystem", 0.2


def exiftool_batch(paths):
    with tempfile.NamedTemporaryFile("w", suffix=".args", delete=False) as f:
        f.write("\n".join(str(p) for p in paths))
        argfile = f.name
    try:
        out = subprocess.run(
            ["exiftool", "-json", "-n", "-G", "-charset", "filename=utf8", "-@", argfile],
            capture_output=True, text=True)
        data = json.loads(out.stdout or "[]")
    finally:
        os.unlink(argfile)
    return {str(Path(d["SourceFile"])): d for d in data}


def ffprobe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True)
    return json.loads(out.stdout or "{}")


def orientation_of(w, h):
    if w and h and abs(w - h) / max(w, h) < 0.05:
        return "square"
    return "horizontal" if w > h else "vertical"


def is_screenshot(path, meta):
    if path.suffix.lower() != ".png":
        return False
    if any(isinstance(v, str) and "screenshot" in v.lower() for k, v in meta.items() if "UserComment" in k):
        return True
    return not meta.get("EXIF:Make")


def make_photo_outputs(path, short, catalog):
    thumbs = catalog / "thumbs"
    work = catalog / "work"
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        if path.suffix.lower() in {".heic", ".heif"}:
            work_path = work / f"{short}.jpg"
            if not work_path.exists():
                exif = im.info.get("exif")
                kwargs = {"exif": exif} if exif else {}
                im.convert("RGB").save(work_path, "JPEG", quality=92, **kwargs)
        thumb = im.convert("RGB")
        thumb.thumbnail((THUMB_MAX, THUMB_MAX))
        thumb.save(thumbs / f"{short}.jpg", "JPEG", quality=85)
    return w, h, [f"catalog/thumbs/{short}.jpg"]


def make_video_outputs(path, short, catalog, duration):
    thumbs = catalog / "thumbs"
    outs = []
    times = [duration * f for f in (0.1, 0.5, 0.9)] if duration else [0]
    scale = f"scale={THUMB_MAX}:{THUMB_MAX}:force_original_aspect_ratio=decrease"
    for i, t in enumerate(times, 1):
        out = thumbs / f"{short}_kf{i}.jpg"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
             "-vf", scale, "-map_metadata", "-1", "-q:v", "3", str(out)],
            capture_output=True)
        if out.exists():
            outs.append(f"catalog/thumbs/{out.name}")
    if not outs:
        return None, None, []
    with Image.open(ROOT / outs[len(outs) // 2]) as im:
        w, h = im.size  # ffmpeg ya aplica la rotación
    return w, h, outs


def ingest_one(path, meta, catalog):
    digest = sha256(path)
    short = digest[:16]
    ext = path.suffix.lower()
    date, date_source, conf = resolve_date(path, meta)
    tech = {
        "ext": ext,
        "make": meta.get("EXIF:Make") or meta.get("QuickTime:Make"),
        "model": meta.get("EXIF:Model") or meta.get("QuickTime:Model"),
        "has_gps": any("GPS" in k for k in meta),
    }
    asset = {
        "id": f"sha256:{digest}",
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "date": date.astimezone().isoformat(timespec="seconds"),
        "date_source": date_source,
        "date_confidence": conf,
    }
    if ext in VIDEO_EXT:
        probe = ffprobe(path)
        streams = probe.get("streams", [])
        duration = float(probe.get("format", {}).get("duration") or 0)
        w, h, outs = make_video_outputs(path, short, catalog, duration)
        if not outs:
            raise RuntimeError("ffmpeg no pudo extraer keyframes")
        asset["media_type"] = "video"
        asset["video"] = {
            "duration_s": round(duration, 2),
            "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        }
        vs = next((s for s in streams if s.get("codec_type") == "video"), {})
        tech["codec"] = vs.get("codec_name")
    else:
        w, h, outs = make_photo_outputs(path, short, catalog)
        if is_screenshot(path, meta):
            asset["media_type"] = "screenshot"
        elif ext == ".webp":
            asset["media_type"] = "graphic"
        else:
            asset["media_type"] = "photo"
    asset["orientation"] = orientation_of(w, h)
    tech.update(width=w, height=h, thumbs=outs)
    return asset, tech


def init_db(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY, path TEXT NOT NULL, data TEXT NOT NULL,
            ingested_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS tech (
            id TEXT PRIMARY KEY REFERENCES assets(id), data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS paths (
            path TEXT PRIMARY KEY, id TEXT NOT NULL REFERENCES assets(id),
            size INTEGER NOT NULL, mtime REAL NOT NULL);
    """)


def list_media(source):
    files = []
    for dirpath, _, names in os.walk(source, followlinks=True):
        for n in names:
            p = Path(dirpath) / n
            if p.suffix.lower() in PHOTO_EXT | VIDEO_EXT and not n.startswith("."):
                files.append(p)
    return sorted(files)


def stratified_sample(files, n):
    by_ext = defaultdict(list)
    for f in files:
        by_ext[f.suffix.lower()].append(f)
    total = len(files)
    quota = {e: max(1, round(n * len(v) / total)) for e, v in by_ext.items()}
    while sum(quota.values()) > n:
        quota[max(quota, key=quota.get)] -= 1
    picked = []
    for e, items in by_ext.items():
        k = min(quota[e], len(items))
        step = len(items) / k
        picked += [items[int(i * step)] for i in range(k)]
    return sorted(picked)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(ROOT / "media"))
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--sample", type=int, help="ingestar una muestra estratificada de N archivos")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    catalog = Path(args.catalog)
    for sub in ("thumbs", "work", "sidecars"):
        (catalog / sub).mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(catalog / "catalog.sqlite")
    init_db(db)

    files = list_media(args.source)
    if args.sample:
        files = stratified_sample(files, args.sample)

    known = {row[0]: (row[1], row[2]) for row in db.execute("SELECT path, size, mtime FROM paths")}
    todo = []
    for f in files:
        st = f.stat()
        rel = str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f)
        if known.get(rel) != (st.st_size, st.st_mtime):
            todo.append(f)
    print(f"{len(files)} archivos seleccionados, {len(todo)} por ingestar, {len(files) - len(todo)} ya ingestados.")

    started = time.time()
    metas = exiftool_batch(todo) if todo else {}

    results, errors = [], []

    def work(f):
        try:
            return f, ingest_one(f, metas.get(str(f), {}), catalog), None
        except Exception as e:
            return f, None, f"{type(e).__name__}: {e}"

    with ThreadPoolExecutor(args.workers) as pool:
        for f, res, err in pool.map(work, todo):
            if err:
                errors.append((f, err))
                continue
            asset, tech = res
            problems = [e.message for e in VALIDATOR.iter_errors(asset)]
            if problems:
                errors.append((f, "schema: " + "; ".join(problems)))
                continue
            results.append((f, asset, tech))

    thumbs = [str(ROOT / t) for _, _, tech in results for t in tech["thumbs"]]
    if thumbs:
        subprocess.run(["exiftool", "-q", "-all=", "-overwrite_original", *thumbs], capture_output=True)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    seen_ids = Counter()
    for f, asset, tech in results:
        seen_ids[asset["id"]] += 1
        st = f.stat()
        existing = db.execute("SELECT path FROM assets WHERE id=?", (asset["id"],)).fetchone()
        if existing and existing[0] != asset["path"]:
            asset_row_path = existing[0]  # duplicado exacto: se conserva el primer path
        else:
            asset_row_path = asset["path"]
            db.execute("INSERT OR REPLACE INTO assets VALUES (?,?,?,?)",
                       (asset["id"], asset["path"], json.dumps(asset, ensure_ascii=False), now))
            db.execute("INSERT OR REPLACE INTO tech VALUES (?,?)",
                       (asset["id"], json.dumps(tech, ensure_ascii=False)))
            (catalog / "sidecars" / f"{asset['id'][7:23]}.json").write_text(
                json.dumps(asset, ensure_ascii=False, indent=2))
        db.execute("INSERT OR REPLACE INTO paths VALUES (?,?,?,?)",
                   (asset["path"], asset["id"], st.st_size, st.st_mtime))
        if asset_row_path != asset["path"]:
            print(f"  duplicado exacto: {asset['path']} == {asset_row_path}")
    db.commit()

    elapsed = time.time() - started
    report = {
        "ingested": len(results),
        "errors": [{"path": str(f), "error": e} for f, e in errors],
        "media_type": Counter(a["media_type"] for _, a, _ in results),
        "date_source": Counter(a["date_source"] for _, a, _ in results),
        "orientation": Counter(a["orientation"] for _, a, _ in results),
        "exact_duplicates_in_run": sum(c - 1 for c in seen_ids.values() if c > 1),
        "seconds": round(elapsed, 1),
    }
    (catalog / "ingest_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=dict))

    print(f"\nIngestados: {len(results)}  Errores: {len(errors)}  Tiempo: {elapsed:.1f}s")
    for key in ("media_type", "date_source", "orientation"):
        print(f"  {key}: {dict(report[key])}")
    for f, e in errors:
        print(f"  ERROR {f.name}: {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
