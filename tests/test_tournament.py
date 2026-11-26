import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from backend.ai.tournament import (
    GameRecord,
    TournamentConfig,
    build_schedule,
    load_progress,
    main,
    play_game,
    run_tournament,
    summarize,
    validate_config,
)


MATE_IN_ONE_FOR_BLACK = 'rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2'


class TournamentTests(unittest.TestCase):
    def test_resume_after_interrupt_preserves_prefix_and_skips_recorded_limits(self):
        config = TournamentConfig(('minimax', 'alphabeta'), depth=1,
                                  time_limit_ms=50, max_plies=1)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            def interrupt(plan, settings):
                if plan.game_id == 2:
                    raise KeyboardInterrupt
                return play_game(plan, settings)
            with self.assertRaises(KeyboardInterrupt):
                run_tournament(config, output, game_runner=interrupt)
            self.assertFalse((output / 'tournament.lock').exists())
            prefix = {name: (output / name).read_bytes()
                      for name in ('games.csv', 'moves.csv', 'game-001.pgn')}
            records, _ = load_progress(output, config)
            self.assertEqual(len(records), 1)
            self.assertTrue(records[0].limit_reached)
            seen = []
            def resume_runner(plan, settings):
                seen.append(plan.game_id)
                return play_game(plan, settings)
            result = run_tournament(config, output, resume=True, game_runner=resume_runner)
            self.assertEqual(seen, [2])
            self.assertEqual(len(result.records), 2)
            for name, content in prefix.items():
                self.assertTrue((output / name).read_bytes().startswith(content))
            # A completed run can regenerate derived summaries without replaying.
            again = run_tournament(config, output, resume=True,
                                   game_runner=lambda *args: self.fail('Replayed a saved game'))
            self.assertEqual(again.summary, result.summary)

    def test_resume_rejects_changed_config_and_incomplete_csv_without_writes(self):
        config = TournamentConfig(('minimax', 'alphabeta'), max_plies=1)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            run_tournament(config, output)
            changed = TournamentConfig(config.algorithms, max_plies=2)
            with self.assertRaisesRegex(ValueError, 'configuration differs'):
                run_tournament(changed, output, resume=True)
            with (output / 'moves.csv').open('a') as stream:
                stream.write('3,1')
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaisesRegex(ValueError, 'Incomplete CSV'):
                run_tournament(config, output, resume=True)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_cli_resume_loads_saved_config_and_dry_run_is_read_only(self):
        config = TournamentConfig(('minimax', 'alphabeta'), depth=2, max_plies=1)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            run_tournament(config, output)
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with patch('sys.argv', ['tournament', '--resume', '--dry-run', '--output', str(output)]):
                main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_legacy_progress_and_claim_draw_stats_are_resumable(self):
        # 100 halfmoves permits a draw claim before an actual move is played.
        config = TournamentConfig(('minimax', 'alphabeta'), max_plies=2,
                                  initial_fen='4k3/8/8/8/8/8/8/R3K3 w - - 100 51')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'run'
            run_tournament(config, output)
            (output / 'run_config.json').unlink()
            (output / 'metadata.json').unlink()
            records, moves = load_progress(output, config)
            self.assertEqual([r.plies for r in records], [0, 0])
            self.assertEqual([r.result for r in records], ['1/2-1/2'] * 2)
            self.assertEqual(len(moves), 2)
            with patch('sys.argv', ['tournament', '--resume', '--dry-run', '--output', str(output)]):
                with self.assertRaises(SystemExit) as raised:
                    main()
            self.assertEqual(raised.exception.code, 2)

    def test_schedule_covers_each_pair_and_balances_colours(self):
        config = TournamentConfig(('minimax', 'alphabeta', 'pvs'), games_per_pair=2)
        plans = build_schedule(config)
        self.assertEqual(len(plans), 6)  # 3 unordered pairs × 2 games.
        by_pair = {}
        for plan in plans:
            by_pair.setdefault((plan.algorithm_a, plan.algorithm_b), []).append(plan)
        self.assertEqual(set(by_pair), {
            ('minimax', 'alphabeta'), ('minimax', 'pvs'), ('alphabeta', 'pvs'),
        })
        for pair, games in by_pair.items():
            self.assertEqual(len(games), 2)
            self.assertEqual(sum(game.white_algorithm == pair[0] for game in games), 1)
            self.assertEqual(sum(game.black_algorithm == pair[0] for game in games), 1)

    def test_odd_games_per_pair_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'even'):
            validate_config(TournamentConfig(('minimax', 'alphabeta'), games_per_pair=3))

    def test_summary_counts_wins_draws_losses_and_unfinished_separately(self):
        records = [
            GameRecord(1, 1, 1, 'minimax', 'alphabeta', 'minimax', 'alphabeta',
                       '1-0', 'minimax', True, False, 12, 'Checkmate', 'fen', 'game-001.pgn'),
            GameRecord(2, 1, 2, 'minimax', 'alphabeta', 'alphabeta', 'minimax',
                       '1/2-1/2', '', True, False, 42, 'Stalemate', 'fen', 'game-002.pgn'),
            GameRecord(3, 1, 3, 'minimax', 'alphabeta', 'minimax', 'alphabeta',
                       '*', '', False, True, 80, 'Stopped at max_plies', 'fen', 'game-003.pgn'),
        ]
        moves = [
            {'algorithm': 'minimax', 'elapsed_ms': 10.0, 'nodes': 20, 'cutoffs': 3},
            {'algorithm': 'minimax', 'elapsed_ms': 20.0, 'nodes': 40, 'cutoffs': 5},
            {'algorithm': 'alphabeta', 'elapsed_ms': 5.0, 'nodes': 10, 'cutoffs': 4},
        ]
        summary, head_to_head = summarize(('minimax', 'alphabeta'), records, moves)
        standings = {row['algorithm']: row for row in summary}

        self.assertEqual(standings['minimax']['games'], 3)
        self.assertEqual(standings['minimax']['wins'], 1)
        self.assertEqual(standings['minimax']['draws'], 1)
        self.assertEqual(standings['minimax']['losses'], 0)
        self.assertEqual(standings['minimax']['unfinished'], 1)
        self.assertEqual(standings['minimax']['points'], 1.5)
        self.assertEqual(standings['minimax']['score_percent'], 75.0)
        self.assertEqual(standings['minimax']['avg_elapsed_ms'], 15.0)

        self.assertEqual(standings['alphabeta']['wins'], 0)
        self.assertEqual(standings['alphabeta']['draws'], 1)
        self.assertEqual(standings['alphabeta']['losses'], 1)
        self.assertEqual(standings['alphabeta']['unfinished'], 1)
        self.assertEqual(standings['alphabeta']['points'], 0.5)
        self.assertEqual(standings['alphabeta']['score_percent'], 25.0)

        self.assertEqual(head_to_head[0]['algorithm_a_wins'], 1)
        self.assertEqual(head_to_head[0]['algorithm_b_wins'], 0)
        self.assertEqual(head_to_head[0]['draws'], 1)
        self.assertEqual(head_to_head[0]['unfinished'], 1)

    def test_real_tournament_writes_report_ready_artifacts(self):
        config = TournamentConfig(
            ('minimax', 'alphabeta'),
            games_per_pair=2,
            depth=1,
            time_limit_ms=50,
            max_plies=1,
            initial_fen=MATE_IN_ONE_FOR_BLACK,
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'tournament'
            result = run_tournament(config, output)

            self.assertEqual(len(result.records), 2)
            self.assertTrue(all(record.finished for record in result.records))
            self.assertTrue(all(record.result == '0-1' for record in result.records))
            for filename in ('games.csv', 'moves.csv', 'summary.csv', 'head_to_head.csv',
                             'metadata.json', 'summary.json', 'report_summary.md',
                             'game-001.pgn', 'game-002.pgn'):
                self.assertTrue((output / filename).is_file(), filename)

            with (output / 'games.csv').open(encoding='utf-8', newline='') as handle:
                games = list(csv.DictReader(handle))
            self.assertEqual([game['result'] for game in games], ['0-1', '0-1'])
            self.assertEqual(games[0]['white_algorithm'], 'minimax')
            self.assertEqual(games[1]['white_algorithm'], 'alphabeta')

            summary = json.loads((output / 'summary.json').read_text(encoding='utf-8'))
            self.assertEqual(summary['metadata']['counts']['finished_games'], 2)
            self.assertEqual(summary['metadata']['counts']['unfinished_games'], 0)
            standings = {row['algorithm']: row for row in summary['standings']}
            self.assertEqual(standings['minimax']['wins'], 1)
            self.assertEqual(standings['alphabeta']['wins'], 1)

            with self.assertRaises(FileExistsError):
                run_tournament(config, output)

    def test_new_engines_complete_colour_reversed_matches(self):
        algorithms = ('astar_ab', 'expectimax', 'alphabeta_q')
        config = TournamentConfig(algorithms, games_per_pair=2, depth=1, time_limit_ms=1000,
                                  max_plies=1, initial_fen=MATE_IN_ONE_FOR_BLACK)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'tournament'
            result = run_tournament(config, output)
            colours = {(game.white_algorithm, game.black_algorithm) for game in result.records}
            self.assertEqual(colours, {(a, b) for a in algorithms for b in algorithms if a != b})
            self.assertTrue(all(game.finished and game.winner == game.black_algorithm
                                for game in result.records))
            with (output / 'moves.csv').open(encoding='utf-8', newline='') as handle:
                moves = list(csv.DictReader(handle))
            self.assertEqual(len(moves), 6)
            self.assertTrue(any(int(move['route_nodes']) > 0 for move in moves))
            self.assertTrue(any(int(move['qnodes']) > 0 for move in moves))


if __name__ == '__main__':
    unittest.main()
