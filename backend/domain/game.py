"""Game controller independent of rendering. Rules supplied by python-chess.

No chess engine / AI is used. Keep rule-library calls here so that a future
custom rules implementation can replace this adapter without rewriting the UI.
"""
import chess


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = chess.Board()
        self.history = []
        self.claimed_draw = False
        self.resigned = None
        self.agreed_draw = False

    @property
    def finished(self):
        return self.claimed_draw or self.resigned is not None or self.agreed_draw or self.board.is_game_over()

    def moves_from(self, square):
        if self.finished:
            return []
        return [m for m in self.board.legal_moves if m.from_square == square]

    def play(self, move):
        if self.finished or move not in self.board.legal_moves:
            return False
        notation = self.board.san(move)
        self.board.push(move)
        self.history.append(notation)
        return True

    def undo(self):
        if self.resigned is not None or self.agreed_draw:
            self.resigned = None
            self.agreed_draw = False
        elif self.claimed_draw:
            self.claimed_draw = False
        elif self.board.move_stack:
            self.board.pop()
            self.history.pop()

    def claim_draw(self):
        if not self.finished and self.board.can_claim_draw():
            self.claimed_draw = True
            return True
        return False

    def status(self):
        if self.resigned is not None:
            return ("BLACK WINS" if self.resigned else "WHITE WINS"), "Resignation"
        if self.agreed_draw:
            return "DRAW", "Agreement between both players"
        if self.claimed_draw:
            return "DRAW CLAIMED", "Repetition / fifty-move rule"
        outcome = self.board.outcome()
        if outcome:
            title = "DRAW" if outcome.winner is None else (
                "WHITE WINS" if outcome.winner else "BLACK WINS")
            return title, outcome.termination.name.replace("_", " ").title()
        side = "WHITE" if self.board.turn else "BLACK"
        return f"{side} TO MOVE", "CHECK - protect your king!" if self.board.is_check() else "Select a piece, then its destination"

    def resign(self):
        if self.finished:
            raise ValueError("Game already finished")
        self.resigned = self.board.turn

    def agree_draw(self):
        if self.finished:
            raise ValueError("Game already finished")
        self.agreed_draw = True

    def result(self):
        if self.resigned is not None:
            return "0-1" if self.resigned else "1-0"
        if self.claimed_draw or self.agreed_draw:
            return "1/2-1/2"
        return self.board.result()
