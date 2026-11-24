"""Run reproducible round-robin tournaments between the bundled chess AIs.

Example:
    python -m backend.ai.tournament --games-per-pair 4 --output .local/experiments/run-01

The runner deliberately lives outside the Godot UI: it creates independent in-memory
sessions and never touches the player's autosave.  Every run writes raw game/move data,
per-AI standings, head-to-head summaries, PGNs, and a Markdown table ready for a report.
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Callable

import chess

from backend.ai.search import ALGORITHMS, SearchResult
from backend.application.session import Session


SCHEMA_VERSION = 1
GAME_COLUMNS = (
    'game_id', 'pairing_id', 'round', 'algorithm_a', 'algorithm_b',
    'white_algorithm', 'black_algorithm', 'result', 'winner', 'finished',
    'limit_reached', 'plies', 'termination', 'initial_fen', 'pgn_file',
)
MOVE_COLUMNS = (
    'game_id', 'pairing_id', 'round', 'white_algorithm', 'black_algorithm', 'ply', 'side',
) + tuple(field.name for field in fields(SearchResult))
SUMMARY_COLUMNS = (
    'algorithm', 'games', 'finished_games', 'wins', 'draws', 'losses', 'unfinished',
    'games_as_white', 'games_as_black', 'wins_as_white', 'wins_as_black',
    'points', 'score_percent', 'moves', 'avg_elapsed_ms', 'avg_nodes', 'avg_cutoffs',
)
HEAD_TO_HEAD_COLUMNS = (
    'pairing_id', 'algorithm_a', 'algorithm_b', 'games', 'finished_games',
    'algorithm_a_wins', 'algorithm_b_wins', 'draws', 'unfinished',
    'algorithm_a_points', 'algorithm_b_points',
    'algorithm_a_white_games', 'algorithm_a_black_games',
)


@dataclass(frozen=True)
class TournamentConfig:
    """Configuration shared by every game in one experiment run."""

    algorithms: tuple[str, ...]
    games_per_pair: int = 2
    depth: int = 1
    time_limit_ms: int = 100
    max_plies: int = 80
    initial_fen: str = chess.STARTING_FEN


@dataclass(frozen=True)
class GamePlan:
    """One scheduled game, including its balanced colour assignment."""

    game_id: int
    pairing_id: int
    round_index: int
    algorithm_a: str
    algorithm_b: str
    white_algorithm: str
    black_algorithm: str


@dataclass(frozen=True)
class GameRecord:
    """A completed or stopped game, suitable for CSV/JSON serialization."""

    game_id: int
    pairing_id: int
    round_index: int
    algorithm_a: str
    algorithm_b: str
    white_algorithm: str
    black_algorithm: str
    result: str
    winner: str
    finished: bool
    limit_reached: bool
    plies: int
    termination: str
    initial_fen: str
    pgn_file: str

    def to_row(self) -> dict[str, object]:
        row = asdict(self)
        row['round'] = row.pop('round_index')
        return row


@dataclass
class PlayedGame:
    """Raw per-move data and PGN accompanying one :class:`GameRecord`."""

    record: GameRecord
    move_rows: list[dict[str, object]]
    pgn: str


@dataclass
class TournamentResult:
    """Return value of :func:`run_tournament`, useful for tests or callers."""

    output: Path
    records: list[GameRecord]
    summary: list[dict[str, object]]
    head_to_head: list[dict[str, object]]


def validate_config(config: TournamentConfig) -> None:
    """Reject configurations that would make the comparison unfair or invalid."""

    algorithms = config.algorithms
    if len(algorithms) < 2:
        raise ValueError('Choose at least two different algorithms')
    if len(set(algorithms)) != len(algorithms):
        raise ValueError('Algorithms must not be repeated')
    unknown = set(algorithms).difference(ALGORITHMS)
    if unknown:
        raise ValueError('Unknown algorithm: ' + ', '.join(sorted(unknown)))
    if type(config.games_per_pair) is not int or not 2 <= config.games_per_pair <= 100:
        raise ValueError('games-per-pair must be an integer from 2 to 100')
    if config.games_per_pair % 2:
        raise ValueError('games-per-pair must be even so each AI receives equal colours')
    if type(config.depth) is not int or not 1 <= config.depth <= 5:
        raise ValueError('depth must be an integer from 1 to 5')
    if type(config.time_limit_ms) is not int or not 50 <= config.time_limit_ms <= 2000:
        raise ValueError('time-ms must be an integer from 50 to 2000')
    if type(config.max_plies) is not int or not 1 <= config.max_plies <= 1000:
        raise ValueError('max-plies must be an integer from 1 to 1000')
    try:
        board = chess.Board(config.initial_fen)
    except ValueError as error:
        raise ValueError('initial-fen is invalid') from error
    if not board.is_valid():
        raise ValueError('initial-fen describes an invalid board')
    if board.outcome() is not None:
        raise ValueError('initial-fen is already a finished game')


def build_schedule(config: TournamentConfig) -> list[GamePlan]:
    """Create one balanced home/away pairing for every unordered AI pair."""

    validate_config(config)
    plans: list[GamePlan] = []
    game_id = 1
    for pairing_id, (algorithm_a, algorithm_b) in enumerate(combinations(config.algorithms, 2), start=1):
        for round_index in range(1, config.games_per_pair + 1):
            # Alternating at every round guarantees equal White/Black games because the
            # configured number of games per pair is even.
            white, black = ((algorithm_a, algorithm_b)
                            if round_index % 2 else (algorithm_b, algorithm_a))
            plans.append(GamePlan(game_id, pairing_id, round_index, algorithm_a, algorithm_b, white, black))
            game_id += 1
    return plans


def _new_session(initial_fen: str) -> Session:
    """Return an in-memory session starting from the configured valid position."""

    session = Session()
    session.game.board = chess.Board(initial_fen)
    return session


def _winner(result: str, white: str, black: str, finished: bool) -> str:
    if not finished:
        return ''
    if result == '1-0':
        return white
    if result == '0-1':
        return black
    return ''


def _label_pgn(pgn: str, plan: GamePlan, finished: bool) -> str:
    labelled = pgn.replace('[White "White"]', f'[White "{plan.white_algorithm}"]')
    labelled = labelled.replace('[Black "Black"]', f'[Black "{plan.black_algorithm}"]')
    if not finished:
        labelled += '\n{Stopped at experimental ply limit; not adjudicated as a draw.}\n'
    return labelled


def play_game(plan: GamePlan, config: TournamentConfig) -> PlayedGame:
    """Play one scheduled game in memory and capture every AI decision."""

    session = _new_session(config.initial_fen)
    move_rows: list[dict[str, object]] = []
    state = session.snapshot()
    for ply in range(1, config.max_plies + 1):
        side = 'white' if session.game.board.turn else 'black'
        algorithm = plan.white_algorithm if side == 'white' else plan.black_algorithm
        state = session.action({
            'action': 'ai_move',
            'algorithm': algorithm,
            'depth': config.depth,
            'time_limit_ms': config.time_limit_ms,
        })
        stats = state.get('ai_stats')
        if stats:
            row: dict[str, object] = {
                'game_id': plan.game_id,
                'pairing_id': plan.pairing_id,
                'round': plan.round_index,
                'white_algorithm': plan.white_algorithm,
                'black_algorithm': plan.black_algorithm,
                'ply': ply,
                'side': side,
            }
            row.update(stats)
            move_rows.append(row)
        if state['finished']:
            break

    finished = bool(state['finished'])
    result = str(state['result']) if finished else '*'
    filename = f'game-{plan.game_id:03d}.pgn'
    record = GameRecord(
        game_id=plan.game_id,
        pairing_id=plan.pairing_id,
        round_index=plan.round_index,
        algorithm_a=plan.algorithm_a,
        algorithm_b=plan.algorithm_b,
        white_algorithm=plan.white_algorithm,
        black_algorithm=plan.black_algorithm,
        result=result,
        winner=_winner(result, plan.white_algorithm, plan.black_algorithm, finished),
        finished=finished,
        limit_reached=not finished,
        plies=len(state['history']),
        termination=str(state['detail']) if finished else 'Stopped at max_plies',
        initial_fen=config.initial_fen,
        pgn_file=filename,
    )
    return PlayedGame(record, move_rows, _label_pgn(str(state['pgn']), plan, finished))


def _empty_standing(algorithm: str) -> dict[str, object]:
    return {
        'algorithm': algorithm,
        'games': 0,
        'finished_games': 0,
        'wins': 0,
        'draws': 0,
        'losses': 0,
        'unfinished': 0,
        'games_as_white': 0,
        'games_as_black': 0,
        'wins_as_white': 0,
        'wins_as_black': 0,
        'points': 0.0,
        'score_percent': None,
        'moves': 0,
        'avg_elapsed_ms': None,
        'avg_nodes': None,
        'avg_cutoffs': None,
        '_elapsed_total': 0.0,
        '_nodes_total': 0,
        '_cutoffs_total': 0,
    }


def summarize(
    algorithms: tuple[str, ...], records: list[GameRecord], move_rows: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Calculate standings and per-pair results from immutable raw records."""

    standings = {algorithm: _empty_standing(algorithm) for algorithm in algorithms}
    pairings: dict[int, dict[str, object]] = {}

    for record in records:
        pair = pairings.setdefault(record.pairing_id, {
            'pairing_id': record.pairing_id,
            'algorithm_a': record.algorithm_a,
            'algorithm_b': record.algorithm_b,
            'games': 0,
            'finished_games': 0,
            'algorithm_a_wins': 0,
            'algorithm_b_wins': 0,
            'draws': 0,
            'unfinished': 0,
            'algorithm_a_points': 0.0,
            'algorithm_b_points': 0.0,
            'algorithm_a_white_games': 0,
            'algorithm_a_black_games': 0,
        })
        pair['games'] += 1
        pair['algorithm_a_white_games'] += int(record.white_algorithm == record.algorithm_a)
        pair['algorithm_a_black_games'] += int(record.black_algorithm == record.algorithm_a)

        for algorithm, colour in ((record.white_algorithm, 'white'), (record.black_algorithm, 'black')):
            standing = standings[algorithm]
            standing['games'] += 1
            standing[f'games_as_{colour}'] += 1

        if not record.finished:
            standings[record.white_algorithm]['unfinished'] += 1
            standings[record.black_algorithm]['unfinished'] += 1
            pair['unfinished'] += 1
            continue

        pair['finished_games'] += 1
        standings[record.white_algorithm]['finished_games'] += 1
        standings[record.black_algorithm]['finished_games'] += 1
        if record.result == '1-0':
            winner, loser = record.white_algorithm, record.black_algorithm
        elif record.result == '0-1':
            winner, loser = record.black_algorithm, record.white_algorithm
        else:
            for algorithm in (record.white_algorithm, record.black_algorithm):
                standings[algorithm]['draws'] += 1
                standings[algorithm]['points'] += 0.5
            pair['draws'] += 1
            pair['algorithm_a_points'] += 0.5
            pair['algorithm_b_points'] += 0.5
            continue

        standings[winner]['wins'] += 1
        standings[winner]['points'] += 1.0
        standings[loser]['losses'] += 1
        standings[winner][f'wins_as_{"white" if winner == record.white_algorithm else "black"}'] += 1
        if winner == record.algorithm_a:
            pair['algorithm_a_wins'] += 1
            pair['algorithm_a_points'] += 1.0
        else:
            pair['algorithm_b_wins'] += 1
            pair['algorithm_b_points'] += 1.0

    for row in move_rows:
        algorithm = str(row['algorithm'])
        if algorithm not in standings:
            continue
        standing = standings[algorithm]
        standing['moves'] += 1
        standing['_elapsed_total'] += float(row.get('elapsed_ms') or 0.0)
        standing['_nodes_total'] += int(row.get('nodes') or 0)
        standing['_cutoffs_total'] += int(row.get('cutoffs') or 0)

    summary: list[dict[str, object]] = []
    for algorithm in algorithms:
        standing = standings[algorithm]
        finished_games = int(standing['finished_games'])
        moves = int(standing['moves'])
        standing['score_percent'] = round(100 * float(standing['points']) / finished_games, 2) if finished_games else None
        standing['points'] = round(float(standing['points']), 2)
        standing['avg_elapsed_ms'] = round(float(standing['_elapsed_total']) / moves, 2) if moves else None
        standing['avg_nodes'] = round(int(standing['_nodes_total']) / moves, 2) if moves else None
        standing['avg_cutoffs'] = round(int(standing['_cutoffs_total']) / moves, 2) if moves else None
        for private in ('_elapsed_total', '_nodes_total', '_cutoffs_total'):
            del standing[private]
        summary.append(standing)

    return summary, list(pairings.values())


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open('x', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction='raise')
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, value: object) -> None:
    with path.open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write('\n')


def _format_cell(value: object) -> str:
    if value is None:
        return '—'
    if isinstance(value, float):
        return f'{value:.2f}'
    return str(value)


def _markdown_table(columns: tuple[str, ...], rows: list[dict[str, object]]) -> str:
    headings = [column.replace('_', ' ') for column in columns]
    lines = [
        '| ' + ' | '.join(headings) + ' |',
        '| ' + ' | '.join('---:' if column not in ('algorithm', 'algorithm_a', 'algorithm_b') else '---' for column in columns) + ' |',
    ]
    for row in rows:
        lines.append('| ' + ' | '.join(_format_cell(row[column]) for column in columns) + ' |')
    return '\n'.join(lines)


def _write_report_summary(path: Path, config: TournamentConfig, summary: list[dict[str, object]], head_to_head: list[dict[str, object]]) -> None:
    config_text = [
        '# Kết quả thực nghiệm AI',
        '',
        '## Cấu hình',
        '',
        f'- Thuật toán: {", ".join(config.algorithms)}',
        f'- Số ván mỗi cặp: {config.games_per_pair} (đổi màu cân bằng)',
        f'- Độ sâu / rollout level: {config.depth}',
        f'- Giới hạn thời gian mỗi nước: {config.time_limit_ms} ms',
        f'- Giới hạn mỗi ván: {config.max_plies} ply',
        f'- FEN xuất phát: `{config.initial_fen}`',
        '',
        '## Bảng xếp hạng tổng hợp',
        '',
        _markdown_table(SUMMARY_COLUMNS, summary),
        '',
        '## Đối đầu từng cặp',
        '',
        _markdown_table(HEAD_TO_HEAD_COLUMNS, head_to_head),
        '',
        '## Cách đọc kết quả',
        '',
        '- `points = wins + 0.5 × draws`; `score_percent` chỉ tính trên các ván đã kết thúc.',
        '- Ván chạm `max_plies` được ghi là `unfinished`, không được tính là hòa hoặc cộng điểm.',
        '- `avg_nodes` và `avg_cutoffs` chỉ nên so sánh trực tiếp giữa các thuật toán cùng kiểu tìm kiếm. Node của MCTS có ý nghĩa khác với node của Minimax/Alpha-Beta/PVS.',
        '- Kết quả chỉ có giá trị học thuật khi ghi rõ phần cứng, phiên bản mã, cấu hình và chạy đủ nhiều ván/ thế cờ độc lập.',
        '',
    ]
    path.write_text('\n'.join(config_text), encoding='utf-8', newline='\n')


def run_tournament(
    config: TournamentConfig,
    output: Path,
    *,
    game_runner: Callable[[GamePlan, TournamentConfig], PlayedGame] = play_game,
) -> TournamentResult:
    """Run a full round-robin event and write all artifacts into a new directory.

    ``game_runner`` is injectable solely to make aggregation and output behavior easy to
    test without spending time searching chess positions.
    """

    validate_config(config)
    output = Path(output)
    if output.exists():
        raise FileExistsError(f'Output already exists: {output}. Choose a new directory.')
    output.mkdir(parents=True)
    plans = build_schedule(config)
    records: list[GameRecord] = []
    move_rows: list[dict[str, object]] = []

    try:
        with (output / 'games.csv').open('x', newline='', encoding='utf-8') as game_handle, \
             (output / 'moves.csv').open('x', newline='', encoding='utf-8') as move_handle:
            game_writer = csv.DictWriter(game_handle, fieldnames=GAME_COLUMNS, extrasaction='raise')
            move_writer = csv.DictWriter(move_handle, fieldnames=MOVE_COLUMNS, extrasaction='raise')
            game_writer.writeheader()
            move_writer.writeheader()
            for plan in plans:
                played = game_runner(plan, config)
                record = played.record
                if record.game_id != plan.game_id:
                    raise ValueError('Game runner returned a record for the wrong game')
                game_writer.writerow(record.to_row())
                move_writer.writerows(played.move_rows)
                game_handle.flush()
                move_handle.flush()
                (output / record.pgn_file).write_text(played.pgn, encoding='utf-8', newline='\n')
                records.append(record)
                move_rows.extend(played.move_rows)
                print(
                    f'Game {record.game_id:03d}: {record.white_algorithm} (White) vs '
                    f'{record.black_algorithm} (Black) -> {record.result} '
                    f'[{record.termination}; {record.plies} plies]',
                    flush=True,
                )

        summary, head_to_head = summarize(config.algorithms, records, move_rows)
        _write_csv(output / 'summary.csv', SUMMARY_COLUMNS, summary)
        _write_csv(output / 'head_to_head.csv', HEAD_TO_HEAD_COLUMNS, head_to_head)
        metadata = {
            'schema_version': SCHEMA_VERSION,
            'created_at_utc': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            'config': {
                'algorithms': list(config.algorithms),
                'games_per_pair': config.games_per_pair,
                'depth': config.depth,
                'time_limit_ms': config.time_limit_ms,
                'max_plies': config.max_plies,
                'initial_fen': config.initial_fen,
                'mcts_seed': 0,
            },
            'environment': {
                'python_version': sys.version.split()[0],
                'platform': platform.platform(),
            },
            'counts': {
                'planned_games': len(plans),
                'finished_games': sum(record.finished for record in records),
                'unfinished_games': sum(not record.finished for record in records),
                'moves': len(move_rows),
            },
            'files': ['games.csv', 'moves.csv', 'summary.csv', 'head_to_head.csv', 'metadata.json', 'summary.json', 'report_summary.md'],
        }
        _write_json(output / 'metadata.json', metadata)
        _write_json(output / 'summary.json', {
            'schema_version': SCHEMA_VERSION,
            'metadata': metadata,
            'standings': summary,
            'head_to_head': head_to_head,
        })
        _write_report_summary(output / 'report_summary.md', config, summary, head_to_head)
        return TournamentResult(output, records, summary, head_to_head)
    except Exception:
        # Partial CSV/PGN files are intentionally retained for diagnosis; the caller can
        # choose a fresh directory after resolving the failure.
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description='Run a balanced round-robin tournament between chess AIs.')
    parser.add_argument('--algorithms', nargs='+', choices=ALGORITHMS, default=list(ALGORITHMS))
    parser.add_argument('--games-per-pair', type=int, default=2, help='Even number, alternating White/Black.')
    parser.add_argument('--depth', type=int, default=1, help='Depth for search AIs; rollout level for MCTS.')
    parser.add_argument('--time-ms', type=int, default=100, help='Search budget per move, 50..2000.')
    parser.add_argument('--max-plies', type=int, default=80, help='Stop unfinished games after this many half-moves.')
    parser.add_argument('--initial-fen', default=chess.STARTING_FEN, help='Optional valid non-terminal FEN shared by every game.')
    parser.add_argument('--output', type=Path, required=True, help='New directory for this run; it must not already exist.')
    args = parser.parse_args()
    config = TournamentConfig(tuple(args.algorithms), args.games_per_pair, args.depth, args.time_ms, args.max_plies, args.initial_fen)
    try:
        result = run_tournament(config, args.output)
    except (ValueError, FileExistsError) as error:
        parser.error(str(error))
    print(f'\nTournament complete: {len(result.records)} games. Results: {result.output / "report_summary.md"}', flush=True)


if __name__ == '__main__':
    main()
