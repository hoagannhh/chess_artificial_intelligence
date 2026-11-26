"""Search entry point for the supported chess AIs.

Scores are centipawns from White's perspective. Iterative deepening returns
only completed depths; timeout before depth one uses a legal fallback move.
"""
from dataclasses import asdict, dataclass
from time import perf_counter
import chess
from backend.ai.pawn_routes import promotion_route

VALUES = {chess.PAWN: 100, chess.KNIGHT: 320, chess.BISHOP: 330,
          chess.ROOK: 500, chess.QUEEN: 900, chess.KING: 0}
MATE = 100000
BASE_ALGORITHMS = ('minimax', 'alphabeta', 'pvs', 'mcts', 'astar_ab', 'expectimax', 'alphabeta_q')
NEURAL_NAMES = {'alphazero': 'AlphaZero', 'alphazero_teacher': 'AlphaZero có thầy'}
ALGORITHMS = (*BASE_ALGORITHMS, *NEURAL_NAMES)
QUIESCENCE_PLIES = 4


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
    score: int | float | None
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
    route_nodes: int = 0
    qnodes: int = 0
    model_id: str = ''
    training_method: str = ''

    def to_dict(self):
        return asdict(self)


class SearchTimeout(Exception):
    pass


def search(position, algorithm='alphabeta', depth=3, time_limit_ms=1000):
    if algorithm not in ALGORITHMS:
        raise ValueError('Algorithm must be one of: ' + ', '.join(ALGORITHMS))
    if type(depth) is not int or not 1 <= depth <= 5:
        raise ValueError('Depth must be an integer from 1 to 5')
    if type(time_limit_ms) is not int or not 50 <= time_limit_ms <= 2000:
        raise ValueError('Time limit must be 50 to 2000 ms')
    if algorithm == 'mcts':
        from backend.ai.mcts import search_mcts
        return search_mcts(position, depth, time_limit_ms)
    if algorithm in NEURAL_NAMES:
        try:
            from backend.ai.alphazero.engine import search_alphazero
        except ImportError as error:
            raise ValueError('AlphaZero needs PyTorch. Install backend/ai/alphazero/requirements.txt.') from error
        return search_alphazero(position, depth, time_limit_ms, algorithm=algorithm)
    board = position.copy(stack=True)
    start = perf_counter()
    deadline = start + time_limit_ms / 1000
    nodes = cutoffs = researches = route_nodes = qnodes = 0
    root_color = board.turn
    pruning = algorithm in ('alphabeta', 'pvs', 'astar_ab', 'alphabeta_q')

    def leaf_score():
        nonlocal route_nodes
        score = evaluate(board)
        if algorithm == 'astar_ab':
            for color in (chess.WHITE, chess.BLACK):
                cost, examined = promotion_route(board, color)
                route_nodes += examined
                if cost is not None:
                    bonus = 12 * max(0, 7 - cost)
                    score += bonus if color else -bonus
        return score

    def terminal(ply):
        outcome = board.outcome()
        if outcome is None:
            return None
        if outcome.winner is None:
            return 0
        return (MATE - ply) * (1 if outcome.winner else -1)

    def ordered(moves=None):
        def priority(move):
            victim = board.piece_type_at(move.to_square)
            capture = VALUES.get(victim, 0) + (100 if board.is_en_passant(move) else 0)
            return (-(capture * 10 + VALUES.get(move.promotion, 0)), move.uci())
        return sorted(board.legal_moves if moves is None else moves, key=priority)

    def visit(remaining, alpha, beta, ply):
        nonlocal nodes, cutoffs, researches, qnodes
        if perf_counter() >= deadline:
            raise SearchTimeout
        nodes += 1
        quiescence = algorithm == 'alphabeta_q' and remaining <= 0
        if quiescence:
            qnodes += 1
        end = terminal(ply)
        if end is not None:
            return end, None
        if remaining <= 0 and (not quiescence or remaining <= -QUIESCENCE_PLIES):
            return leaf_score(), None
        maximizing = board.turn == chess.WHITE
        chance = algorithm == 'expectimax' and board.turn != root_color
        total = 0.0
        best = -MATE * 2 if maximizing else MATE * 2
        chosen = None
        if quiescence and not board.is_check():
            # Stand pat unless a capture or promotion improves this position.
            best = evaluate(board)
            if maximizing:
                alpha = max(alpha, best)
            else:
                beta = min(beta, best)
            if alpha >= beta:
                cutoffs += 1
                return best, None
            candidates = ordered(m for m in board.legal_moves if m.promotion or board.is_capture(m))
        else:
            # In check every legal evasion matters, including a quiet king move or block.
            candidates = ordered()
        for move in candidates:
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
            if chance:
                total += score
                continue
            if (maximizing and score > best) or (not maximizing and score < best):
                best, chosen = score, move
            if pruning:
                if maximizing:
                    alpha = max(alpha, best)
                else:
                    beta = min(beta, best)
                if alpha >= beta:
                    cutoffs += 1
                    break
        if chance:
            return total / len(candidates), None
        return best, chosen

    end = terminal(0)
    moves = ordered() if end is None else []
    chosen = moves[0] if moves else None
    score = leaf_score() if end is None else end
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
                        nodes, cutoffs, round((perf_counter() - start) * 1000, 2), timed_out,
                        algorithm, researches=researches, route_nodes=route_nodes, qnodes=qnodes)
