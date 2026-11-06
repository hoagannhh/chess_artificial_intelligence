import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import chess.pgn
from backend.application.session import Session


class AppLifecycleTests(unittest.TestCase):
    def test_autosave_restore_and_pgn_replay(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'current.json'
            session = Session(path)
            for move in ['e2e4', 'e7e5', 'g1f3']:
                session.action({'action': 'move', 'move': move})
            restored = Session(path)
            self.assertEqual(restored.game.board.fen(), session.game.board.fen())
            self.assertEqual(restored.game.history, ['e4', 'e5', 'Nf3'])
            record = chess.pgn.read_game(io.StringIO(restored.snapshot()['pgn']))
            self.assertFalse(record.errors)
            self.assertEqual(record.end().board().fen(), restored.game.board.fen())
            restored.action({'action': 'undo'})
            self.assertEqual(Session(path).game.history, ['e4', 'e5'])
            restored.action({'action': 'reset'})
            self.assertEqual(Session(path).game.history, [])

    def test_resign_draw_and_undo(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'current.json'
            session = Session(path)
            session.action({'action': 'move', 'move': 'e2e4'})
            state = session.action({'action': 'resign'})
            self.assertEqual(state['result'], '1-0')
            self.assertEqual(state['legal'], [])
            self.assertEqual(Session(path).snapshot()['result'], '1-0')
            with self.assertRaises(ValueError):
                session.action({'action': 'move', 'move': 'e7e5'})
            state = session.action({'action': 'undo'})
            self.assertFalse(state['finished'])
            self.assertEqual(state['history'], ['e4'])
            state = session.action({'action': 'agree_draw'})
            self.assertEqual(state['result'], '1/2-1/2')
            self.assertTrue(Session(path).game.agreed_draw)
            record = chess.pgn.read_game(io.StringIO(state['pgn']))
            self.assertEqual(record.headers['Result'], '1/2-1/2')

    def test_corrupt_save_is_preserved_and_load_is_atomic(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'current.json'
            path.write_text('{broken', encoding='utf-8')
            session = Session(path)
            session.action({'action': 'move', 'move': 'e2e4'})
            self.assertEqual(path.read_text(), '{broken')
            before = session.game.board.fen()
            with self.assertRaises(ValueError):
                session.action({'action': 'load'})
            self.assertEqual(session.game.board.fen(), before)
            session.action({'action': 'reset'})
            self.assertEqual(path.with_suffix('.invalid.json').read_text(), '{broken')
            self.assertEqual(Session(path).game.history, [])

    def test_claimed_draw_restores_repetition_history(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'current.json'
            session = Session(path)
            for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 2:
                session.action({'action': 'move', 'move': move})
            session.action({'action': 'claim'})
            restored = Session(path)
            self.assertTrue(restored.game.claimed_draw)
            self.assertTrue(restored.game.board.can_claim_threefold_repetition())
            restored.action({'action': 'undo'})
            self.assertFalse(restored.game.finished)
            self.assertEqual(len(restored.game.history), 8)

    def test_invalid_saved_result_and_illegal_moves_rejected(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'current.json'
            session = Session(path)
            session.action({'action': 'save'})
            data = json.loads(path.read_text())
            data['moves'] = ['e2e5']
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                session.action({'action': 'load'})
            self.assertEqual(session.game.history, [])


if __name__ == '__main__':
    unittest.main()
