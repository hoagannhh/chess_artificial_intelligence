import csv
import tempfile
import unittest
from pathlib import Path

from backend.application.session import Session


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'experiments'
        self.save = Path(tmp.name) / 'current.json'
        self.s = Session(self.save, self.root)
        self.players = ['minimax', 'alphabeta']

    def ai(self, players=None):
        pair = players or self.players
        return self.s.action(dict(action='ai_move', algorithm=pair[0 if self.s.game.board.turn else 1],
                                  ai_players=pair, depth=1, time_limit_ms=1000))

    def test_mate_restore_undo_replay_and_new_game(self):
        # Start the experiment at an interactive position with Black to mate.
        for uci in ('f2f3', 'e7e5', 'g2g4'):
            self.s.action(dict(action='move', move=uci))
        self.assertEqual(self.ai()['result'], '0-1')
        for _ in range(2):
            self.s = Session(self.save, self.root)
            self.s.snapshot()
            table = self.s.experiment_report()['sources'][1]
            self.assertEqual(table['games'], 1)
            self.assertEqual(table['pairs'][0]['a'], 'alphabeta')
            self.assertEqual(table['pairs'][0]['a_wins'], 1)
            game, = table['matches']
            self.assertEqual((game['white_algorithm'], game['black_algorithm'], game['result']),
                             ('minimax', 'alphabeta', '0-1'))
            self.assertEqual(game['game_id'], self.s.game.game_id)
        self.s.action(dict(action='undo'))
        self.assertEqual(self.s.experiment_report()['sources'][1]['games'], 0)
        self.ai()
        self.s.action(dict(action='reset'))
        with (self.root / 'interface-games.csv').open(encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]['result'], rows[0]['start_ply'], rows[0]['plies']), ('0-1', '3', '1'))
        self.assertEqual(rows[0]['termination'], 'Checkmate')

    def test_manual_modes_and_interrupted_game(self):
        for action in ('agree_draw', 'undo'):
            self.s.action(dict(action=action))
        self.s.action(dict(action='ai_move', algorithm='minimax', depth=1))
        self.s.action(dict(action='resign'))
        self.s.action(dict(action='reset'))
        self.ai()
        self.s.action(dict(action='reset'))
        self.ai()
        self.s.action(dict(action='move', move=self.s.snapshot()['legal'][0]))
        self.s.action(dict(action='resign', ai_players=self.players))
        self.assertEqual(self.s.experiment_report()['sources'][1]['games'], 0)

    def test_timeout_survives_reopen(self):
        from unittest.mock import patch
        with patch('backend.domain.clock.monotonic', return_value=0.0) as now:
            self.s.action(dict(action='reset', clock_minutes=5))
            self.ai()
            now.return_value = 301
            self.assertTrue(self.s.snapshot()['finished'])
            self.s = Session(self.save, self.root)
            self.assertEqual(self.s.experiment_report()['sources'][1]['pairs'][0]['b_wins'], 1)

    def test_combined_tournament_and_live_self_play(self):
        pair = ['pvs', 'pvs']
        self.ai(pair)
        self.s = Session(self.save, self.root)
        self.s.action(dict(action='agree_draw', ai_players=pair))
        folder = self.root / 'run-01'
        folder.mkdir()
        (folder / 'summary.json').write_text('{}', encoding='utf8')
        (folder / 'games.csv').write_text(
            'white_algorithm,black_algorithm,result\npvs,mcts,1-0\nmcts,pvs,*\n', encoding='utf8')
        report = self.s.experiment_report()
        combined, live, cli = report['sources']
        self.assertEqual((combined['games'], live['games'], cli['games']), (3, 1, 2))
        pvs = next(row for row in combined['standings'] if row['algorithm'] == 'pvs')
        self.assertEqual((pvs['wins'], pvs['games'], pvs['self_play'], pvs['unfinished']), (1, 3, 1, 1))
        self.assertEqual(live['pairs'][0]['draws'], 1)
        self.assertEqual([(g['white_algorithm'], g['black_algorithm'], g['result'])
                          for g in cli['matches']], [('pvs', 'mcts', '1-0'), ('mcts', 'pvs', '*')])
        self.assertEqual(live['matches'][0]['result'], '1/2-1/2')

    def test_switch_algorithms_starts_from_actual_position(self):
        self.ai()
        fen = self.s.game.board.fen()
        pair = ['mcts', 'pvs']
        self.ai(pair)
        self.s.action(dict(action='resign', ai_players=pair))
        record, = self.s.results.live_rows().values()
        self.assertEqual((record['white_algorithm'], record['black_algorithm']), tuple(pair))
        self.assertEqual((record['initial_fen'], record['start_ply']), (fen, '1'))
