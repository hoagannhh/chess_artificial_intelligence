import importlib.util
from math import tanh
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import chess

HAS_TORCH = importlib.util.find_spec('torch') is not None
if HAS_TORCH:
    import torch
    from backend.ai.alphazero.encoding import action_index
    from backend.ai.alphazero.network import load_checkpoint
    from backend.ai.alphazero.teacher import sample_training_batch, teacher_game
    from backend.ai.alphazero.train import main
    from backend.ai.search import SearchResult, search


@unittest.skipUnless(HAS_TORCH, 'Install AlphaZero requirements')
class TeacherTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_labels_use_teacher_recommendation_and_side_to_move(self):
        position = chess.Board('4k3/8/8/3q4/4P3/8/8/4K3 w - - 0 1')
        for board in (position, position.mirror()):
            expected = search(board, 'alphabeta_q', 1, 1000)
            samples, game, skipped = teacher_game(1, 1000, 1, random.Random(3), board.fen(),
                                                   exploration=1, opening_plies=8)
            sample, = samples
            self.assertEqual(sample['indices'].tolist(), [action_index(chess.Move.from_uci(expected.move))])
            self.assertEqual(sample['teacher_move'], expected.move)
            sign = 1 if board.turn else -1
            self.assertAlmostEqual(sample['value'], tanh(sign * expected.score / 600))
            self.assertEqual(sample['source'], 'alphabeta_q')
            self.assertEqual(sample['value_source'], 'teacher_heuristic')
            self.assertEqual(skipped, 0)
            self.assertIn(next(iter(game.mainline_moves())), board.legal_moves)
            # The position is unfinished, but a completed teacher search supplies a heuristic target.
            self.assertEqual(game.headers['Result'], '*')
            self.assertTrue(sample['value_known'])

    def test_depth_zero_fallback_is_not_used_as_a_teacher_label(self):
        result = SearchResult('a2a3', 0, 0, 3, 1, 0, 50, True, 'alphabeta_q')
        with patch('backend.ai.alphazero.teacher.search', return_value=result):
            samples, _, skipped = teacher_game(3, 50, 1, random.Random(0))
        self.assertEqual(samples, [])
        self.assertEqual(skipped, 1)

    def test_teacher_and_selfplay_batch_ratio_and_short_buffers(self):
        selfplay = [('selfplay', index) for index in range(10)]
        teacher = [('teacher', index) for index in range(10)]
        rng = random.Random(0)
        batch = sample_training_batch(selfplay, teacher, 8, 0.25, rng)
        self.assertEqual(sum(item[0] == 'teacher' for item in batch), 2)
        self.assertEqual(len(set(batch)), 8)
        self.assertEqual(sample_training_batch([], teacher[:1], 8, 0.25, rng), teacher[:1])
        self.assertTrue(all(item[0] == 'selfplay'
                            for item in sample_training_batch(selfplay, teacher, 8, 0, rng)))

    def test_supervised_resume_then_selfplay_preserves_teacher_and_provenance(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'teacher-run'
            args = ['train', '--output', str(output), '--iterations', '1', '--games', '0',
                    '--teacher-games', '1', '--teacher-depth', '1', '--teacher-time-ms', '1000',
                    '--max-plies', '2', '--steps', '2', '--channels', '8', '--blocks', '1']
            with patch('sys.argv', args):
                main()
            _, first = load_checkpoint(output / 'latest.pt')
            self.assertEqual(first['training_method'], 'supervised_teacher')
            self.assertEqual(len(first['teacher_replay']), 2)
            self.assertEqual(first['replay'], [])
            with patch('sys.argv', ['train', '--output', str(output), '--resume', '--iterations', '1',
                                    '--games', '1', '--simulations', '1', '--max-plies', '2', '--steps', '1']):
                main()
            model, second = load_checkpoint(output / 'latest.pt')
            self.assertEqual(second['iteration'], 2)
            self.assertEqual(len(second['teacher_replay']), 2)
            self.assertEqual(len(second['replay']), 2)
            self.assertEqual(second['training_method'], 'teacher_assisted_self_play')
            self.assertEqual([stage['training_method'] for stage in second['lineage']],
                             ['supervised_teacher', 'teacher_assisted_self_play'])
            _, published = load_checkpoint(output / 'current.pt')
            self.assertEqual(published['training_method'], second['training_method'])
            self.assertTrue((output / 'teacher-0001.pgn').exists())


if __name__ == '__main__':
    unittest.main()
