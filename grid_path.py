import re


class Point:
    def __init__(self, x, y):
        self.x, self.y, self.diff, self.slice = x, y, x - y, x + y  # Всё целое

    def __add__(self, move):  # move бывает '|' - сдвиг на (0,1), '-' - сдвиг на (1,0) и '/' - сдвиг на (1,1)
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


class PathItem:
    def __init__(self, move, times=1):
        """Последовательжость одинаковых ходов вида |,-,/"""
        self.move, self.times = move, times

    def __mul__(self, other):
        return PathItem(self.move, self.times * other)  # Предполагается, что other целое

    def __repr__(self):
        return self.move + str(self.times)

    def copy(self):
        return PathItem(self.move, self.times)

    @staticmethod
    def parse(string):
        return PathItem(string[0], int(string[1:]))


class Path:
    # A compact structure for storing paths with large segments of equal elements
    def __init__(self, sequence=list()):
        self._sequence = sequence  # of PathItems

    def __len__(self):
        return len(self._sequence)

    def __lt__(self, other):
        """Нужно только чтобы был корректно определён min((cost1, path1), (cost2, path2)), когда cost1==cost2
        На деле большой роли не играет, поскольку cost1 редко равно cost2, но мы в принципе хотим выбирать пути
        с меньшим числом изломов, так что так и определяем."""
        return len(self) < len(other)

    def __mul__(self, other):
        assert type(other) is int and other > 0
        return Path([item * other for item in self._sequence])

    def __repr__(self):
        return " ".join(repr(item) for item in self._sequence)

    def append(self, move):
        if self._sequence and self._sequence[-1].move == move:
            self._sequence[-1].times += 1
        else:
            self._sequence.append(PathItem(move))
        return self

    def copy(self):
        return Path([item.copy() for item in self._sequence])

    def near_path(self, radius):
        """
        Генератор точек, отстоящих от пути по диагонали не больше, чем на радиус.
        """
        x, y = 0., 0.
        for item in self._sequence:
            dx, dy = {'|': (0, 1), '-': (1, 0), '/': (0.5, 0.5)}[item.move]
            for _ in range(item.times if item.move != '/' else item.times*2):
                x += dx
                y += dy
                for i in self._path_range(x, radius):
                    yield Point(int(x+i), int(y-i))

    @property
    def on_path(self):
        """
        Генератор координат точек, через которые проходит путь. Нужен для подвижки субтитров, поэтому из-за некоторых
        особенностей алгоритма можно пропустить все точки на вертикальных участках, кроме концов
        """
        yield 0, 0
        x, y = 0, 0
        for item in self._sequence:
            dx, dy = {'|': (0, item.times), '-': (1, 0), '/': (1, 1)}[item.move]
            for _ in range(1 if item.move == '|' else item.times):
                x += dx
                y += dy
                yield x, y

    @staticmethod
    def _path_range(x, radius):
        if int(x) == x:
            for i in range(-radius, radius+1):
                yield i
        else:
            for i in range(-radius, radius):
                yield i + .5

    @staticmethod
    def parse(string):
        if not re.match(r'(-|/|\|)\d+( (-|/|\|)\d+)*', string):
            raise ValueError('Incorrect path format')
        return Path([PathItem.parse(i) for i in string.split()])

    def plus(self, move):
        if move is None:
            return self
        return self.copy().append(move)
