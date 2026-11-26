"""App adapter. Cache a loaded checkpoint and reload when the selected file changes."""
from time import perf_counter
import torch

from backend.ai.search import SearchResult
from .mcts import run_search
from .network import Evaluator, load_checkpoint, model_path

_cache = {}


def get_evaluator(algorithm='alphazero'):
    path = model_path(algorithm)
    if not path.is_file():
        variable = 'CHESS_AZ_TEACHER_MODEL' if algorithm == 'alphazero_teacher' else 'CHESS_AZ_PLAIN_MODEL'
        raise ValueError(f'AlphaZero model missing for {algorithm}: {path}. '
                         f'Train this branch or set {variable} to its checkpoint.')
    stat = path.stat()
    key = (str(path), stat.st_mtime_ns, stat.st_size)
    cached = _cache.get(algorithm)
    if cached is None or key != cached[0]:
        torch.set_num_threads(1)
        model, data = load_checkpoint(path)
        cached = (key, Evaluator(model), data['model_id'], data.get('training_method', 'self_play'))
        _cache[algorithm] = cached
    return cached[1:]


def search_alphazero(position, depth, time_limit_ms, *, algorithm='alphazero'):
    evaluator, identifier, method = get_evaluator(algorithm)
    start = perf_counter()
    result = run_search(position, evaluator, simulations=depth * 64,
                        deadline=start + time_limit_ms / 1000)
    move = max(result.policy, key=result.policy.get) if result.policy else None
    white_value = result.value if position.turn else -result.value
    return SearchResult(move.uci() if move else None, None, 0, depth, result.nodes, 0,
                        round((perf_counter() - start) * 1000, 2), result.timed_out, algorithm,
                        iterations=result.simulations, tree_depth=result.tree_depth,
                        mean_reward=white_value, model_id=identifier, training_method=method)
