#!/usr/bin/env python3
"""Fase 4: arma lotes para subagentes `classifier` (catalog/batches/batch_XX.json).

Cada ítem lleva la imagen a mirar (miniatura; en videos, una tira con 3 keyframes)
y los datos ya calculados, para que el modelo no los recalcule. Los no-keepers de
clusters de duplicados no se mandan: heredan las etiquetas del keeper en el merge.

Uso:
  python scripts/04_make_batches.py --sample 50        # un solo lote de muestra
  python scripts/04_make_batches.py --size 100         # todo lo pendiente
"""
import argparse
import json
import random
import sqlite3
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
STRIP_H = 400
TRANSCRIPT_MAX = 300


def video_strip(tech, short):
    out = ROOT / "catalog" / "thumbs" / f"{short}_strip.jpg"
    if out.exists():
        return out
    frames = []
    for t in tech["thumbs"]:
        im = Image.open(ROOT / t).convert("RGB")
        im = im.resize((round(im.width * STRIP_H / im.height), STRIP_H))
        frames.append(im)
    strip = Image.new("RGB", (sum(f.width for f in frames) + 8 * (len(frames) - 1), STRIP_H), "white")
    x = 0
    for f in frames:
        strip.paste(f, (x, 0))
        x += f.width + 8
    strip.save(out, "JPEG", quality=85)
    return out


def item_for(aid, a, t):
    short = aid[7:23]
    if a["media_type"] == "video":
        image = video_strip(t, short)
    else:
        image = ROOT / t["thumbs"][0]
    item = {
        "id": aid,
        "image": str(image.relative_to(ROOT)),
        "media_type": a["media_type"],
        "date": a["date"],
        "date_source": a["date_source"],
        "orientation": a["orientation"],
        "sharpness": a.get("quality", {}).get("sharpness"),
        "exposure_ok": a.get("quality", {}).get("exposure_ok"),
        "series": next((x for x in a.get("tags", []) if x.startswith("serie-")), None),
    }
    v = a.get("video")
    if v:
        item["duration_s"] = v["duration_s"]
        item["speech"] = v.get("speech")
        if v.get("transcript"):
            item["transcript"] = v["transcript"][:TRANSCRIPT_MAX]
    return item


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--size", type=int, default=100)
    ap.add_argument("--sample", type=int, help="un único lote aleatorio (semilla fija) de N ítems")
    ap.add_argument("--force", action="store_true", help="incluir assets ya etiquetados")
    args = ap.parse_args()

    catalog = Path(args.catalog)
    db = sqlite3.connect(catalog / "catalog.sqlite")
    pending = []
    for aid, data, tech in db.execute("SELECT a.id, a.data, t.data FROM assets a JOIN tech t USING(id) ORDER BY a.id"):
        a, t = json.loads(data), json.loads(tech)
        if a.get("cluster_id") and not a.get("is_cluster_keeper", True):
            continue
        if "caption" in a and not args.force:
            continue
        pending.append((aid, a, t))

    if args.sample:
        random.Random(42).shuffle(pending)
        pending = pending[:args.sample]
        size = args.sample
    else:
        size = args.size

    out_dir = catalog / "batches"
    out_dir.mkdir(parents=True, exist_ok=True)
    (catalog / "out").mkdir(exist_ok=True)
    prefix = "sample" if args.sample else "batch"
    written = []
    for i in range(0, len(pending), size):
        items = [item_for(*p) for p in pending[i:i + size]]
        path = out_dir / f"{prefix}_{i // size + 1:02d}.json"
        path.write_text(json.dumps({"items": items}, ensure_ascii=False, indent=1))
        written.append((path, len(items)))
    for path, n in written:
        print(f"{path.relative_to(ROOT)}: {n} ítems")
    print(f"Total: {len(pending)} assets en {len(written)} lotes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
