#!/usr/bin/env python3
"""Fase 4 (revisión): galería de assets etiquetados -> catalog/review/tags.html.

Muestra imagen, era, content_type, vibe, caption y alertas (sensible, terceros,
menores), numerados para dar feedback por número. Sensibles primero.

Uso:
  python scripts/04_review_tags.py                       # todo lo etiquetado
  python scripts/04_review_tags.py --batch catalog/batches/sample_01.json
"""
import argparse
import html
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def flags(a):
    out = [k for k, v in a.get("sensitive", {}).items() if v]
    p = a.get("people", {})
    if p.get("others_identifiable"):
        out.append("terceros")
    if p.get("minors"):
        out.append("menores")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--batch", help="limitar a los ids de un lote")
    args = ap.parse_args()
    catalog = Path(args.catalog)
    out = catalog / "review" / "tags.html"
    out.parent.mkdir(parents=True, exist_ok=True)

    ids = None
    if args.batch:
        ids = {i["id"]: i["image"] for i in json.loads(Path(args.batch).read_text())["items"]}

    db = sqlite3.connect(catalog / "catalog.sqlite")
    rows = []
    for aid, data, tech in db.execute("SELECT a.id, a.data, t.data FROM assets a JOIN tech t USING(id)"):
        a, t = json.loads(data), json.loads(tech)
        if "caption" not in a or (ids is not None and aid not in ids):
            continue
        strip = ROOT / "catalog" / "thumbs" / f"{aid[7:23]}_strip.jpg"
        img = strip if strip.exists() else ROOT / t["thumbs"][0]
        rows.append((a, img))
    rows.sort(key=lambda r: (not flags(r[0]), r[0]["date"]))

    cards = []
    for n, (a, img) in enumerate(rows, 1):
        f = flags(a)
        src = html.escape(os.path.relpath(img, out.parent))
        cards.append(
            f'<figure class="{"flag" if f else ""}"><img loading="lazy" src="{src}"><figcaption>'
            f'<b>#{n}</b> · {a["date"][:10]} · <b>{html.escape(a.get("era", "?"))}</b> · {a["media_type"]}<br>'
            f'{html.escape(", ".join(a.get("content_type", [])))}<br>'
            f'<i>{html.escape(", ".join(a.get("vibe", [])))}</i><br>'
            f'{html.escape(a.get("caption", ""))}'
            f'{"<br><span class=alert>⚠ " + html.escape(", ".join(f)) + "</span>" if f else ""}'
            f'</figcaption></figure>')

    out.write_text(f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Etiquetas</title>
<style>
:root{{--bg:#fafafa;--fg:#111;--card:#fff;--muted:#555;--alert:#c33}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--card:#1c1c1c;--muted:#aaa;--alert:#f66}}}}
body{{background:var(--bg);color:var(--fg);font:13px system-ui,sans-serif;margin:0;padding:16px}}
.grid{{display:flex;flex-wrap:wrap;gap:10px}}
figure{{background:var(--card);margin:0;padding:6px;border-radius:8px;width:260px;border:2px solid transparent}}
figure.flag{{border-color:var(--alert)}}
img{{width:100%;height:240px;object-fit:contain;background:#000;border-radius:4px}}
figcaption{{color:var(--muted);margin-top:4px;line-height:1.4}}
.alert{{color:var(--alert);font-weight:600}}
</style></head><body>
<h1>Etiquetas ({len(rows)})</h1>
<p>Con alerta primero (borde rojo), después por fecha. Feedback por número: "#7 es facu-inicio", "#12 no es sensible".</p>
<div class="grid">{"".join(cards)}</div></body></html>""")
    print(f"{len(rows)} assets -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
