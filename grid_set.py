from bisect import bisect
from itertools import chain, islice

# Obsolete module
class DisjointSegments:
    # Структура для хранения наборов целых точек на прямой, сильно группирующихся в отрезки
    # TODO: Возможно, стоит оптимизировать асимптотику с линейной до логарифмической с помощью interval tree
    def __init__(self):
        self._segments = []

    def __contains__(self, number):
        candidate = self[bisect(self._segments, (number+1,))-1]
        return candidate[0] <= number <= candidate[1]  # !

    def __getitem__(self, item):
        if item < 0 or item >= len(self):
            return 0.5, 0.5  # Говнокод, позволяющий получить False, а не исключение, в строках, помеченных # !
        return self._segments[item]

    def __len__(self):
        return len(self._segments)

    def __repr__(self):
        return 'DS{0}'.format(self._segments)

    def add(self, number):
        ind = bisect(self._segments, (number+1,))
        begin, left, right, end = ind, number, number, ind
        if number-1 == self[ind-1][1]:  # !
            begin, left = ind - 1, self[ind-1][0]
        if number+1 == self[ind][0]:  # !
            right, end = self[ind][1], ind + 1
        self._segments = list(chain(islice(self._segments, begin), [(left, right)], islice(self._segments, end, None)))


class GridSet:
    # Класс для хранения большого числа точек в прямоугольнике, сильно группирующихся вдоль диагоналей
    def __init__(self, width, height):
        self._width, self._height = width, height
        self._diag = [DisjointSegments() for _ in range(width+height+1)]

    def __contains__(self, point):
        return point.x in self._diag[point.y-point.x+self._width]

    def __repr__(self):
        return 'GS{0}'.format(list(filter(bool, map(len, self._diag))))

    def add(self, point):
        self._diag[point.y-point.x+self._width].add(point.x)
