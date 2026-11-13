from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from backend.application.session import Session


class ChessClockTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        clock_patch = patch('backend.domain.clock.monotonic', side_effect=lambda: self.now)
        clock_patch.start()
        self.addCleanup(clock_patch.stop)

    def test_switches_on_legal_move_and_undo_restores_clock(self):
        session = Session()
        session.action({'action': 'reset', 'clock_minutes': 5})
        self.now += 12
        with self.assertRaises(ValueError):
            session.action({'action': 'move', 'move': 'e2e5'})
        state = session.action({'action': 'move', 'move': 'e2e4'})
        self.assertEqual(state['clock']['remaining_ms'], {'white': 288000, 'black': 300000})
        self.now += 4
        self.assertEqual(session.snapshot()['clock']['remaining_ms']['black'], 296000)
        state = session.action({'action': 'undo'})
        self.assertEqual(state['turn'], 'white')
        self.assertEqual(state['clock']['remaining_ms'], {'white': 300000, 'black': 300000})

    def test_expiry_rejects_late_move_and_survives_restart(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'game.json'
            session = Session(path)
            session.action({'action': 'reset', 'clock_minutes': 5})
            self.now += 300
            state = session.action({'action': 'move', 'move': 'e2e4'})
            self.assertEqual(state['history'], [])
            self.assertEqual(state['result'], '0-1')
            self.assertFalse(state['clock']['running'])
            self.assertEqual(state['clock']['remaining_ms']['white'], 0)
            restored = Session(path).snapshot()
            self.assertEqual(restored['result'], '0-1')
            self.assertEqual(restored['clock'], state['clock'])

    def test_live_clock_resumes_from_saved_balances(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'game.json'
            session = Session(path)
            session.action({'action': 'reset', 'clock_minutes': 10})
            self.now += 5
            session.action({'action': 'move', 'move': 'e2e4'})
            self.now += 20
            session.persist()
            self.now += 300
            restored = Session(path)
            self.assertEqual(restored.snapshot()['clock']['remaining_ms'], {'white': 595000, 'black': 580000})
            self.now += 2
            self.assertEqual(restored.snapshot()['clock']['remaining_ms']['black'], 578000)


if __name__ == '__main__':
    unittest.main()
