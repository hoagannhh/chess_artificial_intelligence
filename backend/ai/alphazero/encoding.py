"""Absolute board coordinates, eight historical positions and 73 actions per square."""
import chess
import torch

HISTORY = 8
PLANES = HISTORY * 14 + 8
ACTIONS = 64 * 73
DIRECTIONS = ((0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1))
KNIGHTS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))


def encode(board):
    """Include history and rule state. The original board and stack are untouched."""
    state = torch.zeros(PLANES, 8, 8)
    past = board.copy(stack=True)
    for age in range(HISTORY):
        offset = age * 14
        for square, piece in past.piece_map().items():
            plane = offset + (0 if piece.color else 6) + piece.piece_type - 1
            state[plane, chess.square_rank(square), chess.square_file(square)] = 1
        state[offset + 12].fill_(past.is_repetition(2))
        state[offset + 13].fill_(past.is_repetition(3))
        if not past.move_stack:
            break
        past.pop()
    offset = HISTORY * 14
    values = (board.turn, board.has_kingside_castling_rights(chess.WHITE),
              board.has_queenside_castling_rights(chess.WHITE),
              board.has_kingside_castling_rights(chess.BLACK),
              board.has_queenside_castling_rights(chess.BLACK),
              min(board.halfmove_clock, 150) / 150, min(board.fullmove_number, 300) / 300)
    for index, value in enumerate(values):
        state[offset + index].fill_(value)
    if board.ep_square is not None:
        state[offset + 7, chess.square_rank(board.ep_square), chess.square_file(board.ep_square)] = 1
    return state


def action_index(move):
    """Queen promotion uses its ray. Underpromotions have nine dedicated planes."""
    dx = chess.square_file(move.to_square) - chess.square_file(move.from_square)
    dy = chess.square_rank(move.to_square) - chess.square_rank(move.from_square)
    if move.promotion in (chess.KNIGHT, chess.BISHOP, chess.ROOK):
        plane = 64 + (move.promotion - chess.KNIGHT) * 3 + dx + 1
    elif (dx, dy) in KNIGHTS:
        plane = 56 + KNIGHTS.index((dx, dy))
    else:
        distance = max(abs(dx), abs(dy))
        direction = (dx // distance, dy // distance)
        plane = DIRECTIONS.index(direction) * 7 + distance - 1
    return move.from_square * 73 + plane
