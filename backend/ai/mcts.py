"""Adversarial UCT MCTS with bounded random rollouts and heuristic leaf reward.

Values are always from White's perspective. Selection reverses exploitation
at Black nodes. A rollout cutoff uses tanh(centipawns / 600), not a win probability.
"""
from dataclasses import dataclass, field
from math import log, sqrt, tanh
from random import Random
from time import perf_counter
import chess
from backend.ai.search import SearchResult, evaluate


@dataclass
class Node:
    move: chess.Move | None = None
    visits: int = 0
    total: float = 0.0
    children: list = field(default_factory=list)
    untried: list | None = None


def choose_child(node, white_to_move, exploration=sqrt(2)):
    sign = 1 if white_to_move else -1
    def uct(child):
        if not child.visits:
            return float('inf')
        return sign * child.total / child.visits + exploration * sqrt(log(max(1, node.visits)) / child.visits)
    return max(node.children, key=uct)


def outcome_reward(board):
    outcome = board.outcome()
    if outcome is None:
        return None
    return 0.0 if outcome.winner is None else (1.0 if outcome.winner else -1.0)


def search_mcts(position, depth, time_limit_ms, *, max_iterations=4096, seed=0):
    # Called after shared option validation by search(). Board state never escapes.
    start = perf_counter()
    deadline = start + time_limit_ms / 1000
    rng = Random(seed)
    root = Node()
    limit = depth * 8
    nodes = 1
    tree_depth = 0
    iterations = 0
    expired = False
    terminal = outcome_reward(position)
    legal = sorted(position.legal_moves, key=lambda move: move.uci()) if terminal is None else []
    chosen = legal[0] if legal else None
    value = terminal

    def result():
        return SearchResult(chosen.uci() if chosen else None, None, 0, depth,
                            nodes, 0, round((perf_counter() - start) * 1000, 2), expired, 'mcts',
                            iterations=iterations, rollout_limit=limit, tree_depth=tree_depth,
                            mean_reward=value)

    if not legal:
        return result()
    # Cheap tactical safeguard: a known mate-in-one beats sampled estimates.
    probe = position.copy(stack=True)
    for move in legal:
        if perf_counter() >= deadline:
            expired = True
            return result()
        probe.push(move)
        try:
            if probe.is_checkmate():
                chosen = move
                value = 1.0 if position.turn else -1.0
                return result()
        finally:
            probe.pop()
    root.untried = legal[:]
    rng.shuffle(root.untried)
    for _ in range(max_iterations):
        if perf_counter() >= deadline:
            expired = True
            break
        board = position.copy(stack=True)
        node = root
        path = [root]
        reward = None
        while True:
            if perf_counter() >= deadline:
                expired = True
                break
            reward = outcome_reward(board)
            if reward is not None:
                break
            if node.untried is None:
                node.untried = sorted(board.legal_moves, key=lambda move: move.uci())
                rng.shuffle(node.untried)
            if node.untried:
                move = node.untried.pop()
                board.push(move)
                child = Node(move)
                node.children.append(child)
                node = child
                path.append(node)
                nodes += 1
                break
            node = choose_child(node, board.turn)
            board.push(node.move)
            path.append(node)
        tree_depth = max(tree_depth, len(path) - 1)
        if expired:
            break
        # Expand one node, then simulate at most limit additional half-moves.
        for rollout_ply in range(limit + 1):
            if perf_counter() >= deadline:
                expired = True
                break
            reward = outcome_reward(board)
            if reward is not None:
                break
            if rollout_ply == limit:
                reward = tanh(evaluate(board) / 600.0)
                break
            board.push(rng.choice(list(board.legal_moves)))
        if expired:
            break  # Never backpropagate a partially evaluated simulation.
        for visited in path:
            visited.visits += 1
            visited.total += reward
        iterations += 1
    visited_children = [child for child in root.children if child.visits]
    if visited_children:
        sign = 1 if position.turn else -1
        best = max(visited_children, key=lambda child: (child.visits, sign * child.total / child.visits))
        chosen = best.move
        value = round(best.total / best.visits, 6)
    return result()
