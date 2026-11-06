#!/usr/bin/env python3
"""Fase 3: métricas locales (sin API).

Etapas:
  image      nitidez (varianza del Laplaciano) y exposición sobre la miniatura
  aesthetic  puntaje estético LAION (CLIP ViT-L/14) — solo para ordenar; opcional (--aesthetic)
  scenes     cortes de escena en videos (PySceneDetect, detector adaptativo)
  speech     voz + transcripción con faster-whisper (solo videos con audio)

Cada etapa corre en su propio proceso (OpenCV y PyAV traen libav duplicada).
Idempotente: salta lo ya calculado salvo --force. Solo toca sus propios campos,
así no pisa decisiones de revisión guardadas en paralelo.

Uso:
  python scripts/03_metrics.py                 # todas las etapas
  python scripts/03_metrics.py --stage speech  # una sola
"""
import argparse
import json
import sqlite3
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGES = ("image", "aesthetic", "scenes", "speech")
SHORT_VIDEO_S = 5.0
AESTHETIC_URL = ("https://github.com/christophschuhmann/improved-aesthetic-predictor/raw/main/"
                 "sac+logos+ava1-l14-linearMSE.pth")
CACHE = Path.home() / ".cache" / "reel-story-kit"


def connect(catalog):
    db = sqlite3.connect(catalog / "catalog.sqlite", timeout=30)
    db.execute("PRAGMA busy_timeout=30000")
    return db


def rows(db, where=""):
    q = "SELECT a.id, a.data, t.data FROM assets a JOIN tech t USING(id)"
    for aid, data, tech in db.execute(q + (" WHERE " + where if where else "")).fetchall():
        yield aid, json.loads(data), json.loads(tech)


def merge(db, catalog, aid, key, values):
    """Mezcla `values` dentro de data.<key> de forma atómica y reescribe el sidecar."""
    db.execute(
        "UPDATE assets SET data = json_set(data, ?, json(json_patch(coalesce(json_extract(data, ?), '{}'), ?))) WHERE id=?",
        (f"$.{key}", f"$.{key}", json.dumps(values, ensure_ascii=False), aid))
    data = db.execute("SELECT data FROM assets WHERE id=?", (aid,)).fetchone()[0]
    (catalog / "sidecars" / f"{aid[7:23]}.json").write_text(
        json.dumps(json.loads(data), ensure_ascii=False, indent=2))


def rep_thumb(tech):
    thumbs = tech.get("thumbs") or []
    return ROOT / thumbs[len(thumbs) // 2] if thumbs else None


def stage_image(catalog, force, workers):
    import cv2

    db = connect(catalog)
    todo = [(aid, t) for aid, a, t in rows(db) if force or "sharpness" not in a.get("quality", {})]

    def measure(item):
        aid, tech = item
        img = cv2.imread(str(rep_thumb(tech)), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return aid, None
        sharp = float(cv2.Laplacian(img, cv2.CV_64F).var())
        mean = float(img.mean())
        dark = float((img < 16).mean())
        bright = float((img > 239).mean())
        ok = 40 <= mean <= 215 and dark < 0.4 and bright < 0.25
        return aid, {"sharpness": round(sharp, 1), "exposure_ok": ok}

    with ThreadPoolExecutor(workers) as pool:
        for aid, q in pool.map(measure, todo):
            if q:
                merge(db, catalog, aid, "quality", q)
    db.commit()
    return len(todo)


def stage_aesthetic(catalog, force, workers):
    import open_clip
    import torch
    from PIL import Image

    db = connect(catalog)
    todo = [(aid, t) for aid, a, t in rows(db) if force or "aesthetic_score" not in a.get("quality", {})]
    if not todo:
        return 0

    weights = CACHE / "laion-aesthetic-l14.pth"
    if not weights.exists():
        weights.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(AESTHETIC_URL, weights)

    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model, _, preprocess = open_clip.create_model_and_transforms("ViT-L-14", pretrained="openai", device=device)
    model.eval()

    class MLP(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.layers = torch.nn.Sequential(
                torch.nn.Linear(768, 1024), torch.nn.Dropout(0.2),
                torch.nn.Linear(1024, 128), torch.nn.Dropout(0.2),
                torch.nn.Linear(128, 64), torch.nn.Dropout(0.1),
                torch.nn.Linear(64, 16), torch.nn.Linear(16, 1))

        def forward(self, x):
            return self.layers(x)

    head = MLP()
    head.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
    head.to(device).eval()

    batch = 32
    with torch.no_grad():
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            imgs = torch.stack([preprocess(Image.open(rep_thumb(t)).convert("RGB")) for _, t in chunk]).to(device)
            emb = model.encode_image(imgs)
            emb = emb / emb.norm(dim=-1, keepdim=True)
            scores = head(emb.float()).squeeze(1).cpu().tolist()
            for (aid, _), s in zip(chunk, scores):
                merge(db, catalog, aid, "quality", {"aesthetic_score": round(float(s), 2)})
            db.commit()
    return len(todo)


def stage_scenes(catalog, force, workers):
    from scenedetect import AdaptiveDetector, detect

    db = connect(catalog)
    todo = [(aid, a) for aid, a, t in rows(db, "json_extract(a.data,'$.media_type')='video'")
            if force or "scenes" not in a.get("video", {})]

    def run(item):
        aid, a = item
        dur = a["video"]["duration_s"]
        if dur < SHORT_VIDEO_S:
            return aid, [[0.0, dur]]
        try:
            found = detect(str(ROOT / a["path"]), AdaptiveDetector())
        except Exception:
            return aid, None
        scenes = [[round(s.seconds, 2), round(e.seconds, 2)] for s, e in found]
        return aid, scenes or [[0.0, dur]]

    with ThreadPoolExecutor(workers) as pool:
        for aid, scenes in pool.map(run, todo):
            if scenes is not None:
                merge(db, catalog, aid, "video", {"scenes": scenes})
                db.commit()
    return len(todo)


def stage_speech(catalog, force, workers):
    from faster_whisper import WhisperModel

    db = connect(catalog)
    todo = [(aid, a) for aid, a, t in rows(db, "json_extract(a.data,'$.media_type')='video'")
            if a["video"].get("has_audio") and (force or "speech" not in a["video"])]
    no_audio = [aid for aid, a, t in rows(db, "json_extract(a.data,'$.media_type')='video'")
                if not a["video"].get("has_audio") and "speech" not in a["video"]]
    for aid in no_audio:
        merge(db, catalog, aid, "video", {"speech": False})
    db.commit()
    if not todo:
        return len(no_audio)

    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
    todo.sort(key=lambda x: x[1]["video"]["duration_s"])
    for i, (aid, a) in enumerate(todo, 1):
        try:
            segments, info = model.transcribe(
                str(ROOT / a["path"]), vad_filter=True, beam_size=1, condition_on_previous_text=False)
            kept = [s for s in segments if s.no_speech_prob < 0.6 and s.avg_logprob > -1.0 and s.text.strip()]
        except Exception as e:
            print(f"  speech error {Path(a['path']).name}: {e}", file=sys.stderr)
            continue
        text = " ".join(s.text.strip() for s in kept)
        values = {"speech": bool(text)}
        if text:
            values["transcript"] = text
        merge(db, catalog, aid, "video", values)
        db.execute("UPDATE tech SET data=json_set(data,'$.speech_language',?) WHERE id=?",
                   (info.language if text else None, aid))
        db.commit()
        if i % 25 == 0:
            print(f"  speech {i}/{len(todo)}", flush=True)
    return len(todo) + len(no_audio)


def validate(catalog):
    import jsonschema
    schema = json.loads((ROOT / "schema" / "asset.schema.json").read_text())
    v = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
    db = connect(catalog)
    bad = [(aid, [e.message for e in v.iter_errors(a)]) for aid, a, _ in rows(db)]
    return [b for b in bad if b[1]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--stage", choices=STAGES + ("all",), default="all")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--aesthetic", action="store_true",
                    help="incluir la etapa estética en 'all' (descarga CLIP ViT-L/14 y pesos LAION)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    catalog = Path(args.catalog)

    if args.stage == "all":
        stages = [s for s in STAGES if s != "aesthetic" or args.aesthetic]
        for stage in stages:
            cmd = [sys.executable, __file__, "--stage", stage, "--catalog", str(catalog), "--workers", str(args.workers)]
            if args.force:
                cmd.append("--force")
            if subprocess.run(cmd).returncode != 0:
                return 1
        bad = validate(catalog)
        print(f"Validación: {len(bad)} assets con errores de esquema")
        for aid, problems in bad[:10]:
            print(f"  {aid[:23]}: {problems}")
        return 1 if bad else 0

    started = time.time()
    fn = globals()[f"stage_{args.stage}"]
    n = fn(catalog, args.force, args.workers)
    print(f"[{args.stage}] {n} assets procesados en {time.time() - started:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
