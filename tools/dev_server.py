"""Lokal devserver för designarbete.

Bygger om sidan från data/menus.json vid varje omladdning, så ändringar i
scraper/build.py syns direkt utan att något skrivs till docs/.

Kör: .venv/bin/python tools/dev_server.py
Öppna: http://localhost:8000/  (lägg till ?datum=2026-09-23 för att se en annan dag)
"""
import importlib
import json
import sys
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

PORT = 8000


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        if url.path not in ("/", "/index.html"):
            self._serve_static(url.path)
            return
        try:
            import scraper.weeks
            import scraper.build
            importlib.reload(scraper.weeks)
            build = importlib.reload(scraper.build)
            data = json.loads((ROOT / "data" / "menus.json").read_text(encoding="utf-8"))
            chosen = parse_qs(url.query).get("datum", [None])[0]
            today = date.fromisoformat(chosen) if chosen else datetime.now(build.TZ).date()
            body = build.render(data, today).encode("utf-8")
            status = 200
        except Exception as exc:  # visa felet i webbläsaren i stället för att krascha
            body = f"<pre>Fel vid bygget:\n{type(exc).__name__}: {exc}</pre>".encode("utf-8")
            status = 500
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_static(self, path):
        target = (ROOT / "docs" / path.lstrip("/")).resolve()
        docs = (ROOT / "docs").resolve()
        if docs not in target.parents or not target.is_file():
            self.send_error(404)
            return
        types = {".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8",
                 ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml"}
        self.send_response(200)
        self.send_header("Content-Type", types.get(target.suffix, "application/octet-stream"))
        self.end_headers()
        self.wfile.write(target.read_bytes())

    def log_message(self, fmt, *args):
        sys.stderr.write("%s\n" % (fmt % args))


if __name__ == "__main__":
    print(f"Devserver på http://localhost:{PORT}/")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
