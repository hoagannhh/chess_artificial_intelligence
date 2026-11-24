"""Validated local saves and portable PGN export."""
import json
import os
from pathlib import Path
import chess
import chess.pgn
from uuid import UUID
from backend.ai.search import ALGORITHMS
from backend.domain.game import Game
from backend.domain.clock import ChessClock

DEFAULT_SAVE = Path(__file__).resolve().parents[2] / '.local' / 'saves' / 'current.json'


def save_game(game, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {'version': 1, 'initial_fen': game.board.root().fen(),
               'moves': [m.uci() for m in game.board.move_stack],
               'claimed_draw': game.claimed_draw, 'resigned': game.resigned,
               'agreed_draw': game.agreed_draw, 'game_id': game.game_id,
               'experiment': game.experiment}
    if game.clock:
        payload['clock'] = game.clock.save_data(game.board.turn)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    os.replace(temporary, path)


def load_game(path):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Unsupported save format')
        game = Game()
        if 'game_id' in data:
            game.game_id = UUID(data['game_id']).hex
        game.board = chess.Board(data['initial_fen'])
        if not game.board.is_valid():
            raise ValueError('Invalid saved board')
        moves = data['moves']
        if not isinstance(moves, list) or len(moves) > 20000:
            raise ValueError('Invalid saved move list')
        for uci in moves:
            if not isinstance(uci, str) or not game.play(chess.Move.from_uci(uci)):
                raise ValueError('Illegal move in saved game')
        claimed = data.get('claimed_draw', False)
        agreed = data.get('agreed_draw', False)
        resigned = data.get('resigned')
        if type(claimed) is not bool or type(agreed) is not bool or (resigned is not None and type(resigned) is not bool):
            raise ValueError('Invalid saved result')
        if sum([claimed, agreed, resigned is not None]) > 1:
            raise ValueError('Conflicting saved results')
        if claimed and not game.claim_draw():
            raise ValueError('Invalid saved draw claim')
        if agreed:
            game.agree_draw()
        if resigned is not None:
            if resigned != game.board.turn:
                raise ValueError('Invalid resigned side')
            game.resign()
        if 'clock' in data:
            game.clock = ChessClock.from_save(data['clock'], len(moves), game.board.turn, game.finished)
        context = data.get('experiment')
        if context is not None:
            if (not isinstance(context, dict) or 'game_id' not in data
                    or any(context.get(k) not in ALGORITHMS for k in ('white_algorithm', 'black_algorithm'))
                    or type(context.get('start_ply')) is not int or not 0 <= context['start_ply'] <= len(moves)
                    or type(context.get('depth')) is not int or not 1 <= context['depth'] <= 5
                    or type(context.get('time_limit_ms')) is not int or not 50 <= context['time_limit_ms'] <= 2000
                    or not isinstance(context.get('initial_fen'), str)):
                raise ValueError('Invalid saved AI experiment')
            game.experiment = context
        return game
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Invalid save format') from error


def export_pgn(game):
    record = chess.pgn.Game.from_board(game.board)
    record.headers['Event'] = 'Local two-player game'
    record.headers['White'] = 'White'
    record.headers['Black'] = 'Black'
    record.headers['Result'] = game.result()
    if game.finished:
        record.headers['Termination'] = game.status()[1]
    return str(record)
