"""Game controller independent of rendering. Rules supplied by python-chess.

No chess engine / AI is used. Keep rule-library calls here so that a future
custom rules implementation can replace this adapter without rewriting the UI.
"""
import chess
from backend.domain.clock import ChessClock, side_name


class Game:
    def __init__(self):
        self.reset()

    def reset(self, clock_minutes=0):
        self.board = chess.Board()
        self.history = []
        self.claimed_draw = False
        self.resigned = None
        self.agreed_draw = False
        self.clock = ChessClock(clock_minutes) if clock_minutes else None

    @property
    def flagged(self):
        return self.clock.flagged if self.clock else None

    def update_clock(self):
        return self.clock is not None and not self.finished and self.clock.flag_if_expired(self.board.turn)

    @property
    def finished(self):
        return self.flagged is not None or self.claimed_draw or self.resigned is not None or self.agreed_draw or self.board.is_game_over()

    def moves_from(self, square):
        if self.finished:
            return []
        return [m for m in self.board.legal_moves if m.from_square == square]

    def play(self, move):
        if self.finished or move not in self.board.legal_moves:
            return False
        notation = self.board.san(move)
        if self.clock and not self.clock.complete_turn(self.board.turn):
            return False
        self.board.push(move)
        self.history.append(notation)
        if self.clock and self.finished:
            self.clock.stop(self.board.turn)
        return True

    def undo(self):
        if self.resigned is not None or self.agreed_draw or self.claimed_draw:
            self.resigned = None
            self.agreed_draw = False
            self.claimed_draw = False
            if self.clock:
                self.clock.resume()
        elif self.board.move_stack:
            self.board.pop()
            self.history.pop()
            if self.clock:
                self.clock.undo_move()
        elif self.flagged is not None:
            self.clock = ChessClock(self.clock.minutes)

    def claim_draw(self):
        if not self.finished and self.board.can_claim_draw():
            self.claimed_draw = True
            if self.clock:
                self.clock.stop(self.board.turn)
            return True
        return False

    def status(self):
        if self.flagged is not None:
            title = {'0-1': 'BLACK WINS', '1-0': 'WHITE WINS', '1/2-1/2': 'DRAW'}[self.result()]
            detail = f'{side_name(self.flagged).capitalize()} ran out of time'
            if title == 'DRAW':
                detail += '; opponent has insufficient mating material'
            return title, detail
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
        if self.clock:
            self.clock.stop(self.board.turn)

    def agree_draw(self):
        if self.finished:
            raise ValueError("Game already finished")
        self.agreed_draw = True
        if self.clock:
            self.clock.stop(self.board.turn)

    def result(self):
        if self.flagged is not None:
            if self.board.has_insufficient_material(not self.flagged):
                return '1/2-1/2'
            return '0-1' if self.flagged else '1-0'
        if self.resigned is not None:
            return "0-1" if self.resigned else "1-0"
        if self.claimed_draw or self.agreed_draw:
            return "1/2-1/2"
        return self.board.result()
