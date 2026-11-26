"""Results from interactive AI games and completed local tournament runs."""
import csv
from collections import defaultdict
from pathlib import Path

from backend.ai.search import ALGORITHMS, NEURAL_NAMES


LIVE_FIELDS = ('game_id', 'white_algorithm', 'black_algorithm', 'result', 'termination',
               'start_ply', 'plies', 'initial_fen', 'depth', 'time_limit_ms', 'clock_minutes', 'model_id',
               'white_model_id', 'black_model_id')
OUTCOMES = ('1-0', '1/2-1/2', '0-1', '*')


def standings(games):
    totals = defaultdict(lambda: dict(games=0, wins=0, draws=0, losses=0, unfinished=0, self_play=0))
    pairs = defaultdict(lambda: dict(a_wins=0, draws=0, b_wins=0, unfinished=0))
    for game in games:
        white, black, result = game['white_algorithm'], game['black_algorithm'], game['result']
        a, b = sorted((white, black))
        pair = pairs[a, b]
        for algorithm in {white, black}:
            totals[algorithm]['games'] += 1
        if result == '*':
            pair['unfinished'] += 1
        elif result == '1/2-1/2':
            pair['draws'] += 1
        else:
            # When both seats use the same AI, A denotes White and B denotes Black.
            a_won = (white == a) == (result == '1-0')
            pair['a_wins' if a_won else 'b_wins'] += 1
        if white == black:
            totals[white]['self_play'] += 1
        elif result in ('*', '1/2-1/2'):
            key = 'unfinished' if result == '*' else 'draws'
            totals[white][key] += 1
            totals[black][key] += 1
        else:
            winner, loser = (white, black) if result == '1-0' else (black, white)
            totals[winner]['wins'] += 1
            totals[loser]['losses'] += 1
    return {
        'games': len(games),
        'standings': [dict(algorithm=name, **totals[name]) for name in sorted(totals)],
        'pairs': [dict(a=a, b=b, **counts) for (a, b), counts in sorted(pairs.items())],
    }


class ExperimentResults:
    def __init__(self, root=None):
        self.root = Path(root) if root is not None else None
        self.memory = {}

    def live_rows(self):
        if self.root is None:
            return self.memory.copy()
        path = self.root / 'interface-games.csv'
        if not path.exists():
            return {}
        with path.open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or ()) not in (LIVE_FIELDS, LIVE_FIELDS[:-2], LIVE_FIELDS[:-3]):
                raise ValueError('Invalid interface-games.csv header')
            rows = {}
            for row in reader:
                for color in ('white', 'black'):
                    legacy_id = row.get('model_id', '') if row[f'{color}_algorithm'] in NEURAL_NAMES else ''
                    row.setdefault(f'{color}_model_id', legacy_id)
                rows[row['game_id']] = row
            return rows

    def reconcile(self, game):
        rows = self.live_rows()
        context = game.experiment
        if context and game.finished:
            row = dict(context, game_id=game.game_id, result=game.result(), termination=game.status()[1],
                       plies=len(game.history) - context['start_ply'],
                       clock_minutes=game.clock.minutes if game.clock else 0)
            row = {key: str(row.get(key, '')) for key in LIVE_FIELDS}
            if rows.get(game.game_id) == row:
                return
            rows[game.game_id] = row
        elif rows.pop(game.game_id, None) is None:
            return
        if self.root is None:
            self.memory = rows
            return
        self.root.mkdir(parents=True, exist_ok=True)
        temp = self.root / 'interface-games.csv.tmp'
        with temp.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=LIVE_FIELDS)
            writer.writeheader()
            writer.writerows(rows.values())
        temp.replace(self.root / 'interface-games.csv')

    def report(self):
        def outcomes(rows):
            games = []
            for number, row in enumerate(rows, start=1):
                white, black, result = (row[key] for key in ('white_algorithm', 'black_algorithm', 'result'))
                white_id = row.get('white_model_id', row.get('model_id', ''))
                black_id = row.get('black_model_id', row.get('model_id', ''))
                if white in NEURAL_NAMES and white_id:
                    white = f'{NEURAL_NAMES[white]} [{white_id}]'
                if black in NEURAL_NAMES and black_id:
                    black = f'{NEURAL_NAMES[black]} [{black_id}]'
                if not white or not black or result not in OUTCOMES:
                    raise ValueError('Invalid experiment result')
                games.append(dict(game_id=row.get('game_id') or str(number), number=number,
                                  white_algorithm=white, black_algorithm=black, result=result))
            return games

        live = outcomes(self.live_rows().values())
        combined = live.copy()
        sources = [dict(name='Ván trên giao diện', matches=live, **standings(live))]
        skipped = []
        if self.root and self.root.is_dir():
            for marker in sorted(self.root.rglob('summary.json')):
                folder = marker.parent
                name = str(folder.relative_to(self.root))
                try:
                    with (folder / 'games.csv').open(encoding='utf-8-sig', newline='') as stream:
                        games = outcomes(csv.DictReader(stream))
                except (OSError, ValueError, KeyError, csv.Error):
                    skipped.append(name)
                    continue
                sources.append(dict(name=name, matches=games, **standings(games)))
                combined.extend(games)
        return {'sources': [dict(name='Tất cả thực nghiệm', **standings(combined)), *sources],
                'skipped': skipped}


def experiment_for_move(game, players, algorithm, depth, limit):
    if players is None:
        return None
    if (not isinstance(players, list) or len(players) != 2
            or any(player not in ALGORITHMS for player in players)
            or players[0 if game.board.turn else 1] != algorithm):
        raise ValueError('Invalid AI vs AI players')
    settings = dict(white_algorithm=players[0], black_algorithm=players[1],
                    depth=depth, time_limit_ms=limit)
    if game.experiment and all(game.experiment[k] == v for k, v in settings.items()):
        return game.experiment
    return dict(settings, start_ply=len(game.history), initial_fen=game.board.fen())
