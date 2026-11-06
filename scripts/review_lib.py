"""Decisiones humanas de la revisión de duplicados/series (catalog/review/decisions.json)."""
import json
from pathlib import Path

DECISIONS = ("conservar", "descarte", "collage")
REVIEW_TAGS = {"descarte", "collage"}


def decisions_path(catalog):
    return Path(catalog) / "review" / "decisions.json"


def load_decisions(catalog):
    p = decisions_path(catalog)
    return json.loads(p.read_text()) if p.exists() else {}


def save_decisions(catalog, decisions):
    p = decisions_path(catalog)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(decisions, ensure_ascii=False, indent=2, sort_keys=True))


def apply_decision(asset, decision):
    """Devuelve una copia del asset con la decisión aplicada. No borra nada: solo marca."""
    a = dict(asset)
    tags = [t for t in a.get("tags", []) if t not in REVIEW_TAGS]
    layouts = [l for l in a.get("layout_options", []) if l != "stack-candidate"]
    if decision == "descarte":
        tags.append("descarte")
        a["is_cluster_keeper"] = False
    elif decision == "collage":
        tags.append("collage")
        layouts.append("stack-candidate")
        a["is_cluster_keeper"] = True
    elif decision == "conservar":
        a["is_cluster_keeper"] = True
    for key, values in (("tags", tags), ("layout_options", layouts)):
        if values:
            a[key] = values
        else:
            a.pop(key, None)
    return a
