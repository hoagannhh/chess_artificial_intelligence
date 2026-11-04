"""Integration runner: python tests/godot_smoke.py [--capture]."""
from pathlib import Path
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.api.server import make_server

server = make_server(0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
engine = ROOT / '.tools/godot/Godot_v4.5.1-stable_win64.exe'
capture = '--capture' in sys.argv
command = [str(engine), '--path', str(ROOT / 'frontend')]
if not capture:
    command += ['--headless', '--quit-after', '150']
command += ['--', f'--bridge-port={server.server_port}', '--smoke']
if capture:
    command += ['--capture']
try:
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=45)
    print(result.stdout.encode('ascii', errors='backslashreplace').decode())
    print(result.stderr)
    assert result.returncode == 0
    assert 'BRIDGE_OK pieces=32 legal=20' in result.stdout
    assert 'GODOT_FLOW_OK' in result.stdout
    assert 'SCRIPT ERROR' not in result.stderr
    if capture:
        assert 'CAPTURE_OK' in result.stdout
finally:
    server.shutdown()
    server.server_close()
    thread.join()
