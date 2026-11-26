"""Compact residual policy/value network and versioned checkpoint files."""
import hashlib
import io
import os
import pickle
from pathlib import Path
import tempfile

import torch
from torch import nn

from .encoding import ACTIONS, PLANES, action_index, encode

DEFAULT_MODEL = Path(__file__).resolve().parents[3] / '.local/models/alphazero/current.pt'
DEFAULT_TEACHER_MODEL = DEFAULT_MODEL.parent.parent / 'alphazero-teacher-01/current.pt'
FORMAT = 1


class ResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Conv2d(channels, channels, 3, padding=1), nn.ReLU(),
            nn.Conv2d(channels, channels, 3, padding=1))

    def forward(self, inputs):
        return torch.relu(inputs + self.layers(inputs))


class PolicyValueNet(nn.Module):
    def __init__(self, channels=32, blocks=2, value_activation='relu'):
        super().__init__()
        self.config = dict(channels=channels, blocks=blocks, value_activation=value_activation)
        self.body = nn.Sequential(nn.Conv2d(PLANES, channels, 3, padding=1), nn.ReLU(),
                                  *(ResidualBlock(channels) for _ in range(blocks)))
        self.policy = nn.Sequential(nn.Conv2d(channels, 2, 1), nn.ReLU(),
                                    nn.Flatten(), nn.Linear(128, ACTIONS))
        self.value = nn.Sequential(nn.Conv2d(channels, 1, 1), nn.ReLU(), nn.Flatten(),
                                   nn.Linear(64, 64), nn.ReLU(), nn.Linear(64, 1), nn.Tanh())
        self.set_value_activation(value_activation)

    def set_value_activation(self, activation):
        if activation not in ('relu', 'leaky_relu'):
            raise ValueError('Unsupported value activation')
        for index in (1, 4):
            self.value[index] = nn.LeakyReLU(0.01) if activation == 'leaky_relu' else nn.ReLU()
        self.config['value_activation'] = activation

    def forward(self, inputs):
        features = self.body(inputs)
        return self.policy(features), self.value(features).squeeze(-1)


class Evaluator:
    def __init__(self, model):
        self.model = model

    @torch.inference_mode()
    def __call__(self, board):
        moves = sorted(board.legal_moves, key=lambda move: move.uci())
        device = next(self.model.parameters()).device
        logits, value = self.model(encode(board).unsqueeze(0).to(device))
        indices = [action_index(move) for move in moves]
        probabilities = torch.softmax(logits[0, indices], dim=0).cpu().tolist()
        return dict(zip(moves, probabilities)), float(value.item())


def save_checkpoint(path, model, **training):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(format=FORMAT, config=model.config, weights=model.state_dict(), **training)
    # Unique temporary file and atomic replacement allow safe readers during training.
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.tmp', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        torch.save(data, temporary)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load_checkpoint(path):
    try:
        # weights_only prevents arbitrary Python object deserialization.
        content = Path(path).read_bytes()
        data = torch.load(io.BytesIO(content), map_location='cpu', weights_only=True)
        if data['format'] != FORMAT:
            raise ValueError('Unsupported AlphaZero checkpoint format')
        model = PolicyValueNet(**data['config'])
        model.load_state_dict(data['weights'])
        model.eval()
        data['model_id'] = hashlib.sha256(content).hexdigest()[:12]
    except (OSError, KeyError, TypeError, RuntimeError, ValueError, EOFError, pickle.UnpicklingError) as error:
        raise ValueError(f'Cannot load AlphaZero checkpoint {path}: {error}') from error
    return model, data


def model_path(algorithm='alphazero'):
    if algorithm == 'alphazero_teacher':
        return Path(os.environ.get('CHESS_AZ_TEACHER_MODEL', str(DEFAULT_TEACHER_MODEL))).resolve()
    return Path(os.environ.get('CHESS_AZ_PLAIN_MODEL',
                              os.environ.get('CHESS_AZ_MODEL', str(DEFAULT_MODEL)))).resolve()
