"""Local HTTP adapter; no UI dependencies."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from backend.application.session import Session


def make_server(port=8765):
    session = Session()

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
            else:
                self.send_json(404, {"error": "Not found"})

        def do_POST(self):
            # The native client sends no Origin. Reject browser-origin mutations.
            if self.headers.get("Origin") or self.path != "/action":
                self.send_json(403, {"error": "Forbidden"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 4096:
                    raise ValueError("Invalid body size")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected object")
                self.send_json(200, session.action(data))
            except (ValueError, TypeError) as error:
                self.send_json(400, {"error": str(error)})

        def log_message(self, *args):
            pass

    return HTTPServer(("127.0.0.1", port), Handler)
