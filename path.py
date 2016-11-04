from collections import Counter


class Point:
    def __init__(self, x, y):
        self.x, self.y, self.diff = x, y, x - y

    def __add__(self, move):
        x = self.x + (0 if move == '|' else 1)
        y = self.y + (0 if move == '-' else 1)
        return Point(x, y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def __sub__(self, move):
        x = self.x - (0 if move == '|' else 1)
        y = self.y - (0 if move == '-' else 1)
        return Point(x, y)

    def __repr__(self):
        return 'p{0}'.format((self.x, self.y))

    @property
    def slice(self):
        return self.x + self.y


class PathItem:
    def __init__(self, move, times=1):
        self.move, self.times = move, times

    def __mul__(self, other):
        return PathItem(self.move, self.times * other)

    def __repr__(self):
        return self.move + str(self.times)

    def copy(self):
        return PathItem(self.move, self.times)


class Path:
    # A compact structure for storing paths with large segments of equal elements
    def __init__(self, sequence=list()):
        self._sequence = sequence  # of PathItems

    def __mul__(self, other):
        assert type(other) == int and other > 0
        return Path([item * other for item in self._sequence])

    def __repr__(self):
        return " ".join(str(item) for item in self._sequence)

    def _add(self, item):
        self._sequence.append(item)

    def append(self, move):
        if self._sequence and self._sequence[-1].move == move:
            self._sequence[-1].times += 1
        else:
            self._sequence.append(PathItem(move))
        return self

    def copy(self):
        return Path([item.copy() for item in self._sequence])

    def plus(self, move):
        if move is None:
            return self
        return self.copy().append(move)

    @staticmethod
    def _path_range(x, radius):
        if int(x) == x:
            for i in range(-radius, radius+1):
                yield i
        else:
            for i in range(-radius, radius):
                yield i + .5

    @property
    def last_move(self):
        return self._sequence[-1].move if self._sequence else None

    def near_path(self, radius):
        x, y = 0., 0.
        for item in self._sequence:
            dx, dy = {'|': (0, 1), '-': (1, 0), '/': (0.5, 0.5)}[item.move]
            for _ in range(item.times if item.move != '/' else item.times*2):
                x += dx
                y += dy
                for i in self._path_range(x, radius):
                    yield Point(int(x+i), int(y-i))
