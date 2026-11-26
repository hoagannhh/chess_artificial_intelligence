"""Supervised targets from the project's Alpha-Beta + Quiescence engine."""
from math import tanh

import chess
import chess.pgn
import torch

from backend.ai.search import search
from .encoding import action_index, encode

TEACHER = 'alphabeta_q'
VALUE_SCALE = 600.0


def teacher_game(depth, time_ms, max_plies, rng, initial_fen=chess.STARTING_FEN,
                 exploration=0.15, opening_plies=8):
    """Label the teacher's recommendation before choosing an exploratory played move.

    The value target is a bounded teacher evaluation from the side to move.
    A depth-zero timeout has no completed search and supplies no training label.
    """
    board = chess.Board(initial_fen)
    if not board.is_valid() or board.outcome(claim_draw=True) is not None:
        raise ValueError('Teacher requires a valid unfinished starting position')
    record = chess.pgn.Game()
    record.setup(board)
    record.headers['Event'] = 'Supervised teacher data with exploration'
    record.headers['White'] = record.headers['Black'] = TEACHER
    node = record
    samples = []
    skipped = 0
    for ply in range(max_plies):
        result = search(board, TEACHER, depth, time_ms)
        best_move = chess.Move.from_uci(result.move)
        if best_move not in board.legal_moves:
            raise ValueError('Teacher returned an illegal move')
        if result.depth > 0:
            sign = 1 if board.turn else -1
            samples.append(dict(
                state=encode(board).half(),
                indices=torch.tensor([action_index(best_move)]), policy=torch.tensor([1.0]),
                value=tanh(sign * result.score / VALUE_SCALE), value_known=True,
                source=TEACHER, value_source='teacher_heuristic', fen=board.fen(),
                teacher_move=result.move, teacher_score_cp=result.score,
                teacher_depth=result.depth, teacher_requested_depth=depth,
                teacher_timed_out=result.timed_out))
        else:
            skipped += 1
        legal = list(board.legal_moves)
        played = rng.choice(legal) if ply < opening_plies or rng.random() < exploration else best_move
        node = node.add_variation(played)
        node.comment = f'Teacher {result.move}, depth {result.depth}/{depth}, White cp {result.score}'
        board.push(played)
        if board.outcome(claim_draw=True) is not None:
            break
        if (ply + 1) % 32 == 0:
            print(f'  Teacher data: {ply + 1} plies, {len(samples)} labels', flush=True)
    outcome = board.outcome(claim_draw=True)
    record.headers['Result'] = outcome.result() if outcome else '*'
    record.headers['Termination'] = outcome.termination.name if outcome else 'max_plies'
    return samples, record, skipped


def sample_training_batch(selfplay, teacher, batch_size, teacher_ratio, rng):
    """Use a separate teacher buffer so heuristic labels cannot evict game outcomes."""
    if not selfplay:
        return rng.sample(teacher, min(batch_size, len(teacher)))
    if not teacher or teacher_ratio == 0:
        return rng.sample(selfplay, min(batch_size, len(selfplay)))
    teacher_count = min(round(batch_size * teacher_ratio), len(teacher))
    selfplay_count = min(batch_size - teacher_count, len(selfplay))
    teacher_count = min(batch_size - selfplay_count, len(teacher))
    return rng.sample(selfplay, selfplay_count) + rng.sample(teacher, teacher_count)
