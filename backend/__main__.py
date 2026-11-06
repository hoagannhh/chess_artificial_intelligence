"""Run from repository root: python -m backend --port 8765."""
from backend.api.server import make_server
from backend.application.storage import DEFAULT_SAVE


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    server = make_server(parser.parse_args().port, save_path=DEFAULT_SAVE)
    print(f"Chess rules listening on 127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
