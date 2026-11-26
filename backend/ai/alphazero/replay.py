"""Retain decisive outcomes when recent self-play is dominated by draws."""
from collections import deque


class ReplayBuffer:
    def __init__(self, capacity, samples=()):
        # Half the slots retain win/loss examples. The rest retain draws and truncations.
        self.decisive = deque(maxlen=capacity // 2)
        self.other = deque(maxlen=capacity - capacity // 2)
        self.extend(samples)

    def extend(self, samples):
        for sample in samples:
            target = self.decisive if sample['value_known'] and sample['value'] != 0 else self.other
            target.append(sample)

    def __iter__(self):
        yield from self.decisive
        yield from self.other

    def __len__(self):
        return len(self.decisive) + len(self.other)
