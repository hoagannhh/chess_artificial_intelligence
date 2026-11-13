"""Per-side countdown using the backend's monotonic clock."""
from time import monotonic

CLOCK_MINUTES = (0, 5, 10, 15)


def side_name(color):
    return 'white' if color else 'black'


class ChessClock:
    def __init__(self, minutes):
        self.minutes = minutes
        self.balances = dict.fromkeys(('white', 'black'), minutes * 60_000)
        self.history = []
        self.flagged = None
        self.started = monotonic()

    def remaining(self, color):
        balances = self.balances.copy()
        if self.started is not None:
            side = side_name(color)
            elapsed = int((monotonic() - self.started) * 1000)
            balances[side] = max(0, balances[side] - elapsed)
        return balances

    def flag_if_expired(self, color):
        if self.started is None:
            return False
        balances = self.remaining(color)
        if balances[side_name(color)] > 0:
            return False
        self.balances = balances
        self.flagged = color
        self.started = None
        return True

    def complete_turn(self, color):
        balances = self.remaining(color)
        if balances[side_name(color)] == 0:
            self.flag_if_expired(color)
            return False
        self.history.append(self.balances.copy())
        self.balances = balances
        self.started = monotonic()
        return True

    def stop(self, color):
        self.balances = self.remaining(color)
        self.started = None

    def resume(self):
        self.started = monotonic()

    def undo_move(self):
        self.balances = self.history.pop()
        self.flagged = None
        self.resume()

    def save_data(self, color):
        return {'minutes': self.minutes, 'remaining_ms': self.remaining(color),
                'history': self.history, 'flagged': self.flagged}

    @classmethod
    def from_save(cls, data, plies, turn, finished):
        if not isinstance(data, dict):
            raise ValueError('Invalid saved clock')
        minutes = data.get('minutes')
        if type(minutes) is not int or minutes not in CLOCK_MINUTES[1:]:
            raise ValueError('Invalid saved time control')
        clock = cls(minutes)

        def valid_balances(balances):
            return (isinstance(balances, dict) and set(balances) == {'white', 'black'}
                    and all(type(ms) is int and 0 <= ms <= minutes * 60_000 for ms in balances.values()))

        remaining = data.get('remaining_ms')
        history = data.get('history')
        flagged = data.get('flagged')
        if not valid_balances(remaining) or not isinstance(history, list) or len(history) != plies:
            raise ValueError('Invalid saved clock balances')
        if not all(valid_balances(balances) for balances in history):
            raise ValueError('Invalid saved clock history')
        if flagged is not None and (type(flagged) is not bool or flagged != turn
                                    or remaining[side_name(turn)] != 0 or finished):
            raise ValueError('Invalid saved timeout')
        clock.balances = remaining
        clock.history = history
        clock.flagged = flagged
        if finished or flagged is not None:
            clock.started = None
        return clock
