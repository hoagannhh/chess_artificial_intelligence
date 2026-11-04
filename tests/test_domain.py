import unittest
import chess
from backend.domain.game import Game


class GameTests(unittest.TestCase):
    def test_illegal_move_does_not_mutate(self):
        game = Game()
        before = game.board.fen()
        self.assertFalse(game.play(chess.Move.from_uci("e2e5")))
        self.assertEqual(before, game.board.fen())
        self.assertEqual([], game.history)

    def test_mate_blocks_moves_and_undo_restores(self):
        game = Game()
        for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
            self.assertTrue(game.play(chess.Move.from_uci(uci)))
        self.assertTrue(game.finished)
        self.assertEqual(game.history[-1], "Qh4#")
        self.assertEqual(game.status()[0], "ORANGE WINS")
        game.undo()
        self.assertFalse(game.finished)
        self.assertEqual(len(game.history), 3)

    def test_special_moves_undo(self):
        positions = [
            ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1"),
            ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1", "e5d6"),
            ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a7a8n")]
        for fen, uci in positions:
            game = Game()
            game.board = chess.Board(fen)
            before = game.board.fen()
            self.assertTrue(game.play(chess.Move.from_uci(uci)))
            game.undo()
            self.assertEqual(before, game.board.fen())

    def test_claim_draw_and_undo(self):
        game = Game()
        for uci in ("g1f3", "g8f6", "f3g1", "f6g8") * 2:
            game.play(chess.Move.from_uci(uci))
        self.assertFalse(game.finished)
        self.assertTrue(game.claim_draw())
        self.assertTrue(game.finished)
        game.undo()
        self.assertFalse(game.finished)
        self.assertEqual(len(game.history), 8)


