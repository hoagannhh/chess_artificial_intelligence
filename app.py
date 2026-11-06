"""Start Python rules on an available local port, then Godot; clean up on exit."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import threading
from backend.api.server import make_server
from backend.application.storage import DEFAULT_SAVE

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--godot", help="Path to a Godot 4 executable")
    args = parser.parse_args()
    candidates = list((ROOT / ".tools" / "godot").glob("Godot*_win64.exe"))
    engine = args.godot or os.environ.get("GODOT_EXE") or shutil.which("godot") or (str(candidates[0]) if candidates else None)
    if not engine:
        parser.error('Godot not found. Use --godot "C:/path/to/Godot.exe"')
    server = make_server(0, save_path=DEFAULT_SAVE)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        return subprocess.call([engine, "--path", str(ROOT / "frontend"), "--", f"--bridge-port={server.server_port}"])
    finally:
        server.shutdown()
        server.server_close()
        worker.join()


if __name__ == "__main__":
    raise SystemExit(main())
