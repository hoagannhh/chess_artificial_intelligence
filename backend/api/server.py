"""Local HTTP adapter; no UI dependencies."""
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from backend.application.session import Session


def make_server(port=8765, save_path=None):
    session = Session(save_path)

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
