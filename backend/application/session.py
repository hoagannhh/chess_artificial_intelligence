"""Application commands and frontend-neutral snapshots."""
from pathlib import Path
import chess
from backend.domain.game import Game
from backend.application.storage import load_game, save_game, export_pgn


class Session:
    def __init__(self, save_path=None):
        self.game = Game()
        self.save_path = Path(save_path) if save_path else None
        self.notice = ''
        # A corrupt save is preserved until the player explicitly starts a new game.
        self.save_blocked = False
        if self.save_path and self.save_path.exists():
            try:
                self.game = load_game(self.save_path)
                self.notice = 'Previous game restored.'
            except (OSError, ValueError) as error:
                self.notice = f'Cannot restore save: {error}. New Game enables saving again.'
                self.save_blocked = True

    def snapshot(self):
        board = self.game.board
        title, detail = self.game.status()
        return {
            'pieces': [{'square': square, 'symbol': piece.symbol()} for square, piece in board.piece_map().items()],
            'legal': [m.uci() for m in board.legal_moves] if not self.game.finished else [],
            'turn': 'white' if board.turn else 'black', 'title': title, 'detail': detail,
            'history': self.game.history[:], 'finished': self.game.finished,
            'check': board.king(board.turn) if board.is_check() else -1,
            'last': board.peek().uci() if board.move_stack else '',
            'claimable': not self.game.finished and board.can_claim_draw(),
            'result': self.game.result(), 'fen': board.fen(),
            'pgn': export_pgn(self.game), 'notice': self.notice,
            'can_undo': bool(board.move_stack) or self.game.claimed_draw or self.game.resigned is not None or self.game.agreed_draw,
        }

    def persist(self):
        if self.save_path and not self.save_blocked:
            try:
                save_game(self.game, self.save_path)
                self.notice = 'Game saved automatically.'
            except OSError as error:
                self.notice = f'Game is in memory only. Save failed: {error}'

    def action(self, data):
        action = data.get('action')
        if action == 'move':
            uci = data.get('move', '')
            if not isinstance(uci, str):
                raise ValueError('Expected move in UCI notation')
            move = chess.Move.from_uci(uci)
            if not self.game.play(move):
                raise ValueError('Illegal move')
        elif action == 'undo':
            self.game.undo()
        elif action == 'reset':
            if self.save_blocked and self.save_path.exists():
                # Keep the unreadable original available for recovery.
                backup = self.save_path.with_suffix('.invalid.json')
                if backup.exists():
                    raise ValueError('A save backup already exists; move it before starting a new game')
                self.save_path.rename(backup)
            self.game.reset()
            self.save_blocked = False
        elif action == 'claim':
            if not self.game.claim_draw():
                raise ValueError('Draw cannot be claimed')
        elif action == 'resign':
            self.game.resign()
        elif action == 'agree_draw':
            self.game.agree_draw()
        elif action == 'save':
            if not self.save_path or self.save_blocked:
                raise ValueError('Saving is unavailable; start a new game if the save is damaged')
        elif action == 'load':
            if not self.save_path or not self.save_path.exists():
                raise ValueError('No saved game')
            restored = load_game(self.save_path)
            self.game = restored
            self.save_blocked = False
        else:
            raise ValueError('Unknown action')
        self.persist()
        return self.snapshot()
