"""Multi-source A* for the cheapest pawn promotion route on a static board."""
from heapq import heapify, heappop, heappush

import chess


def promotion_route(board, color):
    """Return minimum weighted cost and number of squares examined, for one side.

    Each edge advances one pawn at a cost of 1, plus 1 on an attacked destination.
    Occupancy and opposing attacks are frozen at the evaluated leaf position.
    """
    goal_rank, home_rank, step = (7, 1, 8) if color else (0, 6, -8)

    def lower_bound(square):
        rank = chess.square_rank(square)
        # Ignore obstacles, danger and the need to capture. Allow the initial double step.
        return abs(goal_rank - rank) - int(rank == home_rank)

    best = {square: 0 for square in board.pieces(chess.PAWN, color)}
    frontier = [(lower_bound(square), 0, square) for square in best]
    heapify(frontier)
    examined = 0
    capturable = board.occupied_co[not color] & ~board.kings
    while frontier:
        _, cost, square = heappop(frontier)
        if cost != best[square]:
            continue
        examined += 1
        if chess.square_rank(square) == goal_rank:
            return cost, examined
        targets = chess.BB_PAWN_ATTACKS[color][square] & capturable
        forward = square + step
        if not board.occupied & chess.BB_SQUARES[forward]:
            targets |= chess.BB_SQUARES[forward]
            if chess.square_rank(square) == home_rank and not board.occupied & chess.BB_SQUARES[forward + step]:
                targets |= chess.BB_SQUARES[forward + step]
        for target in chess.scan_forward(targets):
            new_cost = cost + 1 + int(board.is_attacked_by(not color, target))
            if target not in best or new_cost < best[target]:
                best[target] = new_cost
                heappush(frontier, (new_cost + lower_bound(target), new_cost, target))
    return None, examined
