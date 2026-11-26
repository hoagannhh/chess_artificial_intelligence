"""Bounded self-play and training, with resumable optimizer, replay and RNG state."""
import argparse
from collections import Counter, deque
import json
from pathlib import Path
import random
from time import perf_counter

import chess
import chess.pgn
import torch
from torch.nn import functional as F

from .encoding import action_index, encode
from .mcts import run_search, terminal_value
from .network import DEFAULT_MODEL, Evaluator, PolicyValueNet, load_checkpoint, save_checkpoint
from .replay import ReplayBuffer
from .teacher import TEACHER, VALUE_SCALE, sample_training_batch, teacher_game


def self_play(model, simulations, max_plies, rng, initial_fen=chess.STARTING_FEN,
              temperature_moves=30, late_temperature=0.75):
    board = chess.Board(initial_fen)
    if not board.is_valid() or terminal_value(board) is not None:
        raise ValueError('Self-play requires a valid, unfinished starting position')
    samples = []
    evaluator = Evaluator(model)
    model.eval()
    for ply in range(max_plies):
        tree = run_search(board, evaluator, simulations, rng=rng)
        moves = list(tree.policy)
        probabilities = list(tree.policy.values())
        samples.append(dict(state=encode(board).half(), turn=board.turn,
                            indices=torch.tensor([action_index(move) for move in moves]),
                            policy=torch.tensor(probabilities)))
        # Keep exploring after the opening to escape deterministic repetition cycles.
        temperature = 1.0 if ply < temperature_moves else late_temperature
        if temperature == 0:
            move = max(tree.policy, key=tree.policy.get)
        else:
            peak = max(probabilities)
            weights = [(probability / peak) ** (1 / temperature) for probability in probabilities]
            move = rng.choices(moves, weights)[0]
        board.push(move)
        if terminal_value(board) is not None:
            break
    outcome = board.outcome(claim_draw=True)
    for sample in samples:
        turn = sample.pop('turn')
        sample['value_known'] = outcome is not None
        sample['value'] = 0.0 if outcome is None or outcome.winner is None else (
            1.0 if outcome.winner == turn else -1.0)
    game = chess.pgn.Game.from_board(board)
    game.headers['White'] = game.headers['Black'] = 'AlphaZero self-play'
    game.headers['Result'] = outcome.result() if outcome else '*'
    game.headers['Termination'] = outcome.termination.name if outcome else 'max_plies'
    return samples, game


def train_batch(model, optimizer, samples):
    device = next(model.parameters()).device
    states = torch.stack([sample['state'] for sample in samples]).to(device=device, dtype=torch.float32)
    logits, values = model(states)
    log_probabilities = F.log_softmax(logits, dim=1)
    policy_loss = torch.stack([
        -(log_probabilities[row, sample['indices'].to(device)] * sample['policy'].to(device)).sum()
        for row, sample in enumerate(samples)
    ]).mean()
    targets = torch.tensor([sample['value'] for sample in samples], device=device)
    known = torch.tensor([sample['value_known'] for sample in samples], device=device)
    # Truncated games teach the search policy but supply no invented win/draw label.
    value_loss = ((values - targets).square() * known).sum() / known.sum().clamp_min(1)
    loss = policy_loss + value_loss
    if not torch.isfinite(loss):
        raise ValueError('Non-finite training loss')
    optimizer.zero_grad(set_to_none=True)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
    optimizer.step()
    return float(policy_loss.detach()), float(value_loss.detach())


def train(args):
    torch.set_num_threads(args.threads)
    output = args.output.resolve()
    if args.resume:
        if not (output / 'latest.pt').is_file():
            raise ValueError('Resume requires output/latest.pt')
    elif output.exists():
        raise ValueError('Output exists. Use --resume to continue it, or choose a new --output.')
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'training.lock'
    with lock.open('x') as handle:
        handle.write('Training in progress')
    try:
        rng = random.Random(args.seed)
        torch.manual_seed(args.seed)
        device = torch.device(args.device)
        metrics = []
        start_iteration = 0
        replay = ReplayBuffer(args.replay_size)
        teacher_replay = deque(maxlen=args.teacher_replay_size)
        lineage = []
        if args.resume:
            model, data = load_checkpoint(output / 'latest.pt')
            model.to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
            optimizer.load_state_dict(data['optimizer'])
            for group in optimizer.param_groups:
                group['lr'] = args.learning_rate
            replay.extend(data['replay'])
            teacher_replay.extend(data.get('teacher_replay', []))
            lineage = data.get('lineage', [])
            rng.setstate(data['random_state'])
            torch.set_rng_state(data['torch_state'])
            if device.type == 'cuda' and data.get('cuda_state') is not None:
                torch.cuda.set_rng_state_all(data['cuda_state'])
            metrics = data['metrics']
            start_iteration = data['iteration']
        else:
            if args.init_from:
                model, parent = load_checkpoint(args.init_from)
                model.to(device)
                lineage = [*parent.get('lineage', []), dict(model_id=parent['model_id'],
                           path=str(args.init_from.resolve()),
                           training_method=parent.get('training_method', 'self_play'))]
            else:
                model = PolicyValueNet(args.channels, args.blocks,
                                       value_activation=args.value_activation or 'leaky_relu').to(device)
            optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
        if args.value_activation:
            model.set_value_activation(args.value_activation)
        if not args.resume:
            save_checkpoint(output / 'initial.pt', model, iteration=0, trained=bool(args.init_from),
                            initialized_from=str(args.init_from) if args.init_from else '')
        config = {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()}
        config.update(model.config)
        config['teacher'] = TEACHER
        config['teacher_value_target'] = f'tanh(side_to_move_cp / {VALUE_SCALE:g})'
        for iteration in range(start_iteration + 1, start_iteration + args.iterations + 1):
            started = perf_counter()
            games = []
            counts = {'white_wins': 0, 'black_wins': 0, 'draws': 0, 'truncated': 0}
            terminations = Counter()
            teacher_games = []
            teacher_labels = teacher_skipped = 0
            teacher_depths = Counter()
            for number in range(args.teacher_games):
                print(f'Iteration {iteration}, teacher game {number + 1}/{args.teacher_games}', flush=True)
                samples, game, skipped = teacher_game(
                    args.teacher_depth, args.teacher_time_ms, args.max_plies, rng,
                    args.initial_fen, args.teacher_exploration)
                teacher_replay.extend(samples)
                teacher_labels += len(samples)
                teacher_skipped += skipped
                teacher_depths.update(sample['teacher_depth'] for sample in samples)
                teacher_games.append(str(game))
                print(f'  {game.headers["Result"]}, {len(samples)} labels, {skipped} skipped', flush=True)
            for number in range(args.games):
                samples, game = self_play(model, args.simulations, args.max_plies, rng, args.initial_fen,
                                          args.temperature_moves, args.late_temperature)
                replay.extend(samples)
                games.append(str(game))
                key = {'1-0': 'white_wins', '0-1': 'black_wins', '1/2-1/2': 'draws', '*': 'truncated'}[game.headers['Result']]
                counts[key] += 1
                terminations[game.headers['Termination']] += 1
                print(f'Iteration {iteration}, game {number + 1}/{args.games}: '
                      f'{game.headers["Result"]}, {len(samples)} plies', flush=True)
            model.train()
            losses = []
            population = list(replay)
            teacher_population = list(teacher_replay)
            if not population and not teacher_population:
                raise ValueError('No training labels. Increase the teacher search time.')
            method = 'self_play'
            if teacher_population and not population:
                method = 'supervised_teacher'
            elif teacher_population and args.teacher_ratio > 0:
                method = 'teacher_assisted_self_play'
            if not lineage or lineage[-1].get('training_method') != method:
                lineage.append(dict(training_method=method, started_iteration=iteration,
                                    teacher=TEACHER if method != 'self_play' else None))
            for _ in range(args.steps):
                batch = sample_training_batch(population, teacher_population, args.batch_size,
                                              args.teacher_ratio, rng)
                losses.append(train_batch(model, optimizer, batch))
            model.eval()
            metrics.append(dict(iteration=iteration, **counts, replay_positions=len(replay),
                                value_positions=sum(sample['value_known'] for sample in replay),
                                decisive_positions=len(replay.decisive), terminations=dict(terminations),
                                training_method=method, teacher_positions=len(teacher_replay),
                                teacher_labels=teacher_labels, teacher_skipped=teacher_skipped,
                                teacher_completed_depths=dict(teacher_depths),
                                policy_loss=sum(pair[0] for pair in losses) / len(losses),
                                value_loss=sum(pair[1] for pair in losses) / len(losses),
                                elapsed_seconds=round(perf_counter() - started, 2), config=config))
            save_checkpoint(output / 'latest.pt', model, iteration=iteration, trained=True,
                            optimizer=optimizer.state_dict(), replay=list(replay), metrics=metrics,
                            teacher_replay=list(teacher_replay), training_method=method, lineage=lineage,
                            random_state=rng.getstate(), torch_state=torch.get_rng_state(),
                            cuda_state=torch.cuda.get_rng_state_all() if device.type == 'cuda' else None)
            save_checkpoint(output / f'checkpoint-{iteration:04d}.pt', model,
                            iteration=iteration, trained=True, training_config=config,
                            training_method=method, lineage=lineage)
            save_checkpoint(output / 'current.pt', model, iteration=iteration, trained=True, training_config=config,
                            training_method=method, lineage=lineage)
            (output / f'selfplay-{iteration:04d}.pgn').write_text('\n\n'.join(games) + '\n', encoding='utf-8')
            if teacher_games:
                (output / f'teacher-{iteration:04d}.pgn').write_text('\n\n'.join(teacher_games) + '\n', encoding='utf-8')
            temporary = output / 'metrics.json.tmp'
            temporary.write_text(json.dumps(metrics, indent=2), encoding='utf-8')
            temporary.replace(output / 'metrics.json')
            print(f'Saved iteration {iteration}: policy loss {metrics[-1]["policy_loss"]:.4f}, '
                  f'value loss {metrics[-1]["value_loss"]:.4f}', flush=True)
            print(f'Replay: {len(replay.decisive)} decisive / {len(replay)} positions. '
                  f'Teacher: {len(teacher_replay)} positions. Terminations: {dict(terminations)}', flush=True)
            if population and not replay.decisive:
                print('Training warning: replay has no win/loss targets; value loss alone '
                      'cannot indicate playing strength.', flush=True)
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_MODEL.parent)
    parser.add_argument('--resume', action='store_true', help='Continue output/latest.pt')
    parser.add_argument('--init-from', type=Path, help='Start a new run from checkpoint weights with fresh replay/optimizer')
    parser.add_argument('--value-activation', choices=('relu', 'leaky_relu'), default='leaky_relu',
                        help='Value head used during training, including resumed runs')
    parser.add_argument('--iterations', type=int, default=2, help='Additional iterations this run')
    parser.add_argument('--games', type=int, default=2, help='Self-play games per iteration')
    parser.add_argument('--teacher-games', type=int, default=0, help='Teacher games per iteration; --games 0 gives supervised warm-up')
    parser.add_argument('--teacher-depth', type=int, default=3)
    parser.add_argument('--teacher-time-ms', type=int, default=200)
    parser.add_argument('--teacher-exploration', type=float, default=0.15)
    parser.add_argument('--teacher-replay-size', type=int, default=2048)
    parser.add_argument('--teacher-ratio', type=float, default=0.25, help='Teacher fraction in mixed batches')
    parser.add_argument('--simulations', type=int, default=32)
    parser.add_argument('--max-plies', type=int, default=256)
    parser.add_argument('--steps', type=int, default=32, help='Optimizer updates per iteration')
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--replay-size', type=int, default=2048)
    parser.add_argument('--channels', type=int, default=32)
    parser.add_argument('--blocks', type=int, default=2)
    parser.add_argument('--learning-rate', type=float, default=0.001)
    parser.add_argument('--threads', type=int, default=1)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--initial-fen', default=chess.STARTING_FEN)
    parser.add_argument('--temperature-moves', type=int, default=30)
    parser.add_argument('--late-temperature', type=float, default=0.75,
                        help='Self-play sampling after opening; 0 selects the most visited move')
    args = parser.parse_args()
    for name in ('iterations', 'simulations', 'max_plies', 'steps', 'batch_size',
                 'replay_size', 'channels', 'blocks', 'threads', 'teacher_replay_size'):
        if getattr(args, name) < 1:
            parser.error(f'{name} must be positive')
    if not 0 < args.learning_rate < 1:
        parser.error('learning-rate must be between 0 and 1')
    if args.resume and args.init_from:
        parser.error('Use either --resume or --init-from')
    if args.games < 0 or args.teacher_games < 0 or args.games + args.teacher_games == 0:
        parser.error('Supply self-play games, teacher games, or both')
    if not 1 <= args.teacher_depth <= 5 or not 50 <= args.teacher_time_ms <= 2000:
        parser.error('teacher-depth must be 1..5 and teacher-time-ms must be 50..2000')
    if not 0 <= args.teacher_exploration <= 1 or not 0 <= args.teacher_ratio <= 1:
        parser.error('teacher-exploration and teacher-ratio must be in [0,1]')
    if args.replay_size < 2 or args.temperature_moves < 0 or not 0 <= args.late_temperature <= 2:
        parser.error('replay-size must be at least 2; temperature-moves >= 0; late-temperature in [0,2]')
    if args.device == 'cuda' and not torch.cuda.is_available():
        parser.error('CUDA is unavailable in this PyTorch installation')
    try:
        train(args)
    except (ValueError, OSError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
