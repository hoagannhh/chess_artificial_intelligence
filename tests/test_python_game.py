import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import unittest
import chess
import pygame
from archive.pygame.robot_chess.app import App
from archive.pygame.robot_chess.projection import project


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.app = App()

    def tearDown(self):
        pygame.quit()

    def test_clicks_and_flipped_coordinates(self):
        for flipped in (False, True):
            self.app.flipped = flipped
            for square in chess.SQUARES:
                self.assertEqual(square, self.app.square_at(self.app.square_rect(square).center))
        self.app.click_square(chess.E2)
        self.app.click_square(chess.E4)
        self.assertEqual(self.app.game.history, ["e4"])
        self.assertIsNone(self.app.selected)
        self.app.draw()

    def test_promotion_modal_and_reset_confirmation(self):
        self.app.game.board = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
        self.app.click_square(chess.A7)
        self.app.click_square(chess.A8)
        self.assertEqual(len(self.app.promotions), 4)
        self.app.draw()
        box, _ = self.app.promotion_boxes()[-1]
        self.app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=box.center))
        self.assertEqual(self.app.game.board.piece_at(chess.A8).piece_type, chess.KNIGHT)
        self.app.ask_reset()
        self.app.draw()
        self.app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(450, 440)))
        self.assertEqual(self.app.game.board.fen(), chess.Board().fen())
        self.assertFalse(self.app.confirm_reset)

    def test_projected_tile_interiors_and_outside(self):
        for flipped in (False, True):
            self.app.flipped = flipped
            for square in chess.SQUARES:
                col, row = self.app.board_coords(square)
                for dx, dy in ((0.05, 0.05), (0.95, 0.05), (0.05, 0.95), (0.95, 0.95)):
                    self.assertEqual(square, self.app.square_at(project(col + dx, row + dy)))
            for point in ((0, 0), (30, 190), (690, 500), (360, 710)):
                self.assertIsNone(self.app.square_at(point))

    def test_projected_mouse_move_in_both_orientations(self):
        for flipped in (False, True):
            self.app.game.reset()
            self.app.clear_selection()
            self.app.flipped = flipped
            for square in (chess.E2, chess.E4):
                self.app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                    button=1, pos=self.app.square_rect(square).center))
            self.assertEqual(self.app.game.history, ["e4"])
            self.app.draw()

    def test_every_friendly_base_can_be_selected(self):
        for flipped in (False, True):
            self.app.flipped = flipped
            for square, piece in self.app.game.board.piece_map().items():
                if piece.color == chess.WHITE:
                    self.app.clear_selection()
                    self.app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN,
                        button=1, pos=self.app.square_rect(square).center))
                    self.assertEqual(self.app.selected, square)

    def test_click_visible_sprite_above_its_tile(self):
        self.app.game.board = chess.Board("4k3/p7/8/8/8/8/8/4K3 w - - 0 1")
        square = chess.E1
        piece = self.app.game.board.piece_at(square)
        sprite, rect = self.app.art.placement(square, piece, self.app.board_coords)
        point = None
        for y in range(sprite.get_height() // 2):
            for x in range(sprite.get_width()):
                candidate = (rect.x + x, rect.y + y)
                if sprite.get_at((x, y)).a > 128 and self.app.square_at(candidate) != square:
                    point = candidate
                    break
            if point:
                break
        self.assertIsNotNone(point)
        self.app.event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=point))
        self.assertEqual(self.app.selected, square)

    def test_atlas_has_twelve_transparent_sprites(self):
        self.assertEqual(len(self.app.art.originals), 12)
        for sprite in self.app.art.originals.values():
            self.assertTrue(sprite.get_flags() & pygame.SRCALPHA)
            self.assertGreater(sprite.get_height(), 30)
            self.assertGreater(sprite.get_width(), 20)


if __name__ == "__main__":
    unittest.main()
