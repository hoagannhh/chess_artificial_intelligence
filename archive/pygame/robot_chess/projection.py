"""Shared board projection for drawing and inverse mouse picking.

An oblique diamond gives depth without introducing a 3D runtime.
Coordinates are in board space, with (0, 0) at the far left corner.
"""
import math


def project(col, row):
    return (350 + 43 * col - 38 * row, 176 + 22 * col + 44 * row)


def unproject(position):
    x, y = position[0] - 350, position[1] - 176
    determinant = 43 * 44 + 38 * 22
    col = (44 * x + 38 * y) / determinant
    row = (-22 * x + 43 * y) / determinant
    if 0 <= col < 8 and 0 <= row < 8:
        return math.floor(col), math.floor(row)
    return None


def polygon(col, row, inset=0):
    return [project(col + inset, row + inset),
            project(col + 1 - inset, row + inset),
            project(col + 1 - inset, row + 1 - inset),
            project(col + inset, row + 1 - inset)]
