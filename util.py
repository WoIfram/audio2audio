"""Моя библиотечка для работы с сабами."""
import re
import os
from itertools import tee


def pairwise(iterable):
    """Из рецептов к itertools в оф. документации
    s -> (s0,s1), (s1,s2), (s2, s3), ..."""
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


class Timing:
    """Тайминг события: begin_str - момент появления на экране, end_str - момент исчезновения с экрана, (строки)
    begin_ss, end_ss - то же самое в сантисекундах,
    length - целое число, длительность в сантисекундах"""
    def __init__(self, begin_str, end_str):
        self.begin_str, self.end_str = begin_str, end_str  # 10-символьные строки типа 0:00:00.00
        self.begin_ss, self.end_ss = map(self.to_ss, (begin_str, end_str))  # В сотых секунды

    def __hash__(self):
        return hash((self.begin_ss, self.end_ss))

    def __iadd__(self, ss):
        """Сдвинуть тайминг на ss сантисекунд вперёд (для сдвига назад подставлять отрицательное).
        Возвращает исключение, если получился отрицательный тайминг."""
        self.begin_ss += ss
        self.end_ss += ss
        if self.begin_ss < 0:
            raise ValueError("Negative time stamp")
        self._str_update()
        return self

    def __imul__(self, koef):
        """Умножение конца и начала на одно и то же число number, фича для смены частоты кадров"""
        self.begin_ss, self.end_ss = (int(i*koef) for i in (self.begin_ss, self.end_ss))
        self._str_update()
        return self

    def __len__(self):
        return self.end_ss - self.begin_ss

    def __lt__(self, other):
        return (self.begin_ss, self.end_ss) < (other.begin_ss, other.end_ss)

    def __repr__(self):
        return self.begin_str + ',' + self.end_str

    @property
    def pad_view(self):
        tmp, ss = divmod(self.begin_ss, 100)
        m, s = divmod(tmp, 60)
        return "{m}:{s:0>2}.{ss:0>2},{ls}.{lss:0>2}".format(m=m, s=s, ss=ss, ls=len(self)//100, lss=len(self)%100)

    @staticmethod
    def to_ss(string):
        h, m, s = string.split(':')
        s, ss = s.split('.')
        return int(h)*360000+int(m)*6000+int(s)*100+int(ss)

    @staticmethod
    def to_string(ss):
        tmp, ss = divmod(ss, 100)
        tmp, s = divmod(tmp, 60)
        h, m = divmod(tmp, 60)
        return "{h}:{m:0>2}:{s:0>2}.{ss:0>2}".format(h=h, m=m, s=s, ss=ss)

    def _str_update(self):
        self.begin_str, self.end_str = map(self.to_string, (self.begin_ss, self.end_ss))


class Event:
    TEMPLATE = "Dialogue: {df.layer},{self.timing},{self.style},{actor}," + \
        "{df.margin_l},{df.margin_r},{df.margin_v},{df.effect},{self.text}"
    DEFAULT_EVENT = []
    (layer, margin_l, margin_r, margin_v), effect = '0'*4, ''

    def __init__(self, event_string):
        """Типичный event_string: '0,0:00:08.62,0:00:09.14,Default,,0,0,0,,This is a sentence, perhaps, with commas'"""
        self.layer, begin, end, self.style, self.actor, self.margin_l, \
            self.margin_r, self.margin_v, self.effect, self.text = event_string.split(',', 9)
        self.timing = Timing(begin, end)
        if str(self) != repr(self):
            print("Warning: non-default parameters in event '{}'".format(self.timing))

    def __eq__(self, other):
        return self.style == other.style and self.text == other.text

    def __iadd__(self, ss):
        self.timing += ss
        return self

    def __imul__(self, koef):
        self.timing *= koef
        return self

    def __lt__(self, other):
        return self.timing < other.timing

    @property
    def actorless_str(self):
        return self.TEMPLATE.format(self=self, df=Event, actor='')

    def __str__(self):
        return self.TEMPLATE.format(self=self, df=Event, actor=self.actor)

    def __repr__(self):
        return self.TEMPLATE.format(self=self, df=self, actor=self.actor)


class Style:
    TEMPLATE = "Style: {self.name},{df.fontname},{df.fontsize},{self.color},{df.tail}"
    fontname, fontsize, tail = "Arial", 68, "0,0,0,0,100,100,0,0,1,2.25,2.25,2,30,30,45,1"

    def __init__(self, style_string):
        self.name, self.fontname, self.fontsize, col1, col2, col3, col4, self.tail = style_string.split(',', 7)
        self.color = ','.join((col1, col2, col3, col4))
        if str(self) != repr(self):
            print("Warning: non-default parameters in style '{}'".format(self.name))

    def __eq__(self, other):
        return self.name == other.name and self.color == other.color

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.TEMPLATE.format(self=self, df=Style)

    def __repr__(self):
        return self.TEMPLATE.format(self=self, df=self)


def file_to_text(filename, encoding='utf-8'):
    f = open(filename, "rb")
    text = f.read().decode(encoding).replace('\r', '')
    f.close()
    return text


class Subs:
    ResX, ResY = 1920, 1080
    verbose = True

    def __init__(self):
        self.existing_styles = set()
        self.info = self.garbage = self.events = self.event_format = self.style_format = None
        self.styles = {}  # Name: Style object
        self.events = []

    def __getitem__(self, item):
        return self.events[item]

    def __iadd__(self, ss):
        for event in self.events:
            event += ss
        return self

    def __imul__(self, koef):
        for event in self.events:
            event *= koef
        return self

    def __iter__(self):
        for i in self.events:
            yield i

    def parse(self, filename):
        match = re.search(r'\[Script Info\](.*?)PlayResX: (\d+)\s+PlayResY: (\d+)(.*?)(\[Aegisub Project Garbage\].*?)?'
                          r'\[V4\+ Styles\](.*?)\[Events\](.*)', file_to_text(filename), re.DOTALL)
        if match is None:
            raise SyntaxError("Bad .ass file structure in {}, cannot process it.".format(filename))
        self.info, X, Y, _, self.garbage, styles, events = [match.group(i) for i in range(1, 8)]
        if self.verbose and int(X) != self.ResX or int(Y) != self.ResY:
            print('Warning: wrong resolution in file "{}".'.format(filename))
        m_styles = re.search(r'(Format: [a-zA-Z, ]*)\n(.*)', styles, re.DOTALL)
        if m_styles is None:
            raise SyntaxError("Bad styles structure in {}, cannot process it.".format(filename))
        self.style_format = m_styles.group(1)
        for line in m_styles.group(2).split('\n'):
            begin = 'Style: '
            if line[:len(begin)] == begin:
                new_style = Style(line[len(begin):])
                name = new_style.name
                if name in self.styles:
                    if self.verbose and self.styles[name] != new_style:
                        print("Style collision: {0}!\n{1}\n{2}\n\n"
                              .format(name, repr(self.styles[name]), repr(new_style)))
                else:
                    self.styles[name] = new_style
        m_events = re.search(r'(Format: [a-zA-Z, ]*)\n(.*)', events, re.DOTALL)
        if m_events is None:
            raise SyntaxError("Bad events structure in {}, cannot process it.".format(filename))
        self.event_format = m_events.group(1)
        for line in m_events.group(2).split("\n"):
            begin = 'Dialogue: '
            if line[:len(begin)] == begin:
                new_event = Event(line[len(begin):])
                self.events.append(new_event)
                self.existing_styles.add(new_event.style)
        return self

    def join_styles(self, default):
        """Default is a boolean variable which is True if we need to set the default parameters to styles
        like fontsize = 68"""
        output_styles = [(str if default else repr)(self.styles[i]) for i in self.existing_styles]
        return '{}\n'.format(self.style_format) + '\n'.join(sorted(output_styles))

    def join_events(self, default):
        """Default is a variable of values 'actorless', 'default', 'full'"""
        self.events.sort()
        for ev1, ev2 in pairwise(self.events):
            if self.verbose and ev1.timing.end_ss > ev2.timing.begin_ss:
                print("Warning: event collision:\n{0}\n{1}".format(ev1, ev2))
        func = {'actorless': (lambda i: i.actorless_str), 'default': str, 'full': repr}[default]
        return '{}\n'.format(self.event_format) + '\n'.join(func(i) for i in self.events)

    def output(self, filename, encoding='utf-8', **options):
        text = '[Script Info]{self.info}PlayResX: {self.ResX}\nPlayResY: {self.ResY}\n\n' \
               '{garbage}[V4+ Styles]\n{styles}\n\n[Events]\n{events}'\
                .format(self=self, garbage=('' if options['remove_garbage'] else self.garbage),
                        styles=self.join_styles(options['default_styles']),
                        events=self.join_events(options['default_events']))
        if 'unify' in options:
            text = text.replace('...', '…').replace(' - ', ' — ')
        if 'rusify' in options:
            text = text.replace('…?', '?..').replace('…!', '!..')
        if 'englify' in options:
            text = text.replace('?..', '…?').replace('!..', '…!')
        text = re.sub(r' +', ' ', text)
        f = open(filename, "wb")
        f.write(text.replace('\n', '\r\n').encode(encoding))
        f.close()


def merge(dir_name='merge', **options):
    subs = Subs()
    s, e = 'XX', 'XX'
    for filename in os.listdir(dir_name):
        if filename.split('.')[-1] == 'ass':
            print(filename)
            match = re.search(r'(s|S)(\d{1,2})(e|E)(\d{1,2})', filename)
            if match and s == 'XX':
                s, e = map(lambda i: match.group(i).zfill(2), (2, 4))
            subs.parse(dir_name+'/'+filename)
    subs.output(dir_name+'/Sub_MLPFiM_S{0}E{1}_English.ass'.format(s, e), **options)


def process(**options):
    """Process all .ass files in the directory"""
    dir_name = os.path.dirname(os.path.realpath(__file__))
    for filename in os.listdir(dir_name):
        if filename.split('.')[-1] == 'ass':
            print(filename)
            Subs().parse(filename).output(filename[:-4]+'_copy.ass', **options)


if __name__ == '__main__':
    merge(remove_garbage=True, default_styles=True, default_events='actorless', unify=None, englify=None)
