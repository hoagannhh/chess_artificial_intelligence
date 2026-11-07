"""Run repeatable AI matches: python -m backend.ai.match --games 2."""
import argparse
import csv
from dataclasses import fields
from backend.ai.search import ALGORITHMS, SearchResult
from pathlib import Path
from backend.application.session import Session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--white', choices=ALGORITHMS, default='minimax')
    parser.add_argument('--black', choices=ALGORITHMS, default='alphabeta')
    parser.add_argument('--games', type=int, default=2)
    parser.add_argument('--depth', type=int, default=3)
    parser.add_argument('--time-ms', type=int, default=1000)
    parser.add_argument('--max-plies', type=int, default=200)
    parser.add_argument('--output', type=Path, default=Path('.local/experiments/ai-match'))
    args = parser.parse_args()
    if not 1 <= args.games <= 100 or not 1 <= args.max_plies <= 1000:
        parser.error('games: 1..100; max-plies: 1..1000')
    if not 1 <= args.depth <= 5 or not 50 <= args.time_ms <= 2000:
        parser.error('depth: 1..5; time-ms: 50..2000')
    args.output.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents silently replacing earlier experimental results.
    with (args.output / 'moves.csv').open('x', newline='', encoding='utf-8') as handle:
        columns = ['game', 'ply', 'side'] + [field.name for field in fields(SearchResult)]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for game_id in range(args.games):
            session = Session()
            pair = [args.white, args.black] if game_id % 2 == 0 else [args.black, args.white]
            for ply in range(args.max_plies):
                side = 0 if session.game.board.turn else 1
                state = session.action({'action': 'ai_move', 'algorithm': pair[side],
                                        'depth': args.depth, 'time_limit_ms': args.time_ms})
                writer.writerow({'game': game_id + 1, 'ply': ply + 1, **state['ai_stats']})
                handle.flush()
                if state['finished']:
                    break
            pgn = state['pgn'].replace('[White "White"]', f'[White "{pair[0]}"]').replace('[Black "Black"]', f'[Black "{pair[1]}"]')
            if not state['finished']:
                pgn += '\n{Stopped at experimental ply limit; not adjudicated as a draw.}\n'
            (args.output / f'game-{game_id + 1}.pgn').write_text(pgn, encoding='utf-8')
            print(f"Game {game_id + 1}: {pair[0]} vs {pair[1]}: {state['result']} ({len(state['history'])} plies)", flush=True)


if __name__ == '__main__':
    main()
