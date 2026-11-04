"""Asset-backed 2.5D renderer. Atlas is sliced in memory, originals preserved."""
from pathlib import Path
import random

import chess
import pygame

from .projection import project, polygon

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "scifi"
ORDER = (chess.KING, chess.QUEEN, chess.BISHOP, chess.KNIGHT, chess.ROOK, chess.PAWN)
CYAN, ORANGE = (92, 221, 249), (255, 168, 80)


class ArenaArt:
    def __init__(self, size):
        atlas = pygame.image.load(str(ASSETS / "units.png")).convert_alpha()
        self.originals = {}
        self.scaled = {}
        width, height = atlas.get_size()
        for row, color in enumerate((chess.WHITE, chess.BLACK)):
            for col, kind in enumerate(ORDER):
                left, top = round(col * width / 6), round(row * height / 2)
                right, bottom = round((col + 1) * width / 6), round((row + 1) * height / 2)
                cell = atlas.subsurface((left, top, right - left, bottom - top))
                bounds = cell.get_bounding_rect(min_alpha=24)
                if not bounds.width or not bounds.height:
                    raise ValueError(f"Empty sprite atlas cell: {row}, {col}")
                self.originals[color, kind] = cell.subsurface(bounds).copy()
        self.background = pygame.transform.smoothscale(
            pygame.image.load(str(ASSETS / "orbital.png")).convert(), size)
        # Tint background to keep the playable board and UI dominant.
        shade = pygame.Surface(size, pygame.SRCALPHA)
        shade.fill((6, 15, 26, 100))
        self.background.blit(shade, (0, 0))
        self.deck = pygame.Surface(size, pygame.SRCALPHA)
        self._deck()

    def sprite(self, color, kind, width, height):
        key = color, kind, width, height
        if key not in self.scaled:
            source = self.originals[color, kind]
            factor = min(width / source.get_width(), height / source.get_height())
            self.scaled[key] = pygame.transform.smoothscale(source,
                (max(1, round(source.get_width() * factor)), max(1, round(source.get_height() * factor))))
        return self.scaled[key]

    def placement(self, square, piece, coords):
        col, row = coords(square)
        x, y = project(col + 0.5, row + 0.5)
        depth = (col + row) / 14
        width = round(52 + 10 * depth)
        height = round((69 if piece.piece_type == chess.PAWN else 88) + 10 * depth)
        sprite = self.sprite(piece.color, piece.piece_type, width, height)
        return sprite, sprite.get_rect(midbottom=(round(x), round(y + 8)))

    def draw_units(self, screen, board, coords):
        # Sort by screen-space feet, not chess rank, for oblique overlapping sprites.
        order = sorted(board.piece_map(), key=lambda s: project(*coords(s))[1])
        for square in order:
            piece = board.piece_at(square)
            sprite, rect = self.placement(square, piece, coords)
            shadow = pygame.Surface((72, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 4, 12, 125), (5, 5, 62, 16))
            screen.blit(shadow, (rect.centerx - 30, rect.bottom - 12))
            screen.blit(sprite, rect)

    def pick_unit(self, pos, board, coords):
        order = sorted(board.piece_map(), key=lambda s: project(*coords(s))[1], reverse=True)
        for square in order:
            piece = board.piece_at(square)
            sprite, rect = self.placement(square, piece, coords)
            if rect.collidepoint(pos):
                local = pos[0] - rect.x, pos[1] - rect.y
                if sprite.get_at(local).a > 64:
                    return square
        return None

    def _deck(self):
        s = self.deck
        outer = [project(-0.18, -0.18), project(8.18, -0.18), project(8.18, 8.18), project(-0.18, 8.18)]
        pygame.draw.polygon(s, (0, 4, 10, 160), [(x + 6, y + 44) for x, y in outer])
        for a, b, color in ((1, 2, (31, 43, 57)), (2, 3, (22, 34, 46))):
            p, q = outer[a], outer[b]
            pygame.draw.polygon(s, color, [p, q, (q[0], q[1] + 28), (p[0], p[1] + 28)])
            pygame.draw.line(s, (88, 109, 124), (p[0], p[1] + 27), (q[0], q[1] + 27), 2)
            glow = ORANGE if a == 1 else CYAN
            for i in range(8):
                t0, t1 = (i + 0.12) / 8, (i + 0.8) / 8
                start = (p[0] + (q[0] - p[0]) * t0, p[1] + (q[1] - p[1]) * t0 + 16)
                end = (p[0] + (q[0] - p[0]) * t1, p[1] + (q[1] - p[1]) * t1 + 16)
                pygame.draw.line(s, tuple(c // 3 for c in glow), start, end, 8)
                pygame.draw.line(s, glow, start, end, 3)
        pygame.draw.polygon(s, (59, 74, 87), outer)
        pygame.draw.polygon(s, (128, 149, 160), outer, 2)
        rng = random.Random(19)
        for row in range(8):
            for col in range(8):
                light = (col + row) % 2 == 1
                base = (132, 143, 151) if light else (47, 59, 73)
                poly = polygon(col, row, 0.015)
                pygame.draw.polygon(s, base, poly)
                pygame.draw.line(s, tuple(min(255, c + 24) for c in base), poly[0], poly[1], 1)
                pygame.draw.line(s, (24, 32, 41), poly[2], poly[3], 2)
                # Small seams, worn metal scratches and corner fasteners.
                for _ in range(9):
                    u, v = rng.uniform(.1, .8), rng.uniform(.1, .9)
                    delta = rng.randint(-12, 10)
                    ink = tuple(max(0, min(255, c + delta)) for c in base)
                    pygame.draw.line(s, ink, project(col + u, row + v),
                                     project(col + min(u + .18, .96), row + v), 1)
                for u, v in ((.08, .08), (.92, .92)):
                    x, y = project(col + u, row + v)
                    pygame.draw.circle(s, (30, 40, 51), (round(x), round(y)), 2)
                    pygame.draw.circle(s, (173, 184, 190), (round(x), round(y - 1)), 1)
