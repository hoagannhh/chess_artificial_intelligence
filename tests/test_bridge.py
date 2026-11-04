import json
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from backend.application.session import Session
from backend.api.server import make_server


class BridgeTests(unittest.TestCase):
    def test_state_move_undo_and_reset(self):
        s = Session()
        self.assertEqual(len(s.snapshot()['pieces']), 32)
        self.assertEqual(len(s.snapshot()['legal']), 20)
        result = s.action({'action': 'move', 'move': 'e2e4'})
        self.assertEqual(result['turn'], 'black')
        self.assertEqual(result['history'], ['e4'])
        self.assertEqual(result['last'], 'e2e4')
        self.assertEqual(s.action({'action': 'undo'})['history'], [])
        self.assertEqual(s.action({'action': 'reset'})['turn'], 'white')

    def test_bad_move_leaves_state_unchanged(self):
        s = Session()
        before = s.snapshot()
        with self.assertRaises(ValueError):
            s.action({'action': 'move', 'move': 'e2e5'})
        self.assertEqual(s.snapshot(), before)

    def test_http_contract(self):
        server = make_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(url + '/state') as response:
                self.assertEqual(len(json.load(response)['legal']), 20)
            request = Request(url + '/action', data=b'{"action":"move","move":"e2e4"}',
                              headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertEqual(json.load(response)['history'], ['e4'])
            request = Request(url + '/action', data=b'{"action":"reset"}',
                              headers={'Origin': 'https://example.com'})
            with self.assertRaises(HTTPError) as caught:
                urlopen(request)
            self.assertEqual(caught.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
