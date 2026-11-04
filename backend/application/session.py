"""Application commands and frontend-neutral snapshots."""
import chess
from backend.domain.game import Game


class Session:
    def __init__(self):
        self.game = Game()

    def snapshot(self):
        board = self.game.board
        title, detail = self.game.status()
        return {
            "pieces": [{"square": square, "symbol": piece.symbol()} for square, piece in board.piece_map().items()],
            "legal": [m.uci() for m in board.legal_moves] if not self.game.finished else [],
            "turn": "white" if board.turn else "black", "title": title, "detail": detail,
            "history": self.game.history[:], "finished": self.game.finished,
            "check": board.king(board.turn) if board.is_check() else -1,
            "last": board.peek().uci() if board.move_stack else "",
            "claimable": not self.game.finished and board.can_claim_draw(),
        }

    def action(self, data):
        action = data.get("action")
        if action == "move":
            move = chess.Move.from_uci(data.get("move", ""))
            if not self.game.play(move):
                raise ValueError("Illegal move")
        elif action == "undo":
            self.game.undo()
        elif action == "reset":
            self.game.reset()
        elif action == "claim":
            if not self.game.claim_draw():
                raise ValueError("Draw cannot be claimed")
        else:
            raise ValueError("Unknown action")
        return self.snapshot()

