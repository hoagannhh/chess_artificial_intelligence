"""Desktop entry point: python main.py."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from archive.pygame.robot_chess.app import run

if __name__ == "__main__":
    run()
