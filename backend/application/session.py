"""Application commands and frontend-neutral snapshots."""
from pathlib import Path
import chess
from backend.domain.game import Game
from backend.domain.clock import CLOCK_MINUTES
from backend.ai.search import search
from backend.application.storage import load_game, save_game, export_pgn


class Session:
    def __init__(self, save_path=None):
        self.game = Game()
        self.save_path = Path(save_path) if save_path else None
        self.notice = ''
        self.ai_stats = None
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
        if self.game.update_clock():
            self.persist()
        board = self.game.board
        title, detail = self.game.status()
        # Replay actual captures so promotion and en passant are represented correctly.
        captured = {'white': [], 'black': []}
        replay = board.root()
        for move in board.move_stack:
            victim = replay.piece_at(move.to_square)
            if replay.is_en_passant(move):
                victim = chess.Piece(chess.PAWN, not replay.turn)
            if victim and not replay.is_castling(move):
                captured['white' if victim.color else 'black'].append(victim.symbol())
            replay.push(move)
        return {
            'captured': captured,
            'pieces': [{'square': square, 'symbol': piece.symbol()} for square, piece in board.piece_map().items()],
            'legal': [m.uci() for m in board.legal_moves] if not self.game.finished else [],
            'turn': 'white' if board.turn else 'black', 'title': title, 'detail': detail,
            'history': self.game.history[:], 'finished': self.game.finished,
            'check': board.king(board.turn) if board.is_check() else -1,
            'last': board.peek().uci() if board.move_stack else '',
            'claimable': not self.game.finished and board.can_claim_draw(),
            'ai_stats': self.ai_stats,
            'clock': self.clock_state(),
            'result': self.game.result(), 'fen': board.fen(),
            'pgn': export_pgn(self.game), 'notice': self.notice,
            'can_undo': self.game.flagged is not None or bool(board.move_stack) or self.game.claimed_draw or self.game.resigned is not None or self.game.agreed_draw,
        }

    def clock_state(self):
        clock = self.game.clock
        if clock is None:
            return None
        return {'minutes': clock.minutes, 'remaining_ms': clock.remaining(self.game.board.turn),
                'running': clock.started is not None}

    def persist(self):
        if self.save_path and not self.save_blocked:
            try:
                save_game(self.game, self.save_path)
                self.notice = 'Game saved automatically.'
            except OSError as error:
                self.notice = f'Game is in memory only. Save failed: {error}'

    def action(self, data):
        action = data.get('action')
        if self.game.update_clock():
            self.persist()
        if self.game.flagged is not None and action in ('move', 'ai_move', 'claim', 'resign', 'agree_draw'):
            return self.snapshot()
        if action == 'ai_move':
            if self.game.finished:
                raise ValueError('Game already finished')
            algorithm = data.get('algorithm', 'alphabeta')
            depth = data.get('depth', 3)
            limit = data.get('time_limit_ms', 1000)
            # Validate options even when a draw can be claimed.
            result = search(self.game.board, algorithm, depth, limit)
            if self.game.update_clock():
                self.persist()
                return self.snapshot()
            side = 'white' if self.game.board.turn else 'black'
            if self.game.board.can_claim_draw():
                self.game.claim_draw()
                result.move = None
                result.score = None if algorithm == 'mcts' else 0
                if algorithm == 'mcts':
                    result.mean_reward = 0.0
            elif result.move is None or not self.game.play(chess.Move.from_uci(result.move)):
                if self.game.flagged is None:
                    raise ValueError('AI could not produce a legal move')
            self.ai_stats = {**result.to_dict(), 'side': side}
        elif action == 'move':
            uci = data.get('move', '')
            if not isinstance(uci, str):
                raise ValueError('Expected move in UCI notation')
            move = chess.Move.from_uci(uci)
            if not self.game.play(move) and self.game.flagged is None:
                raise ValueError('Illegal move')
        elif action == 'undo':
            count = data.get('count', 1)
            if type(count) is not int or count not in (1, 2):
                raise ValueError('Undo count must be 1 or 2')
            if self.game.claimed_draw or self.game.agreed_draw or self.game.resigned is not None:
                self.game.undo()
            else:
                for _ in range(count):
                    self.game.undo()
        elif action == 'reset':
            minutes = data.get('clock_minutes', 0)
            if type(minutes) is not int or minutes not in CLOCK_MINUTES:
                raise ValueError('Clock must be off or 5, 10, or 15 minutes')
            if self.save_blocked and self.save_path.exists():
                # Keep the unreadable original available for recovery.
                backup = self.save_path.with_suffix('.invalid.json')
                if backup.exists():
                    raise ValueError('A save backup already exists; move it before starting a new game')
                self.save_path.rename(backup)
            self.game.reset(minutes)
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
        if action != 'ai_move':
            self.ai_stats = None
        self.persist()
        return self.snapshot()
