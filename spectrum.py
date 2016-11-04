# Standard
from random import randrange
from time import clock
from subprocess import call
from os import remove, devnull

# Third-party
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from scipy.spatial.distance import cosine

# My modules
from path import Point, Path
from priority_queue import PriorityQueue
from grid_set import GridSet


def cos_sim(x, y):
    # Cosine similarity с учётом возможных нуль-векторов
    nonzero = x.any(), y.any()
    if nonzero[0] and nonzero[1]:
        return cosine(x, y)  # 1-cos(угла между векторами), т.е. значения бывают от 0 (на сонаправленных) до 2
    elif nonzero[0] or nonzero[1]:
        return 1  # Ноль считаем перпендикулярным всему
    return 0  # Между двумя нуль-векторами расстояние 0


def cos_log(x, y):
    """
    Стрёмное расстояние между двумя векторами, используемое в A* как веса ребёр.
    (Неравенству треугольника оно не удовлетворяет.)
    От него мы хотим выполнение следующих требований:
    1) На сонаправленных ненулевых векторах оно 0 (для дорожек, по-разному отнормированных по громкости)
    2) При равном ненулевом угле между векторами чем больше длины векторов, тем больше расстояние
    (случайные шумы на разных дорожках не должны сильно их разнести)
    3) 0 между двумя нуль-векторами
    4) Между нуль-вектором и не нуль-вектором чем длиннее последний, тем больше расстояние
    5) Расстояние растёт медленно с увеличением длины вектора, чтобы случайные всплески громкости не давали слишком
    большой вклад.
    """
    return cos_sim(x, y) * (np.log(1 + np.linalg.norm(x)) + np.log(1 + np.linalg.norm(y)))


def extract_mono(data):
    if len(data.shape) > 1:
        return np.transpose(data)[0]
    return data


def name_split(filename):
    tmp = filename.split('.')
    return ".".join(tmp[:-1]), tmp[-1]


class Spectrogram:
    BASE_TICK = 0.04  # sec
    MULT_BY = 128
    OVERLAP_DEGREE = 3
    MAXIMAL_WINDOW_SIZE = 10000

    def __init__(self, filename, func=(lambda i: wavfile.read(i))):
        self._filename, self._func = name_split(filename)[0], func
        self._rate, self._wav = func(filename)
        self._wav = extract_mono(self._wav)
        self._sample_tick = None
        self._spec = None
        self.calculate_spec()

    def __getitem__(self, item):
        return self._spec[item]

    def __len__(self):
        return len(self._spec)

    def calculate_spec(self):
        self._sample_tick = int(self._rate * self.MULT_BY * self.BASE_TICK)
        window_size = self._sample_tick * self.OVERLAP_DEGREE
        if window_size > self.MAXIMAL_WINDOW_SIZE:
            new_rate = self.MAXIMAL_WINDOW_SIZE * self._rate // (100 * window_size) * 100
            tmp_name = self._filename+'_tmp{0}Hz'.format(new_rate)
            call('ffmpeg -i {0}.wav -ac 1 -ar {1} {2}.wav'.format(self._filename, new_rate, tmp_name),
                 shell=True, stderr=open(devnull, 'w'))
            self._spec = Spectrogram(tmp_name+'.wav', self._func)._spec
            remove(tmp_name+'.wav')
            return
        overlap = self._sample_tick * (self.OVERLAP_DEGREE - 1)
        wav_reshape = (-len(self._wav))//self._sample_tick*(-self._sample_tick)+overlap
        new_wav = np.concatenate((self._wav, np.zeros(wav_reshape-len(self._wav))))
        spec = spectrogram(new_wav, nperseg=window_size, noverlap=overlap)[2]
        # chunk_size = len(spec)//self.MAXIMAL_SIZE + 1
        # chunk_number = len(spec)//chunk_size
        # self._spec = np.transpose(np.average(spec[:chunk_number*chunk_size]
        #                                      .reshape(chunk_number, chunk_size, spec.shape[1]), 1))
        self._spec = np.transpose(spec)

    @property
    def rand_vector(self):
        return self._spec[randrange(len(self._spec))]

    @property
    def shape(self):
        return self._spec.shape


class Comparator:
    DEBUG = True
    SAMPLE_SIZE = 1000
    RADIUS = 5

    def __init__(self, spec1, spec2):
        self._x, self._y = spec1, spec2
        self._goal, self._av_cost = None, None
        print("Spectrogram sizes are", spec1.shape, spec2.shape)

    @property
    def _a_star_search(self):
        first_stamp = prev_stamp = clock()
        front = PriorityQueue()  # В key хранятся координаты, в value - пара (цена, путь), в priority - цена+эвристика
        front.update(key=Point(0, 0), priority=0, cost=0, path=Path(), move=None)
        cycles, current, self._goal = 0, None, Point(len(self._x), len(self._y))
        self._av_cost = self._average_cost
        visited = GridSet(self._goal.x, self._goal.y)

        while not front.empty():
            current = front.pop()

            if self.DEBUG and clock() - prev_stamp > 10:
                print('Current: {0}; heap_size: {1}; cnt: {2}'.format(str(current), str(len(front)), str(cycles)))
                prev_stamp = clock()

            if current.key == self._goal:
                break

            for edge, vertex in self._options(current.key):
                if vertex not in visited:
                    new_cost = current.cost + self._cost(current.key, edge)
                    front.update(key=vertex, priority=(new_cost+self._heuristic(vertex)),
                                 cost=new_cost, path=current.path, move=edge)
            visited.add(current.key)
            cycles += 1

        if self.DEBUG:
            print("A* terminated in {0} cycles and {1} seconds.".format(cycles, clock()-first_stamp))
        return current.path

    @property
    def _average_cost(self):
        ans = sum(cos_log(self._x.rand_vector, self._y.rand_vector) for _ in range(self.SAMPLE_SIZE))/self.SAMPLE_SIZE
        if self.DEBUG:
            print('Av_cost={0}'.format(ans))
        return ans * 1.3

    def _cost(self, v, move):
        if move == '/':
            return cos_log(self._x[v.x], self._y[v.y])
        return self._av_cost

    def _heuristic(self, v):
        return abs(v.diff-self._goal.diff) * self._av_cost

    def _last_two_slice_search(self, draft_path):
        first_stamp = prev_stamp = clock()
        for spec in (self._x, self._y):
            spec.calculate_spec()
        curr, prev1, prev2 = {}, {}, {}
        prev1[Point(0, 0)] = (0., Path())
        current_slice = 1
        self._goal, self._av_cost = Point(len(self._x), len(self._y)), self._average_cost
        for point in draft_path.near_path(self.RADIUS):
            if point.slice > self._goal.slice:
                break
            if point.slice > current_slice:
                current_slice = point.slice
                curr, prev1, prev2 = {}, curr, prev1
            if 0 <= point.x <= self._goal.x and 0 <= point.y <= self._goal.y:
                best_cost, best_path = None, None
                for move, prev in self._options_back(point):
                    try:
                        cost, path = prev2[prev] if move == '/' else prev1[prev]
                        new_cost = cost + self._cost(prev, move)
                        if best_cost is None or best_cost > new_cost:
                            best_cost, best_path = new_cost, path.plus(move)
                    except KeyError:
                        continue
                curr[point] = (best_cost, best_path)
        return curr[self._goal][1]

    def _options(self, v):
        if v.x == self._goal.x:
            moves = '|'
        elif v.y == self._goal.y:
            moves = '-'
        else:
            moves = '|-/'
        return ((move, v + move) for move in moves)

    def _options_back(self, v):
        if v.x == 0:
            moves = '|'
        elif v.y == 0:
            moves = '-'
        else:
            moves = '|-/'
        return ((move, v - move) for move in moves)

    @property
    def full_search(self):
        draft_path = self._a_star_search
        Spectrogram.MULT_BY //= 2
        while Spectrogram.MULT_BY:
            print("Draft path={0}".format(draft_path))
            print("Multfactor={0}".format(Spectrogram.MULT_BY))
            draft_path = self._last_two_slice_search(draft_path * 2)
            Spectrogram.MULT_BY //= 2
        return draft_path
