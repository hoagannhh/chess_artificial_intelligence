"""Minimax, alpha-beta, PVS and MCTS entry point.

Scores are centipawns from White's perspective. Iterative deepening returns
only completed depths; timeout before depth one uses a legal fallback move.
"""
from dataclasses import asdict, dataclass
from time import perf_counter
import chess

VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
          chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
MATE = 100000
ALGORITHMS = ('minimax', 'alphabeta', 'pvs', 'mcts')


def evaluate(board):
    score = 0
    for square, piece in board.piece_map().items():
        rank = chess.square_rank(square) if piece.color else 7 - chess.square_rank(square)
        file = chess.square_file(square)
        center = 7 - abs(2 * file - 7) - abs(2 * rank - 7)
        bonus = 0
        if piece.piece_type == chess.PAWN:
            bonus = rank * 8
        elif piece.piece_type in (chess.KNIGHT, chess.BISHOP):
            bonus = center * 5
        score += (VALUES[piece.piece_type] + bonus) * (1 if piece.color else -1)
    return score


@dataclass
class SearchResult:
    move: str | None
    score: int | None
    depth: int
    requested_depth: int
    nodes: int
    cutoffs: int
    elapsed_ms: float
    timed_out: bool
    algorithm: str
    researches: int = 0
    iterations: int = 0
    rollout_limit: int = 0
    tree_depth: int = 0
    mean_reward: float | None = None

    def to_dict(self):
        return asdict(self)


class SearchTimeout(Exception):
    pass


def search(position, algorithm='alphabeta', depth=3, time_limit_ms=1000):
    if algorithm not in ALGORITHMS:
        raise ValueError('Algorithm must be minimax, alphabeta, pvs or mcts')
    if type(depth) is not int or not 1 <= depth <= 5:
        raise ValueError('Depth must be an integer from 1 to 5')
    if type(time_limit_ms) is not int or not 50 <= time_limit_ms <= 2000:
        raise ValueError('Time limit must be 50 to 2000 ms')
    if algorithm == 'mcts':
        from backend.ai.mcts import search_mcts
        return search_mcts(position, depth, time_limit_ms)
    board = position.copy(stack=True)
    start = perf_counter()
    deadline = start + time_limit_ms / 1000
    nodes = cutoffs = researches = 0

    def terminal(ply):
        outcome = board.outcome()
        if outcome is None:
            return None
        if outcome.winner is None:
            return 0
        return (MATE - ply) * (1 if outcome.winner else -1)

    def ordered():
        # Both algorithms use identical ordering to make comparisons meaningful.
        def priority(move):
            victim = board.piece_type_at(move.to_square)
            capture = VALUES.get(victim, 0) + (100 if board.is_en_passant(move) else 0)
            return (-(capture * 10 + VALUES.get(move.promotion, 0)), move.uci())
        return sorted(board.legal_moves, key=priority)

    def visit(remaining, alpha, beta, ply):
        nonlocal nodes, cutoffs, researches
        if perf_counter() >= deadline:
            raise SearchTimeout
        nodes += 1
        end = terminal(ply)
        if end is not None:
            return end, None
        if remaining == 0:
            return evaluate(board), None
        maximizing = board.turn == chess.WHITE
        best = -MATE * 2 if maximizing else MATE * 2
        chosen = None
        for move in ordered():
            board.push(move)
            try:
                if algorithm == 'pvs' and chosen is not None:
                    low, high = (alpha, alpha + 1) if maximizing else (beta - 1, beta)
                    score, _ = visit(remaining - 1, low, high, ply + 1)
                    if alpha < score < beta:
                        researches += 1
                        score, _ = visit(remaining - 1, alpha, beta, ply + 1)
                else:
                    score, _ = visit(remaining - 1, alpha, beta, ply + 1)
            finally:
                board.pop()
            if chosen is None or (score > best if maximizing else score < best):
                best, chosen = score, move
            if algorithm in ('alphabeta', 'pvs'):
                if maximizing:
                    alpha = max(alpha, best)
                else:
                    beta = min(beta, best)
                if alpha >= beta:
                    cutoffs += 1
                    break
        return best, chosen

    end = terminal(0)
    moves = ordered() if end is None else []
    chosen = moves[0] if moves else None
    score = evaluate(board) if end is None else end
    completed = 0
    timed_out = False
    if moves:
        for current in range(1, depth + 1):
            try:
                value, move = visit(current, -MATE * 2, MATE * 2, 0)
            except SearchTimeout:
                timed_out = True
                break
            chosen, score, completed = move, value, current
    return SearchResult(chosen.uci() if chosen else None, score, completed, depth,
                        nodes, cutoffs, round((perf_counter() - start) * 1000, 2), timed_out, algorithm, researches=researches)
