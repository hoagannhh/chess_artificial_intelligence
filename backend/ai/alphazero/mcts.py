"""PUCT search. Each node stores values from its own side-to-move perspective."""
from dataclasses import dataclass, field
from math import sqrt
from time import perf_counter


@dataclass
class Node:
    prior: float = 1.0
    visits: int = 0
    total: float = 0.0
    children: dict = field(default_factory=dict)

    @property
    def mean(self):
        return self.total / self.visits if self.visits else 0.0


@dataclass
class TreeResult:
    policy: dict
    value: float
    simulations: int
    nodes: int
    tree_depth: int
    timed_out: bool


def terminal_value(board):
    # Match the app's policy of claiming an available draw.
    outcome = board.outcome(claim_draw=True)
    if outcome is None:
        return None
    if outcome.winner is None:
        return 0.0
    return 1.0 if outcome.winner == board.turn else -1.0


def select_child(node, exploration=1.5):
    def score(item):
        child = item[1]
        # Child values belong to the opposing player.
        return -child.mean + exploration * child.prior * sqrt(max(1, node.visits)) / (1 + child.visits)
    return max(node.children.items(), key=score)


def run_search(position, evaluator, simulations=64, *, deadline=None, rng=None):
    if simulations < 1:
        raise ValueError('Simulations must be positive')
    end = terminal_value(position)
    if end is not None:
        return TreeResult({}, end, 0, 1, 0, False)
    # A proven mate is exact rule information, even if the network gives it no prior.
    probe = position.copy(stack=True)
    checked = 0
    for move in list(probe.legal_moves):
        if deadline is not None and perf_counter() >= deadline:
            break
        probe.push(move)
        mate = probe.is_checkmate()
        probe.pop()
        checked += 1
        if mate:
            return TreeResult({move: 1.0}, 1.0, 0, checked + 1, 1, False)
    root = Node()
    priors, initial_value = evaluator(position)
    root.children = {move: Node(prior) for move, prior in priors.items()}
    if rng is not None:
        noise = [rng.gammavariate(0.3, 1.0) for _ in priors]
        total = sum(noise)
        for child, sample in zip(root.children.values(), noise):
            child.prior = 0.75 * child.prior + 0.25 * sample / total
    nodes = 1 + len(root.children)
    completed = tree_depth = 0
    expired = False
    for _ in range(simulations):
        if deadline is not None and perf_counter() >= deadline:
            expired = True
            break
        board = position.copy(stack=True)
        node = root
        path = [node]
        while node.children:
            move, node = select_child(node)
            board.push(move)
            path.append(node)
            if deadline is not None and perf_counter() >= deadline:
                expired = True
                break
        if expired:
            break
        value = terminal_value(board)
        if value is None:
            priors, value = evaluator(board)
            node.children = {move: Node(prior) for move, prior in priors.items()}
            nodes += len(node.children)
        # A single neural forward pass is indivisible and may slightly overrun the budget.
        for visited in reversed(path):
            visited.visits += 1
            visited.total += value
            value = -value
        tree_depth = max(tree_depth, len(path) - 1)
        completed += 1
    visits = sum(child.visits for child in root.children.values())
    policy = {move: child.visits / visits for move, child in root.children.items()} if visits else {
        move: child.prior for move, child in root.children.items()}
    return TreeResult(policy, root.mean if completed else initial_value, completed,
                      nodes, tree_depth, expired)
