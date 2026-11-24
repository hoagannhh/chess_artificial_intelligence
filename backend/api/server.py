"""Local HTTP adapter; no UI dependencies."""
import json
import csv
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from backend.application.session import Session
from backend.application.storage import DEFAULT_SAVE


def make_server(port=8765, save_path=None, experiments_root=None):
    if experiments_root is None and save_path is not None:
        save = Path(save_path)
        base = save.parent.parent if save.resolve() == DEFAULT_SAVE else save.parent
        experiments_root = base / 'experiments'
    session = Session(save_path, experiments_root)

    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, data):
            payload = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            if self.path == "/state":
                self.send_json(200, session.snapshot())
            elif self.path == "/experiments":
                try:
                    report = session.experiment_report()
                except (OSError, ValueError, KeyError, csv.Error) as error:
                    self.send_json(500, {"error": str(error)})
                    return
                self.send_json(200, report)
            else:
                self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            try:
                self.connection.settimeout(5)
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("Invalid body size")
                payload = self.rfile.read(size)
                # Drain the bounded body before closing: Windows may otherwise
                # reset the connection before the client receives the response.
                if self.headers.get("Origin") or self.path != "/action":
                    self.send_json(403, {"error": "Forbidden"})
                    return
                data = json.loads(payload)
                if not isinstance(data, dict):
                    raise ValueError("Expected object")
                self.send_json(200, session.action(data))
            except (ValueError, TypeError, OSError) as error:
                self.send_json(400, {"error": str(error)})

        def log_message(self, *args):
            pass

    class ChessServer(HTTPServer):
        def server_close(self):
            if session.game.clock is not None:
                session.game.update_clock()
                session.persist()
            super().server_close()

    return ChessServer(("127.0.0.1", port), Handler)
