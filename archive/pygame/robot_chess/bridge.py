"""Legacy compatibility imports."""
from backend.application.session import Session
from backend.api.server import make_server

if __name__ == "__main__":
    from backend.__main__ import main
    main()
