import unittest
import random
from backend.ai.mcts import Node, choose_child, search_mcts
import chess
from backend.ai.pawn_routes import promotion_route
from backend.ai.search import search
from backend.application.session import Session


class SearchTests(unittest.TestCase):
    def test_same_score_and_move_at_completed_depth(self):
        for fen in [chess.STARTING_FEN, '4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1']:
            board = chess.Board(fen)
            a = search(board, 'minimax', 2, 2000)
            b = search(board, 'alphabeta', 2, 2000)
            self.assertEqual((a.depth, b.depth), (2, 2))
            self.assertEqual((a.score, a.move), (b.score, b.move))
            self.assertLessEqual(b.nodes, a.nodes)
            self.assertEqual(board.fen(), fen)

    def test_mate_and_terminal(self):
        board = chess.Board()
        for uci in ['f2f3', 'e7e5', 'g2g4']:
            board.push_uci(uci)
        before = board.fen()
        stack = list(board.move_stack)
        for algorithm in ['minimax', 'alphabeta', 'pvs', 'expectimax', 'astar_ab', 'alphabeta_q']:
            result = search(board, algorithm, 2, 2000)
            self.assertEqual(result.move, 'd8h4')
            self.assertLess(result.score, -90000)
        self.assertEqual(board.fen(), before)
        self.assertEqual(board.move_stack, stack)
        board.push_uci('d8h4')
        self.assertIsNone(search(board).move)

    def test_timeout_preserves_board_and_returns_legal_move(self):
        board = chess.Board()
        result = search(board, 'minimax', 5, 50)
        self.assertTrue(result.timed_out)
        self.assertIn(chess.Move.from_uci(result.move), board.legal_moves)
        self.assertEqual(board.fen(), chess.STARTING_FEN)
        self.assertLess(result.elapsed_ms, 1000)

    def test_selfplay_and_undo(self):
        session = Session()
        for index in range(8):
            state = session.action({'action': 'ai_move', 'algorithm': ['minimax', 'alphabeta', 'pvs', 'mcts'][index % 4], 'depth': 1, 'time_limit_ms': 50})
            self.assertEqual(len(state['history']), index + 1)
            self.assertEqual(state['ai_stats']['side'], 'white' if index % 2 == 0 else 'black')
        session.action({'action': 'undo'})
        self.assertEqual(len(session.game.history), 7)
        self.assertIsNone(session.snapshot()['ai_stats'])

    def test_bad_options_do_not_change_game(self):
        session = Session()
        before = session.snapshot()
        for options in [{'algorithm': 'unknown'}, {'depth': True}, {'depth': 8}, {'time_limit_ms': 0}]:
            with self.assertRaises(ValueError):
                session.action({'action': 'ai_move', **options})
            self.assertEqual(before, session.snapshot())

    def test_pvs_matches_reference_on_both_turns(self):
        board = chess.Board()
        rng = random.Random(42)
        for _ in range(8):
            board.push(rng.choice(list(board.legal_moves)))
            before = board.fen(), list(board.move_stack)
            reference = search(board, 'minimax', 2, 2000)
            result = search(board, 'pvs', 2, 2000)
            self.assertEqual((reference.depth, result.depth), (2, 2))
            self.assertEqual((result.score, result.move), (reference.score, reference.move))
            self.assertEqual((board.fen(), board.move_stack), before)

    def test_uct_models_adversary(self):
        positive = Node(visits=10, total=8)
        negative = Node(visits=10, total=-8)
        parent = Node(visits=20, children=[positive, negative])
        self.assertIs(choose_child(parent, chess.WHITE), positive)
        self.assertIs(choose_child(parent, chess.BLACK), negative)

    def test_mcts_repeatable_fixed_simulations_and_no_mutation(self):
        board = chess.Board()
        board.push_uci('e2e4')
        before = board.fen(), list(board.move_stack)
        a = search_mcts(board, 1, 2000, max_iterations=24, seed=7)
        b = search_mcts(board, 1, 2000, max_iterations=24, seed=7)
        self.assertEqual(a.iterations, 24)
        self.assertEqual((a.move, a.mean_reward, a.nodes), (b.move, b.mean_reward, b.nodes))
        self.assertIn(chess.Move.from_uci(a.move), board.legal_moves)
        self.assertTrue(-1 <= a.mean_reward <= 1)
        self.assertIsNone(a.score)
        self.assertEqual((board.fen(), board.move_stack), before)

    def test_mcts_mate_for_either_color_and_draw(self):
        board = chess.Board()
        for move in ['f2f3', 'e7e5', 'g2g4']:
            board.push_uci(move)
        for position in [board, board.mirror()]:
            result = search(position, 'mcts', 1, 500)
            after = position.copy()
            after.push_uci(result.move)
            self.assertTrue(after.is_checkmate())
            self.assertEqual(result.mean_reward, 1 if position.turn else -1)
        draw = chess.Board('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1')
        result = search(draw, 'mcts', 1, 50)
        self.assertIsNone(result.move)
        self.assertEqual(result.mean_reward, 0)

    def test_new_algorithms_respect_deadline(self):
        for algorithm in ['pvs', 'mcts', 'expectimax', 'astar_ab', 'alphabeta_q']:
            board = chess.Board()
            result = search(board, algorithm, 5, 50)
            self.assertIn(chess.Move.from_uci(result.move), board.legal_moves)
            self.assertLess(result.elapsed_ms, 1000)
            self.assertEqual(board.fen(), chess.STARTING_FEN)

    def test_expectimax_averages_replies_for_either_side(self):
        position = chess.Board('7k/8/2p5/8/3P4/8/8/K7 w - - 0 1')
        for board in (position, position.mirror()):
            result = search(board, 'expectimax', 2, 1000)
            self.assertEqual(result.depth, 2)
            # Three king moves leave a White advantage of 8, one pawn move makes it 0.
            self.assertEqual(result.score, 6 if board.turn else -6)
            self.assertEqual(search(board, 'minimax', 2, 1000).score, 0)

    def test_astar_handles_blocked_attacked_and_capture_routes(self):
        for fen, expected in [
            ('7k/8/8/8/8/8/P7/7K w - - 0 1', 5),
            ('7k/8/8/8/8/R7/P7/7K w - - 0 1', None),
            ('7r/P7/7k/8/8/8/8/7K w - - 0 1', 2),
            ('Rn5k/P7/8/8/8/8/8/7K w - - 0 1', 1),
        ]:
            position = chess.Board(fen)
            for board in (position, position.mirror()):
                with self.subTest(fen=board.fen()):
                    cost, examined = promotion_route(board, board.turn)
                    self.assertEqual(cost, expected)
                    self.assertGreater(examined, 0)
                    self.assertEqual(promotion_route(board, not board.turn), (None, 0))

    def test_astar_promotion_bonus_changes_leaf_score(self):
        position = chess.Board('7k/8/8/P7/8/8/8/7K w - - 0 1')
        for board in (position, position.mirror()):
            base = search(board, 'alphabeta', 1, 1000)
            hybrid = search(board, 'astar_ab', 1, 1000)
            self.assertEqual(hybrid.move, base.move)
            self.assertEqual(hybrid.score - base.score, 60 if board.turn else -60)
            self.assertGreater(hybrid.route_nodes, 0)

    def test_quiescence_sees_recapture_beyond_depth_one(self):
        position = chess.Board('3r3k/3p4/8/8/8/8/8/3Q3K w - - 0 1')
        for board in (position, position.mirror()):
            poisoned_capture = 'd1d7' if board.turn else 'd8d2'
            self.assertEqual(search(board, 'alphabeta', 1, 1000).move, poisoned_capture)
            result = search(board, 'alphabeta_q', 1, 1000)
            self.assertEqual(result.depth, 1)
            self.assertNotEqual(result.move, poisoned_capture)
            self.assertIn(chess.Move.from_uci(result.move), board.legal_moves)
            self.assertGreater(result.qnodes, 0)
            self.assertLessEqual(result.qnodes, result.nodes)

    def test_mcts_claimed_draw_reward(self):
        session = Session()
        for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 2:
            session.action({'action': 'move', 'move': move})
        state = session.action({'action': 'ai_move', 'algorithm': 'mcts', 'time_limit_ms': 50})
        self.assertTrue(state['finished'])
        self.assertIsNone(state['ai_stats']['score'])
        self.assertEqual(state['ai_stats']['mean_reward'], 0)

    def test_undo_pair_and_manual_result(self):
        session = Session()
        session.action({'action': 'move', 'move': 'e2e4'})
        session.action({'action': 'move', 'move': 'e7e5'})
        before = session.snapshot()
        with self.assertRaises(ValueError):
            session.action({'action': 'undo', 'count': 3})
        self.assertEqual(before, session.snapshot())
        session.action({'action': 'resign'})
        session.action({'action': 'undo', 'count': 2})
        self.assertEqual(len(session.game.history), 2)
        self.assertFalse(session.game.finished)
        state = session.action({'action': 'undo', 'count': 2})
        self.assertEqual(state['history'], [])
        self.assertEqual(state['turn'], 'white')


if __name__ == '__main__':
    unittest.main()
