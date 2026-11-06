#!/usr/bin/env python3
"""Fase 2 (revisión): sirve la galería de duplicados/series y guarda tus decisiones.

Cada clic (Conservar / Descarte / Collage) se guarda en catalog/review/decisions.json
y se aplica al catálogo (SQLite + sidecar). Solo escucha en 127.0.0.1.

Uso:
  python scripts/02_review.py            # abre http://127.0.0.1:8765/review/clusters.html
"""
import argparse
import functools
import json
import sqlite3
import sys
import threading
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jsonschema

from review_lib import DECISIONS, apply_decision, load_decisions, save_decisions

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "schema" / "asset.schema.json").read_text())
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA, format_checker=jsonschema.FormatChecker())
LOCK = threading.Lock()


class Handler(SimpleHTTPRequestHandler):
    catalog: Path

    def log_message(self, fmt, *args):
        pass

    def send_json(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/decisions":
            return self.send_json(200, load_decisions(self.catalog))
        return super().do_GET()

    def do_POST(self):
        if self.path != "/api/decisions":
            return self.send_json(404, {"error": "not found"})
        try:
            batch = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        except (ValueError, TypeError):
            return self.send_json(400, {"error": "json inválido"})
        if not isinstance(batch, dict) or any(d not in DECISIONS for d in batch.values()):
            return self.send_json(400, {"error": f"decisiones válidas: {DECISIONS}"})

        with LOCK:
            db = sqlite3.connect(self.catalog / "catalog.sqlite")
            decisions = load_decisions(self.catalog)
            for aid, decision in batch.items():
                row = db.execute("SELECT data FROM assets WHERE id=?", (aid,)).fetchone()
                if not row:
                    continue
                asset = apply_decision(json.loads(row[0]), decision)
                if list(VALIDATOR.iter_errors(asset)):
                    continue
                db.execute("UPDATE assets SET data=? WHERE id=?", (json.dumps(asset, ensure_ascii=False), aid))
                (self.catalog / "sidecars" / f"{aid[7:23]}.json").write_text(
                    json.dumps(asset, ensure_ascii=False, indent=2))
                decisions[aid] = decision
            db.commit()
            db.close()
            save_decisions(self.catalog, decisions)
        return self.send_json(200, decisions)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--catalog", default=str(ROOT / "catalog"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    catalog = Path(args.catalog).resolve()
    if not (catalog / "review" / "clusters.html").exists():
        print("Falta catalog/review/clusters.html: corré primero scripts/02_dedup.py")
        return 1
    Handler.catalog = catalog
    handler = functools.partial(Handler, directory=str(catalog))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    url = f"http://127.0.0.1:{args.port}/review/clusters.html"
    print(f"Galería de revisión: {url}  (Ctrl+C para cerrar)")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
