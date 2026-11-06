#!/usr/bin/env python3
"""Fase 2: duplicados. pHash (exactos/redimensionados) + CNN (casi duplicados) -> clusters.

Trabaja sobre las miniaturas de catalog/thumbs (videos: keyframe del medio).
No borra nada: marca cluster_id e is_cluster_keeper en el catálogo y genera
catalog/review/clusters.html para revisión humana.

Uso:
  python scripts/02_dedup.py
  python scripts/02_dedup.py --phash-max 4 --cnn-min 0.93
"""
import argparse
import hashlib
import html
import json
import os
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

import jsonschema
from imagededup.methods import CNN, PHash

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "asset.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        self.parent[self.find(a)] = self.find(b)


def load_assets(db):
    rows = db.execute("SELECT a.id, a.data, t.data FROM assets a JOIN tech t USING(id)").fetchall()
    assets = {}
    for aid, data, tech in rows:
        a, t = json.loads(data), json.loads(tech)
        thumbs = t.get("thumbs") or []
        if not thumbs:
            continue
        rep = thumbs[len(thumbs) // 2]
        assets[aid] = {"asset": a, "tech": t, "thumb": rep}
    return assets


def kind_of(asset):
    return "video" if asset["media_type"] == "video" else "image"


def find_edges(assets, phash_max, cnn_min):
    """Devuelve {(a, b): method} con method 'exact' (pHash) o 'near' (CNN)."""
    edges = {}
    with tempfile.TemporaryDirectory() as tmp:
        by_name = {}
        for aid, info in assets.items():
            name = aid[7:23] + ".jpg"
            os.symlink(ROOT / info["thumb"], Path(tmp) / name)
            by_name[name] = aid

        phash = PHash(verbose=False)
        enc = phash.encode_images(image_dir=tmp)
        dups = phash.find_duplicates(encoding_map=enc, max_distance_threshold=phash_max)
        for name, others in dups.items():
            for other in others:
                a, b = sorted((by_name[name], by_name[other]))
                edges[(a, b)] = "exact"

        cnn = CNN(verbose=False)
        enc = cnn.encode_images(image_dir=tmp)
        dups = cnn.find_duplicates(encoding_map=enc, min_similarity_threshold=cnn_min, scores=True)
        for name, others in dups.items():
            for other, _score in others:
                a, b = sorted((by_name[name], by_name[other]))
                edges.setdefault((a, b), "near")

    # Fotos y videos no se agrupan entre sí (p. ej. Live Photo foto+video son material distinto).
    return {k: m for k, m in edges.items()
            if kind_of(assets[k[0]]["asset"]) == kind_of(assets[k[1]]["asset"])}


def keeper_score(info):
    a, t = info["asset"], info["tech"]
    pixels = (t.get("width") or 0) * (t.get("height") or 0)
    duration = a.get("video", {}).get("duration_s", 0)
    return (a["media_type"] == "photo", pixels, duration, a["date_confidence"], -len(a["path"]))


def group(assets, edges, prefix, with_keeper):
    uf = UnionFind()
    for a, b in edges:
        uf.union(a, b)
    groups = defaultdict(list)
    for aid in assets:
        if aid in uf.parent:
            groups[uf.find(aid)].append(aid)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort()
        gid = prefix + hashlib.sha1("".join(members).encode()).hexdigest()[:8]
        keeper = max(members, key=lambda m: keeper_score(assets[m])) if with_keeper else None
        out.append({"id": gid, "members": members, "keeper": keeper})
    out.sort(key=lambda c: (-len(c["members"]), c["id"]))
    return out


def build_groups(assets, edges):
    """Duplicados = solo aristas pHash. Series = cualquier arista (CNN agrupa lo parecido, no lo igual)."""
    exact = [k for k, m in edges.items() if m == "exact"]
    clusters = group(assets, exact, "c-", with_keeper=True)
    series = group(assets, list(edges), "serie-", with_keeper=False)
    # Una "serie" que es solo un cluster de duplicados no aporta nada.
    dup_sets = {frozenset(c["members"]) for c in clusters}
    series = [s for s in series if frozenset(s["members"]) not in dup_sets]
    return clusters, series


def write_db(db, assets, clusters, series):
    in_cluster = {m: (c["id"], m == c["keeper"]) for c in clusters for m in c["members"]}
    in_series = {m: s["id"] for s in series for m in s["members"]}

    db.executescript("""
        DROP TABLE IF EXISTS clusters;
        CREATE TABLE clusters (
            cluster_id TEXT NOT NULL, id TEXT NOT NULL REFERENCES assets(id),
            is_keeper INTEGER NOT NULL, PRIMARY KEY (cluster_id, id));
        DROP TABLE IF EXISTS series;
        CREATE TABLE series (
            series_id TEXT NOT NULL, id TEXT NOT NULL REFERENCES assets(id),
            PRIMARY KEY (series_id, id));
    """)

    errors = []
    for aid, info in assets.items():
        a = dict(info["asset"])
        cid, keeper = in_cluster.get(aid, (None, True))
        a["cluster_id"] = cid
        a["is_cluster_keeper"] = keeper
        tags = [t for t in a.get("tags", []) if not t.startswith("serie-")]
        if aid in in_series:
            tags.append(in_series[aid])
        if tags:
            a["tags"] = tags
        else:
            a.pop("tags", None)
        problems = [e.message for e in VALIDATOR.iter_errors(a)]
        if problems:
            errors.append((aid, problems))
            continue
        db.execute("UPDATE assets SET data=? WHERE id=?", (json.dumps(a, ensure_ascii=False), aid))
        (ROOT / "catalog" / "sidecars" / f"{aid[7:23]}.json").write_text(
            json.dumps(a, ensure_ascii=False, indent=2))
    for c in clusters:
        for m in c["members"]:
            db.execute("INSERT INTO clusters VALUES (?,?,?)", (c["id"], m, int(m == c["keeper"])))
    for s in series:
        for m in s["members"]:
            db.execute("INSERT INTO series VALUES (?,?)", (s["id"], m))
    db.commit()
    return errors


def write_html(assets, clusters, series, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    n = 0

    def section(title, groups, kind):
        nonlocal n
        cards = []
        for gi, g in enumerate(groups, 1):
            items = []
            members = sorted(g["members"], key=lambda m: (m != g["keeper"], assets[m]["asset"]["date"]))
            for m in members:
                n += 1
                info = assets[m]
                a, t = info["asset"], info["tech"]
                src = os.path.relpath(ROOT / info["thumb"], out.parent)
                extra = f" · {a['video']['duration_s']}s" if "video" in a else ""
                is_keeper = m == g["keeper"]
                items.append(
                    f'<figure class="item{" keeper" if is_keeper else ""}"><img loading="lazy" src="{html.escape(src)}">'
                    f'<figcaption><b>#{n}</b> {html.escape(Path(a["path"]).name)}<br>'
                    f'{a["date"][:10]} · {t.get("width")}×{t.get("height")}{extra}'
                    f'{" · <b>KEEPER</b>" if is_keeper else ""}</figcaption></figure>')
            cards.append(
                f'<section><h3>{kind} {gi} <small>{g["id"]} · {len(g["members"])} archivos</small></h3>'
                f'<div class="grid">{"".join(items)}</div></section>')
        return f"<h2>{title}</h2>" + "".join(cards)

    body = (
        section(f"Duplicados ({len(clusters)})", clusters, "Cluster")
        + "<p>Mismo archivo o misma imagen redimensionada/reexportada. Verde = keeper sugerido; "
          "los demás quedan marcados como no-keeper (no se borra nada).</p>"
        + section(f"Series parecidas ({len(series)})", series, "Serie")
        + "<p>Mismo lugar o situación en momentos distintos. No se descartan: "
          "candidatas a stack, ráfaga rápida o antes/después.</p>")
    doc = f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Clusters de duplicados</title>
<style>
:root{{--bg:#fafafa;--fg:#111;--card:#fff;--muted:#666;--accent:#0a7}}
@media (prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#eee;--card:#1c1c1c;--muted:#999;--accent:#3c9}}}}
body{{background:var(--bg);color:var(--fg);font:14px system-ui,sans-serif;margin:0;padding:16px}}
h1{{font-size:20px}} h2{{font-size:18px;margin:32px 0 4px}} h3{{font-size:15px;margin:20px 0 8px}}
small{{color:var(--muted);font-weight:normal}}
.grid{{display:flex;flex-wrap:wrap;gap:8px}}
.item{{background:var(--card);margin:0;padding:6px;border-radius:8px;width:180px;border:2px solid transparent}}
.item.keeper{{border-color:var(--accent)}}
.item img{{width:100%;height:220px;object-fit:contain;background:#000;border-radius:4px}}
figcaption{{font-size:12px;color:var(--muted);margin-top:4px;word-break:break-all}}
</style></head><body>
<h1>Duplicados y series</h1>
<p>{len(assets)} assets. Corregí por número: "#12 es keeper", "#30 no va en su serie".</p>
{body}
</body></html>"""
    out.write_text(doc)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--phash-max", type=int, default=4, help="distancia Hamming máx. para exactos (0-64)")
    ap.add_argument("--cnn-min", type=float, default=0.93, help="similitud coseno mín. para casi duplicados")
    args = ap.parse_args()

    catalog = Path(args.catalog)
    db = sqlite3.connect(catalog / "catalog.sqlite")
    assets = load_assets(db)
    print(f"{len(assets)} assets con miniatura.")

    edges = find_edges(assets, args.phash_max, args.cnn_min)
    clusters, series = build_groups(assets, edges)
    errors = write_db(db, assets, clusters, series)
    out = catalog / "review" / "clusters.html"
    write_html(assets, clusters, series, out)

    dup_files = sum(len(c["members"]) for c in clusters)
    print(f"Duplicados: {len(clusters)} clusters, {dup_files} archivos, "
          f"{dup_files - len(clusters)} no-keepers (candidatos a descarte)")
    print(f"Series: {len(series)}, {sum(len(s['members']) for s in series)} archivos (no se descartan)")
    print(f"Galería: {out}")
    for aid, problems in errors:
        print(f"  ERROR schema {aid[:23]}: {problems}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
