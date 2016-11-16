# Standard
from random import randrange
import random
from time import clock

# Third-party
import numpy as np
from scipy.io import wavfile
from scipy.signal import spectrogram
from scipy.spatial.distance import cosine
try:
    from PIL import Image
except ImportError:
    print('Warning: pillow module not found, cannot use Comparator.image()')
    pass

# My modules
from config import Config
from grid_path import Point, Path
# from priority_queue import PriorityQueue
# from grid_set import GridSet


random.seed = 31168


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


class Spectrogram:
    MULT_BY = 1  # Текущая точность вычислений, измеряется в Config.PRECISION-ах

    def __init__(self, filename):
        self._filename = filename
        self._rate, self._wav = self.file_open(filename)
        self._samples_in_tick = int(Config.BASE_TICK * self._rate / 100)
        self._base_spec = self.calculate_base_spec()
        self._curr_spec = None

    def __getitem__(self, item):
        return self._curr_spec[item]

    def __len__(self):
        return len(self._curr_spec)

    @property
    def base_len(self):
        return len(self._base_spec)

    def calculate_base_spec(self):
        window_size = self._samples_in_tick * Config.B_OVERLAP_DEGREE
        overlap = self._samples_in_tick * (Config.B_OVERLAP_DEGREE - 1)
        wav_reshape = (-len(self._wav))//self._samples_in_tick*(-self._samples_in_tick)+overlap
        new_wav = np.concatenate((self._wav, np.zeros(wav_reshape-len(self._wav))))
        spec = np.transpose(spectrogram(new_wav, nperseg=window_size, noverlap=overlap)[2])
        # chunk_size = len(spec)//self.MAXIMAL_SIZE + 1
        # chunk_number = len(spec)//chunk_size
        # self._spec = np.transpose(np.average(spec[:chunk_number*chunk_size]
        #                                      .reshape(chunk_number, chunk_size, spec.shape[1]), 1))
        print("Spectrogram size is", spec.shape)
        return spec

    def calculate_curr_spec(self):
        tick = Config.PRECISION * self.MULT_BY  # in base_ticks
        ticks, freq = self._base_spec.shape
        window_number = -((-ticks)//tick)
        spec_reshape = (window_number + Config.C_OVERLAP_DEGREE - 1) * tick
        new_spec = np.concatenate((self._base_spec, np.zeros((spec_reshape-ticks, freq))))
        self._curr_spec = np.array([np.average(new_spec[i*tick:(i+Config.C_OVERLAP_DEGREE)*tick], axis=0) for i in range(window_number)])

    @staticmethod
    def file_open(filename):
        rate, data = wavfile.read(filename)
        print("Rate of {}:".format(filename), rate)
        data = extract_mono(data)
        """
        sec1, sec2 = 0, 300
        r1, r2 = 20, 270
        R1, R2 = 180, 180
        if 'Y' in filename:
           return rate, np.concatenate((data[rate*sec1:rate*r1], data[rate*r2:rate*sec2]))
        else:
            return rate, np.concatenate((data[rate*sec1:rate*R1], data[rate*R2:rate*sec2]))
        """
        return rate, data

    def rand_vector(self):
        return self._curr_spec[randrange(len(self._curr_spec))]

    @property
    def shape(self):
        return self._curr_spec.shape


class Comparator:
    def __init__(self, spec1, spec2):
        self._x, self._y = spec1, spec2
        self._goal, self._av_cost = None, None

    """
    def _a_star_search(self):
        first_stamp = prev_stamp = clock()
        front = PriorityQueue()  # В key хранятся координаты, в value - пара (цена, путь), в priority - цена+эвристика
        front.update(key=Point(0, 0), priority=0, cost=0, path=Path(), move=None)
        cycles, current, self._goal = 0, None, Point(len(self._x), len(self._y))
        self._av_cost = self._average_cost()
        visited = GridSet(self._goal.x, self._goal.y)

        while not front.empty():
            current = front.pop()

            if clock() - prev_stamp > 10:
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

        print("A* terminated in {0} cycles and {1} seconds.".format(cycles, clock()-first_stamp))
        return current.path
    """

    def _average_cost(self):
        ans = sum(cos_log(self._x.rand_vector(), self._y.rand_vector()) for _ in range(Config.SAMPLE_SIZE))/Config.SAMPLE_SIZE
        print('Av_cost={0}'.format(ans))
        return ans

    def _cost(self, v, move):
        if move == '/':
            return cos_log(self._x[v.x], self._y[v.y])
        return self._av_cost * Config.NONDIAGKOEF

    """
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
        for point in draft_path.near_path(Config.RADIUS):
            if clock() - prev_stamp > 10:
                prev_stamp = clock()
                print(point)
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
        print("Time for {0}-prec search: {1}".format(Config.BASE_TICK*Spectrogram.MULT_BY, clock()-first_stamp))
        return curr[self._goal][1]
    """

    def _penalty_search(self, draft_path):
        first_stamp = prev_stamp = clock()
        curr, prev1, prev2 = {}, {}, {}
        prev1[Point(0, 0)] = ((0., Path()), (0., Path()))
        current_slice = 1
        self._goal, self._av_cost = Point(len(self._x), len(self._y)), self._average_cost()
        infinity = self._av_cost * max(Config.PENALTY, 1000) * self._goal.x * self._goal.y
        for point in draft_path.near_path(Config.RADIUS):
            if clock() - prev_stamp > 10:
                prev_stamp = clock()
                print(point)
            if point.slice > self._goal.slice:
                break
            if point.slice > current_slice:
                current_slice = point.slice
                curr, prev1, prev2 = {}, curr, prev1
            if 0 <= point.x <= self._goal.x and 0 <= point.y <= self._goal.y:
                best_diag_cost, best_diag_path, best_horver_cost, best_horver_path = infinity, None, infinity, None
                for move, prev in self._options_back(point):
                    try:
                        if move == '/':
                            cost, path = min(prev2[prev][0], self.add_penalty(prev2[prev][1]))
                            new_cost = cost + self._cost(prev, move)
                            if best_diag_cost > new_cost:
                                best_diag_cost, best_diag_path = new_cost, path.plus(move)
                        else:
                            cost, path = min(prev1[prev][1], self.add_penalty(prev1[prev][0]))
                            new_cost = cost + self._cost(prev, move)
                            if best_horver_cost > new_cost:
                                best_horver_cost, best_horver_path = new_cost, path.plus(move)
                    except KeyError:
                        pass

                curr[point] = ((best_diag_cost, best_diag_path), (best_horver_cost, best_horver_path))
        print("Time for penalty search (precision {0} ss): {1}".format(Config.BASE_TICK * Config.PRECISION *
                                                                       Spectrogram.MULT_BY, clock()-first_stamp))
        ans = min(curr[self._goal])[1]
        print("Draft path: {}".format(ans))
        return ans

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

    def full_search(self):
        min_len = min(self._x.base_len, self._y.base_len)
        Spectrogram.MULT_BY = 2**int(np.log(min_len/Config.PRECISION)/np.log(2))
        draft_path = None
        while True:
            for spec in (self._x, self._y):
                spec.calculate_curr_spec()
            if draft_path is None:
                draft_path = Path.parse('-{} |{}'.format(len(self._x), len(self._y)))
            print("Multfactor={0}".format(Spectrogram.MULT_BY))
            draft_path = self._penalty_search(draft_path)
            Spectrogram.MULT_BY //= 2
            if Spectrogram.MULT_BY == 0:
                break
            else:
                draft_path *= 2
        return draft_path * Config.PRECISION

    @staticmethod
    def add_penalty(pair):
        return pair[0] + Config.PENALTY, pair[1]

    def image(self, filename):
        self._av_cost = self._average_cost()
        visual = np.zeros((len(self._x), len(self._y)))
        for i in range(len(self._x)):
            for j in range(len(self._y)):
                visual[i][j] = int(min(self._cost(Point(i, j), '/')/(2*self._av_cost), 1)*255)
            print("{0}/{1}".format(i, len(self._x)))
        print("Visual constructed!")
        result = Image.fromarray(visual.astype(np.uint8))
        Config.VISUAL = visual
        try:
            result.save(filename)
        except IOError:
            print("Cannot save image")
