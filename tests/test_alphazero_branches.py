import csv
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import chess

HAS_TORCH = importlib.util.find_spec('torch') is not None
if HAS_TORCH:
    import torch
    from backend.ai.alphazero import engine
    from backend.ai.alphazero.network import PolicyValueNet, load_checkpoint, model_path, save_checkpoint
    from backend.ai.search import search
    from backend.ai.tournament import TournamentConfig, run_tournament
    from backend.application.experiments import ExperimentResults, LIVE_FIELDS
    from backend.application.session import Session


@unittest.skipUnless(HAS_TORCH, 'Install AlphaZero requirements')
class AlphaZeroBranchTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.plain = self.root / 'plain.pt'
        self.teacher = self.root / 'teacher.pt'
        model = PolicyValueNet(8, 1)
        save_checkpoint(self.plain, model, training_method='self_play')
        save_checkpoint(self.teacher, model, training_method='supervised_teacher')
        self.plain_id = load_checkpoint(self.plain)[1]['model_id']
        self.teacher_id = load_checkpoint(self.teacher)[1]['model_id']
        environment = patch.dict(os.environ, CHESS_AZ_PLAIN_MODEL=str(self.plain),
                                 CHESS_AZ_TEACHER_MODEL=str(self.teacher),
                                 CHESS_AZ_MODEL=str(self.teacher))
        environment.start()
        self.addCleanup(environment.stop)
        self.players = ['alphazero', 'alphazero_teacher']

    def test_independent_paths_caches_and_missing_teacher(self):
        self.assertEqual(model_path('alphazero'), self.plain)
        self.assertEqual(model_path('alphazero_teacher'), self.teacher)
        with patch.dict(engine._cache, {}, clear=True), patch.object(
                engine, 'load_checkpoint', wraps=load_checkpoint) as loader:
            for algorithm, expected in [('alphazero', self.plain_id),
                                        ('alphazero_teacher', self.teacher_id),
                                        ('alphazero', self.plain_id)]:
                result = search(chess.Board(), algorithm, 1, 50)
                self.assertEqual(result.algorithm, algorithm)
                self.assertEqual(result.model_id, expected)
                self.assertIn(chess.Move.from_uci(result.move), chess.Board().legal_moves)
            self.assertEqual(loader.call_count, 2)
        with patch.dict(os.environ, CHESS_AZ_TEACHER_MODEL=str(self.root / 'missing.pt')):
            with self.assertRaisesRegex(ValueError, 'missing for alphazero_teacher'):
                search(chess.Board(), 'alphazero_teacher', 1, 50)
            self.assertEqual(search(chess.Board(), 'alphazero', 1, 50).model_id, self.plain_id)

    def test_live_match_keeps_both_ids_across_turns_restore_and_model_change(self):
        save = self.root / 'save.json'
        results = self.root / 'results'
        session = Session(save, results)
        for ply in range(4):
            state = session.action(dict(action='ai_move', algorithm=self.players[ply % 2],
                                        ai_players=self.players, depth=1, time_limit_ms=50))
            self.assertEqual(session.game.experiment['start_ply'], 0)
            session = Session(save, results)
        session.action(dict(action='agree_draw', ai_players=self.players))
        row, = session.results.live_rows().values()
        self.assertEqual((row['plies'], row['white_model_id'], row['black_model_id']),
                         ('4', self.plain_id, self.teacher_id))
        match, = session.experiment_report()['sources'][1]['matches']
        self.assertEqual(match['white_algorithm'], f'AlphaZero [{self.plain_id}]')
        self.assertEqual(match['black_algorithm'], f'AlphaZero có thầy [{self.teacher_id}]')
        session.action(dict(action='undo'))
        self.assertEqual(session.experiment_report()['sources'][1]['games'], 0)
        save_checkpoint(self.plain, PolicyValueNet(8, 1), training_method='self_play', iteration=99)
        session.action(dict(action='ai_move', algorithm='alphazero', ai_players=self.players,
                            depth=1, time_limit_ms=50))
        self.assertEqual(session.game.experiment['start_ply'], 4)
        self.assertEqual(session.game.experiment['black_model_id'], self.teacher_id)

    def test_tournament_swap_colours_keeps_the_correct_checkpoints(self):
        config = TournamentConfig(tuple(self.players), games_per_pair=2, depth=1,
                                  time_limit_ms=50, max_plies=4)
        output = self.root / 'tournament'
        run_tournament(config, output)
        with (output / 'games.csv').open(encoding='utf-8', newline='') as handle:
            games = list(csv.DictReader(handle))
        self.assertEqual((games[0]['white_model_id'], games[0]['black_model_id']),
                         (self.plain_id, self.teacher_id))
        self.assertEqual((games[1]['white_model_id'], games[1]['black_model_id']),
                         (self.teacher_id, self.plain_id))
        source = next(row for row in ExperimentResults(self.root).report()['sources']
                      if row['name'] == 'tournament')
        self.assertEqual(len(source['standings']), 2)

    def test_legacy_csv_model_id_survives_new_schema_write(self):
        results = self.root / 'results'
        results.mkdir()
        row = dict(game_id='legacy', white_algorithm='alphazero', black_algorithm='minimax',
                   result='1-0', model_id='old-checkpoint')
        with (results / 'interface-games.csv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=LIVE_FIELDS[:-2])
            writer.writeheader()
            writer.writerow(row)
        session = Session(experiments_root=results)
        session.action(dict(action='ai_move', algorithm='alphazero', ai_players=self.players,
                            depth=1, time_limit_ms=50))
        session.action(dict(action='agree_draw', ai_players=self.players))
        restored = ExperimentResults(results)
        self.assertEqual(restored.live_rows()['legacy']['white_model_id'], 'old-checkpoint')
        match = next(game for game in restored.report()['sources'][1]['matches']
                     if game['game_id'] == 'legacy')
        self.assertEqual(match['white_algorithm'], 'AlphaZero [old-checkpoint]')


if __name__ == '__main__':
    unittest.main()
