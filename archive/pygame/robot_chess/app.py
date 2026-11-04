"""Playable sci-fi chess: sprite-backed 2.5D board and tactical HUD."""
import argparse
from pathlib import Path

import chess
import pygame

from .game import Game
from .projection import project, unproject, polygon
from .art import ArenaArt, ORDER

WIDTH, HEIGHT = 1180, 820
CYAN, ORANGE = (79, 221, 238), (255, 164, 82)
BG, PANEL, TEXT, MUTED = (10, 16, 26), (20, 30, 44), (224, 235, 245), (139, 161, 181)
NAMES = {1: "PAWN", 2: "KNIGHT", 3: "BISHOP", 4: "ROOK", 5: "QUEEN", 6: "KING"}


class App:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Robot Chess | Python edition")
        self.clock = pygame.time.Clock()
        self.fonts = {size: pygame.font.SysFont("segoeui", size) for size in (14, 16, 18, 22, 28, 36)}
        self.art = ArenaArt((WIDTH, HEIGHT))
        self.game = Game()
        self.selected = None
        self.promotions = []
        self.confirm_reset = False
        self.flipped = False
        self.scroll = 0
        self.running = True
        self.buttons = [(pygame.Rect(728, 572, 192, 44), "NEW GAME", self.ask_reset),
                        (pygame.Rect(936, 572, 192, 44), "UNDO", self.undo),
                        (pygame.Rect(728, 628, 192, 44), "FLIP BOARD", self.flip),
                        (pygame.Rect(936, 628, 192, 44), "CLAIM DRAW", self.claim)]

    def text(self, text, pos, size=18, color=TEXT, center=False):
        rendered = self.fonts[size].render(text, True, color)
        self.screen.blit(rendered, rendered.get_rect(center=pos) if center else pos)

    def board_coords(self, square):
        file, rank = chess.square_file(square), chess.square_rank(square)
        return (7 - file, rank) if self.flipped else (file, 7 - rank)

    def square_rect(self, square):
        col, row = self.board_coords(square)
        x, y = project(col + 0.5, row + 0.5)
        return pygame.Rect(round(x) - 32, round(y) - 30, 64, 60)

    def square_at(self, pos):
        coords = unproject(pos)
        if coords is None:
            return None
        col, row = coords
        return chess.square(7 - col, row) if self.flipped else chess.square(col, 7 - row)

    def clear_selection(self):
        self.selected = None
        self.promotions = []
        self.scroll = 0

    def ask_reset(self):
        self.confirm_reset = True

    def undo(self):
        self.game.undo()
        self.clear_selection()

    def flip(self):
        self.flipped = not self.flipped

    def claim(self):
        self.game.claim_draw()
        self.clear_selection()

    def commit(self, move):
        self.game.play(move)
        self.clear_selection()

    def click_square(self, square):
        if self.game.finished:
            return
        if square == self.selected:
            self.selected = None
            return
        if self.selected is not None:
            candidates = [m for m in self.game.moves_from(self.selected) if m.to_square == square]
            if candidates:
                if candidates[0].promotion:
                    self.promotions = candidates
                else:
                    self.commit(candidates[0])
                return
        piece = self.game.board.piece_at(square)
        self.selected = square if piece and piece.color == self.game.board.turn else None

    def promotion_boxes(self):
        return [(pygame.Rect(356 + i * 120, 382, 108, 90), kind)
                for i, kind in enumerate((chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT))]

    def event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.confirm_reset = False
                self.clear_selection()
            elif not self.promotions and not self.confirm_reset:
                if event.key == pygame.K_u:
                    self.undo()
                elif event.key == pygame.K_f:
                    self.flip()
                elif event.key == pygame.K_n:
                    self.ask_reset()
        if event.type == pygame.MOUSEWHEEL and not (self.promotions or self.confirm_reset):
            total = (len(self.game.history) + 1) // 2
            self.scroll = max(0, min(max(0, total - 3), self.scroll + event.y))
        if event.type != pygame.MOUSEBUTTONDOWN or event.button != 1:
            return
        if self.confirm_reset:
            if pygame.Rect(392, 420, 180, 48).collidepoint(event.pos):
                self.game.reset()
                self.clear_selection()
                self.confirm_reset = False
            elif pygame.Rect(608, 420, 180, 48).collidepoint(event.pos):
                self.confirm_reset = False
            return
        if self.promotions:
            for rect, kind in self.promotion_boxes():
                if rect.collidepoint(event.pos):
                    self.commit(next(m for m in self.promotions if m.promotion == kind))
                    break
            return
        for rect, _, action in self.buttons:
            if rect.collidepoint(event.pos):
                action()
                return
        square = self.square_at(event.pos)
        # Legal destination tiles take priority; otherwise allow clicking the
        # visible alpha silhouette, including heads extending above their tile.
        legal_targets = {m.to_square for m in self.game.moves_from(self.selected)} if self.selected is not None else set()
        near_base = False
        if square is not None and self.game.board.piece_at(square):
            center = self.square_rect(square).center
            near_base = (center[0] - event.pos[0]) ** 2 + (center[1] - event.pos[1]) ** 2 <= 144
        if square not in legal_targets and not near_base:
            unit = self.art.pick_unit(event.pos, self.game.board, self.board_coords)
            if unit is not None:
                square = unit
        if square is not None:
            self.click_square(square)

    def draw_board(self):
        self.screen.blit(self.art.deck, (0, 0))
        board = self.game.board
        last = board.peek() if board.move_stack else None
        targets = {m.to_square for m in self.game.moves_from(self.selected)} if self.selected is not None else set()
        hover = self.square_at(pygame.mouse.get_pos()) if not (self.promotions or self.confirm_reset) else None
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for square in chess.SQUARES:
            col, row = self.board_coords(square)
            poly = polygon(col, row, 0.025)
            piece = board.piece_at(square)
            if last and square in (last.from_square, last.to_square):
                pygame.draw.polygon(overlay, (*CYAN, 38), poly)
            if piece and piece.piece_type == chess.KING and piece.color == board.turn and board.is_check():
                pygame.draw.polygon(overlay, (255, 65, 75, 130), poly)
            if square == hover:
                pygame.draw.polygon(overlay, (210, 237, 248, 180), poly, 1)
            if square == self.selected:
                pygame.draw.polygon(overlay, (*CYAN, 70), poly)
                pygame.draw.polygon(overlay, (*CYAN, 255), poly, 2)
            if square in targets:
                if piece:
                    pygame.draw.polygon(overlay, (*ORANGE, 230), poly, 3)
                else:
                    x, y = project(col + .5, row + .5)
                    pygame.draw.ellipse(overlay, (*CYAN, 35), (x - 17, y - 9, 34, 18))
                    pygame.draw.ellipse(overlay, (*CYAN, 255), (x - 14, y - 7, 28, 14), 2)
        self.screen.blit(overlay, (0, 0))
        self.art.draw_units(self.screen, board, self.board_coords)
        for index in range(8):
            x, y = project(index + .5, 8.25)
            self.text("abcdefgh"[7 - index if self.flipped else index], (x, y + 15), 14, TEXT, True)
            x, y = project(-.3, index + .5)
            self.text(str(index + 1 if self.flipped else 8 - index), (x - 7, y), 14, TEXT, True)

    def unit_gallery(self):
        selected_piece = self.game.board.piece_at(self.selected) if self.selected is not None else None
        faction = selected_piece.color if selected_piece else self.game.board.turn
        accent = CYAN if faction else ORANGE
        for index, kind in enumerate(ORDER):
            col, row = index % 3, index // 3
            rect = pygame.Rect(730 + col * 134, 224 + row * 120, 126, 114)
            pygame.draw.rect(self.screen, (22, 31, 42), rect, border_radius=5)
            if selected_piece and selected_piece.piece_type == kind:
                pygame.draw.rect(self.screen, accent, rect, 1, border_radius=5)
            sprite = self.art.sprite(faction, kind, 100, 85)
            self.screen.blit(sprite, sprite.get_rect(midbottom=(rect.centerx, rect.y + 88)))
            self.text(NAMES[kind], (rect.centerx, rect.bottom - 12), 14, TEXT, True)

    def draw(self):
        self.screen.blit(self.art.background, (0, 0))
        header = pygame.Surface((WIDTH, 100), pygame.SRCALPHA)
        header.fill((5, 12, 20, 205))
        self.screen.blit(header, (0, 0))
        pygame.draw.line(self.screen, (68, 102, 119), (28, 99), (1152, 99))
        self.text("ROBOT CHESS", (32, 17), 36)
        self.text("O R B I T A L   /   A R E N A", (34, 66), 14, CYAN)
        self.text("LOCAL DUEL", (735, 24), 22)
        self.text("CYAN  vs  EMBER   /   TWO PLAYERS", (735, 61), 14, MUTED)
        self.draw_board()
        footer = pygame.Surface((660, 46), pygame.SRCALPHA)
        footer.fill((7, 15, 23, 210))
        self.screen.blit(footer, (28, 759))
        self.text("SELECT UNIT  /  CHOOSE A HIGHLIGHTED TILE", (42, 768), 14, TEXT)
        self.text("WHITE: CYAN    BLACK: EMBER", (42, 787), 14, MUTED)
        pygame.draw.rect(self.screen, (12, 20, 29), (708, 112, 440, 636), border_radius=8)
        pygame.draw.rect(self.screen, (59, 82, 98), (708, 112, 440, 636), 1, border_radius=8)
        title, detail = self.game.status()
        accent = CYAN if self.game.board.turn else ORANGE
        pygame.draw.rect(self.screen, accent, (708, 133, 3, 40))
        self.text(title, (728, 130), 28, accent)
        self.text(detail, (728, 174), 16, MUTED)
        self.text("UNIT ROSTER", (730, 201), 14, MUTED)
        self.unit_gallery()
        pygame.draw.line(self.screen, (47, 63, 82), (728, 466), (1128, 466))
        self.text("MOVE LOG", (728, 472), 14, MUTED)
        self.text("Scroll to review", (1008, 472), 14, MUTED)
        rows = [self.game.history[i:i + 2] for i in range(0, len(self.game.history), 2)]
        end = max(0, len(rows) - self.scroll)
        start = max(0, end - 3)
        if not rows:
            self.text("Awaiting first move. Cyan starts.", (728, 510), 16, MUTED)
        for idx in range(start, end):
            row = rows[idx]
            y = 495 + (idx - start) * 23
            self.text(f"{idx + 1:02}", (732, y), 14, MUTED)
            self.text(row[0], (793, y), 16, CYAN)
            if len(row) > 1:
                self.text(row[1], (958, y), 16, ORANGE)
        for rect, label, _ in self.buttons:
            enabled = label != "CLAIM DRAW" or (not self.game.finished and self.game.board.can_claim_draw())
            hover = rect.collidepoint(pygame.mouse.get_pos()) and enabled
            pygame.draw.rect(self.screen, (41, 66, 83) if hover else (25, 39, 53), rect, border_radius=4)
            pygame.draw.rect(self.screen, (94, 139, 157) if hover else (48, 70, 86), rect, 1, border_radius=4)
            self.text(label, rect.center, 16, TEXT if enabled else (90, 107, 125), True)
        self.text("U Undo   /   F Flip   /   N New   /   Esc Cancel", (728, 698), 14, MUTED)
        self.text("P Pawn   N Knight   B Bishop   R Rook   Q Queen   K King", (728, 770), 14, TEXT)
        if self.promotions or self.confirm_reset:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 190))
            self.screen.blit(shade, (0, 0))
            pygame.draw.rect(self.screen, PANEL, (316, 292, 548, 236), border_radius=16)
            if self.promotions:
                self.text("CHOOSE PROMOTION", (590, 330), 28, CYAN, True)
                for rect, kind in self.promotion_boxes():
                    pygame.draw.rect(self.screen, (43, 66, 86), rect, border_radius=8)
                    sprite = self.art.sprite(self.game.board.turn, kind, 70, 62)
                    self.screen.blit(sprite, sprite.get_rect(midbottom=(rect.centerx, rect.bottom - 22)))
                    self.text(NAMES[kind], (rect.centerx, rect.bottom - 12), 14, TEXT, True)
            else:
                self.text("START A NEW GAME?", (590, 335), 28, CYAN, True)
                self.text("The current game will be cleared.", (590, 380), 18, MUTED, True)
                for rect, label in [(pygame.Rect(392, 420, 180, 48), "START"), (pygame.Rect(608, 420, 180, 48), "CANCEL")]:
                    pygame.draw.rect(self.screen, (43, 66, 86), rect, border_radius=8)
                    self.text(label, rect.center, 18, TEXT, True)
        pygame.display.flip()

    def run(self):
        while self.running:
            for event in pygame.event.get():
                self.event(event)
            self.draw()
            self.clock.tick(60)
        pygame.quit()


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", type=Path, help="Render one frame, save PNG and exit")
    args = parser.parse_args()
    app = App()
    if args.screenshot:
        app.draw()
        args.screenshot.parent.mkdir(parents=True, exist_ok=True)
        pygame.image.save(app.screen, str(args.screenshot))
        pygame.quit()
    else:
        app.run()
