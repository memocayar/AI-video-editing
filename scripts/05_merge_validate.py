#!/usr/bin/env python3
"""Fase 4: valida catalog/out/*.jsonl y mezcla los campos semánticos al catálogo.

Solo se toman campos semánticos de la salida del modelo; lo técnico (fecha, orientación,
métricas) queda como está. Tags y layout_options se unen con los existentes, así no se
pierden las marcas de series ni las decisiones de revisión. Los no-keepers de clusters
de duplicados heredan los campos semánticos de su keeper.

Uso:
  python scripts/05_merge_validate.py catalog/out/sample_01.jsonl
  python scripts/05_merge_validate.py            # todos los catalog/out/*.jsonl
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "asset.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())

SEMANTIC = ("era", "location_type", "content_type", "vibe", "estilo_visual", "temas_personales",
            "people", "sensitive", "pair_key", "caption", "notes")
UNION = ("tags", "layout_options")
IMAGE_TYPES = {"photo", "screenshot", "meme", "graphic"}


def merge_semantic(asset, out):
    a = dict(asset)
    for k in SEMANTIC:
        if k in out:
            a[k] = out[k]
    for k in UNION:
        if k in out:
            a[k] = list(dict.fromkeys(a.get(k, []) + out[k]))
    if "llm_quality_1_5" in out:
        a["quality"] = {**a.get("quality", {}), "llm_quality_1_5": out["llm_quality_1_5"]}
    if a["media_type"] in IMAGE_TYPES and out.get("media_type") in IMAGE_TYPES:
        a["media_type"] = out["media_type"]
    if a["date_source"] == "filesystem" and out.get("date_source") == "inferred" and out.get("date"):
        a["date"] = out["date"]
        a["date_source"] = "inferred"
        a["date_confidence"] = min(float(out.get("date_confidence", 0.3)), 0.4)
    return a


def write(db, catalog, aid, asset):
    db.execute("UPDATE assets SET data=? WHERE id=?", (json.dumps(asset, ensure_ascii=False), aid))
    (catalog / "sidecars" / f"{aid[7:23]}.json").write_text(json.dumps(asset, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    args = ap.parse_args()
    catalog = Path(args.catalog)
    files = [Path(f) for f in args.files] or sorted((catalog / "out").glob("*.jsonl"))

    db = sqlite3.connect(catalog / "catalog.sqlite", timeout=30)
    ok, invalid, unknown = 0, [], []
    merged = {}
    for f in files:
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                out = json.loads(line)
            except json.JSONDecodeError as e:
                invalid.append((f"{f.name}:{n}", f"JSON inválido: {e}"))
                continue
            aid = out.get("id")
            row = db.execute("SELECT data FROM assets WHERE id=?", (aid,)).fetchone()
            if not row:
                unknown.append(f"{f.name}:{n}")
                continue
            asset = merge_semantic(json.loads(row[0]), out)
            problems = [e.message for e in VALIDATOR.iter_errors(asset)]
            if problems:
                invalid.append((aid, problems))
                continue
            write(db, catalog, aid, asset)
            merged[aid] = out
            ok += 1

    inherited = 0
    for cid, keeper in db.execute("SELECT cluster_id, id FROM clusters WHERE is_keeper=1").fetchall():
        if keeper not in merged:
            continue
        for (member,) in db.execute("SELECT id FROM clusters WHERE cluster_id=? AND is_keeper=0", (cid,)).fetchall():
            row = db.execute("SELECT data FROM assets WHERE id=?", (member,)).fetchone()
            asset = merge_semantic(json.loads(row[0]), merged[keeper])
            if not list(VALIDATOR.iter_errors(asset)):
                write(db, catalog, member, asset)
                inherited += 1
    db.commit()

    print(f"Mergeados: {ok}  Heredados por duplicado: {inherited}  Inválidos: {len(invalid)}  Ids desconocidos: {len(unknown)}")
    for where, problems in invalid:
        print(f"  INVALIDO {where[:30]}: {problems}")
    for where in unknown:
        print(f"  ID DESCONOCIDO {where}")
    return 1 if invalid or unknown else 0


if __name__ == "__main__":
    sys.exit(main())
