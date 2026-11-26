import importlib.util
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import chess

HAS_TORCH = importlib.util.find_spec('torch') is not None
if HAS_TORCH:
    import torch
    from backend.ai.alphazero.encoding import ACTIONS, action_index, encode
    from backend.ai.alphazero.mcts import Node, TreeResult, run_search, select_child
    from backend.ai.alphazero.network import Evaluator, PolicyValueNet, load_checkpoint, save_checkpoint
    from backend.ai.alphazero.train import self_play, train_batch, main
    from backend.ai.alphazero.replay import ReplayBuffer
    from backend.ai.search import search
    from backend.application.session import Session


@unittest.skipUnless(HAS_TORCH, 'Install AlphaZero optional requirements to run neural tests')
class AlphaZeroTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        torch.manual_seed(7)

    def test_encoding_history_and_rule_state(self):
        board = chess.Board()
        for move in ('g1f3', 'g8f6', 'f3g1', 'f6g8'):
            board.push_uci(move)
        before = board.fen(), list(board.move_stack)
        encoded = encode(board)
        without_history = encode(chess.Board(board.fen()))
        self.assertFalse(torch.equal(encoded, without_history))
        self.assertEqual(encoded[12, 0, 0], 1)
        self.assertEqual((board.fen(), board.move_stack), before)

    def test_actions_are_unique_for_special_moves_and_random_positions(self):
        boards = [chess.Board('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1'),
                  chess.Board('1r2k3/P7/8/8/8/8/7p/4K1R1 w - - 0 1'),
                  chess.Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')]
        boards += [board.mirror() for board in boards]
        board = chess.Board()
        rng = random.Random(4)
        for _ in range(100):
            if board.is_game_over():
                break
            boards.append(board.copy())
            board.push(rng.choice(list(board.legal_moves)))
        for board in boards:
            actions = [action_index(move) for move in board.legal_moves]
            self.assertEqual(len(actions), len(set(actions)))
            self.assertTrue(all(0 <= index < ACTIONS for index in actions))

    def test_policy_masks_illegal_moves(self):
        board = chess.Board()
        priors, value = Evaluator(PolicyValueNet(8, 1))(board)
        self.assertEqual(set(priors), set(board.legal_moves))
        self.assertAlmostEqual(sum(priors.values()), 1, places=5)
        self.assertTrue(-1 <= value <= 1)

    def test_puct_reverses_child_value_and_finds_mate_for_both_colours(self):
        losing_child = Node(visits=10, total=9)
        winning_child = Node(visits=10, total=-9)
        root = Node(visits=20, children={'bad': losing_child, 'good': winning_child})
        self.assertEqual(select_child(root)[0], 'good')
        position = chess.Board()
        for move in ('f2f3', 'e7e5', 'g2g4'):
            position.push_uci(move)
        def uniform(board):
            moves = list(board.legal_moves)
            return {move: 1 / len(moves) for move in moves}, 0.0
        for board in (position, position.mirror()):
            before = board.fen(), list(board.move_stack)
            result = run_search(board, uniform, 160)
            after = board.copy()
            after.push(max(result.policy, key=result.policy.get))
            self.assertTrue(after.is_checkmate())
            self.assertGreater(result.value, 0)
            self.assertEqual(result.simulations, 0)
            self.assertEqual((board.fen(), board.move_stack), before)

    def test_mate_is_found_even_with_zero_network_prior(self):
        board = chess.Board()
        for move in ('f2f3', 'e7e5', 'g2g4'):
            board.push_uci(move)
        def wrong_prior(position):
            moves = list(position.legal_moves)
            return {move: 0.0 if move.uci() == 'd8h4' else 1 / (len(moves) - 1)
                    for move in moves}, 0.0
        result = run_search(board, wrong_prior, 1)
        self.assertEqual(result.policy, {chess.Move.from_uci('d8h4'): 1.0})

    def test_neural_leaf_value_is_negated_for_parent(self):
        def evaluator(board):
            moves = list(board.legal_moves)
            return {move: 1 / len(moves) for move in moves}, -0.75
        position = chess.Board()
        for board in (position, position.mirror()):
            result = run_search(board, evaluator, 1)
            self.assertEqual(result.simulations, 1)
            self.assertEqual(result.value, 0.75)

    def test_draw_flood_preserves_decisive_replay(self):
        decisive = [dict(value_known=True, value=value) for value in (1.0, -1.0)]
        replay = ReplayBuffer(8, decisive)
        replay.extend([dict(value_known=True, value=0.0) for _ in range(100)])
        self.assertEqual(len(replay.decisive), 2)
        self.assertEqual(len(replay.other), 4)
        replay.extend(decisive * 5)
        self.assertEqual(len(replay), 8)

    def test_value_head_can_learn_when_convolution_outputs_are_negative(self):
        model = PolicyValueNet(8, 1, value_activation='leaky_relu')
        with torch.no_grad():
            model.value[0].weight.zero_()
            model.value[0].bias.fill_(-1)
        _, values = model(encode(chess.Board()).unsqueeze(0))
        (values - 1).square().mean().backward()
        self.assertGreater(model.value[0].bias.grad.abs().sum().item(), 0)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'leaky.pt'
            save_checkpoint(path, model)
            restored, _ = load_checkpoint(path)
            self.assertEqual(restored.config['value_activation'], 'leaky_relu')
            self.assertIsInstance(restored.value[1], torch.nn.LeakyReLU)

    def test_truncation_has_no_value_target_and_training_changes_weights(self):
        model = PolicyValueNet(8, 1)
        samples, game = self_play(model, 2, 2, random.Random(0))
        self.assertEqual(game.headers['Result'], '*')
        self.assertTrue(all(not sample['value_known'] for sample in samples))
        before = model.policy[-1].weight.detach().clone()
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
        policy_loss, value_loss = train_batch(model, optimizer, samples)
        self.assertGreater(policy_loss, 0)
        self.assertEqual(value_loss, 0)
        self.assertFalse(torch.equal(before, model.policy[-1].weight))

    def test_completed_selfplay_uses_winner_perspective(self):
        position = chess.Board()
        for move in ('f2f3', 'e7e5', 'g2g4'):
            position.push_uci(move)
        result = TreeResult({chess.Move.from_uci('d8h4'): 1.0}, 1.0, 1, 2, 1, False)
        with patch('backend.ai.alphazero.train.run_search', return_value=result):
            samples, game = self_play(PolicyValueNet(8, 1), 1, 1, random.Random(), position.fen())
        self.assertEqual(game.headers['Result'], '0-1')
        self.assertEqual(samples[0]['value'], 1)
        self.assertTrue(samples[0]['value_known'])

    def test_checkpoint_app_results_and_missing_model(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'model.pt'
            model = PolicyValueNet(8, 1)
            save_checkpoint(path, model, iteration=0, trained=False)
            restored, metadata = load_checkpoint(path)
            self.assertTrue(torch.equal(next(model.parameters()), next(restored.parameters())))
            with patch.dict(os.environ, CHESS_AZ_MODEL=str(path)):
                session = Session(experiments_root=Path(temporary) / 'results')
                pair = ['alphazero', 'minimax']
                state = session.action(dict(action='ai_move', algorithm='alphazero',
                                            ai_players=pair, depth=1, time_limit_ms=50))
                self.assertEqual(state['ai_stats']['model_id'], metadata['model_id'])
                self.assertEqual(len(state['history']), 1)
                self.assertIsNone(state['ai_stats']['score'])
                session.action(dict(action='resign', ai_players=pair))
                game, = session.experiment_report()['sources'][1]['matches']
                self.assertIn(metadata['model_id'], game['white_algorithm'])
            with patch.dict(os.environ, CHESS_AZ_MODEL=str(Path(temporary) / 'missing.pt')):
                with self.assertRaisesRegex(ValueError, 'model missing'):
                    search(chess.Board(), 'alphazero', 1, 50)

    def test_training_resumes_optimizer_replay_and_iteration(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            arguments = ['train', '--output', str(output), '--iterations', '1', '--games', '1',
                         '--simulations', '1', '--max-plies', '2', '--steps', '1',
                         '--channels', '8', '--blocks', '1']
            with patch('sys.argv', arguments):
                main()
            with patch('sys.argv', arguments + ['--resume']):
                main()
            _, data = load_checkpoint(output / 'latest.pt')
            self.assertEqual(data['iteration'], 2)
            self.assertEqual(len(data['replay']), 4)
            self.assertEqual(len(data['metrics']), 2)
            self.assertTrue((output / 'checkpoint-0002.pt').is_file())
            self.assertFalse((output / 'training.lock').exists())


if __name__ == '__main__':
    unittest.main()
