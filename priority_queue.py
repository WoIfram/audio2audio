class QueueElement:
    # Вспомогательный класс для хранения элементов PriorityQueue
    def __init__(self, key, priority, cost, path):
        """
        key : Параметр, по которому элемент доступен из PriorityQueue
        priority : Из PriorityQueue доступен элемент с наименьшим значением этого параметра
        heap_index : Индекс элемента в массиве, содержащем кучу в PriorityQueue
        """
        self.key, self.priority, self.cost, self.path, self.heap_index = key, priority, cost, path, None

    def __lt__(self, other):
        # Один элемент меньше другого <=> его priority меньше.
        return self.priority < other.priority

    def __repr__(self):
        return "'key={0}, priority={1}, cost={2}, path={3}'".format(self.key, int(self.priority),
                                                                    int(self.cost), self.path)


class PriorityQueue:
    # Очередь с приоритетом в виде бинарной кучи с хэш-таблицей
    def __init__(self):
        self._heap = []  # Куча QueueElement'ов, сверху минимальный
        self._hash_table = {}  # Ассоциативный массив {key : элемент кучи с таким ключом}

    def __contains__(self, key):
        return key in self._hash_table

    def __getitem__(self, key):
        return self._hash_table[key]

    def __iter__(self):
        return self._heap.__iter__()

    def __setitem__(self, key, value):
        self._hash_table[key] = value

    def __len__(self):
        return len(self._heap)

    def empty(self):
        return len(self) == 0

    def _heap_up(self, item, curr):
        """
        Поднять элемент item с индексом в куче curr наверх, при условии, что все свойства кучи выполняются,
        кроме, быть может, item может быть меньше своего родителя.
        """
        while curr:
            parent = (curr-1) >> 1
            if item < self._heap[parent]:
                self._heap[curr] = self._heap[parent]
                self._heap[curr].heap_index = curr
                curr = parent
            else:
                break
        item.heap_index = curr
        self._heap[curr] = item

    def _heap_down(self):
        """
        Опустить верхний элемент кучи вниз при условии, что все свойства кучи выполняются, кроме, быть может,
        верхний элемент кучи больше своих детей.
        """
        curr = 0
        item = self._heap[0]
        while True:
            left_child = self._heap[2*curr+1] if 2*curr+1 < len(self) else None
            right_child = self._heap[2*curr+2] if 2*curr+2 < len(self) else None
            if left_child is None:
                break
            else:
                new_curr, small_child = (2*curr+1, left_child) if (right_child is None) or (left_child < right_child)\
                    else (2*curr+2, right_child)
                if small_child < item:
                    self._heap[curr] = small_child
                    self._heap[curr].heap_index = curr
                    curr = new_curr
                else:
                    break
        item.heap_index = curr
        self._heap[curr] = item

    def pop(self):
        # Удалить элемент с наименьшим приоритетом и вернуть его
        top = self._heap[0]
        if len(self) > 1:
            self._heap[0] = self._heap.pop()
            self._heap_down()
        else:
            self._heap.pop()
        self._hash_table.pop(top.key)
        return top

    def update(self, key, priority, cost, path, move):
        """
        Вставка нового элемента в очередь или уменьшение ключа у старого, в зависимости от наличия ключа в очереди.
        Если поданное значение priority не меньше старого, update ничего не делает. В противном случае обновляется
        ещё и value.
        """
        if key in self:
            item = self[key]
            if priority < item.priority:
                item.priority, item.cost, item.path = priority, cost, path.plus(move)
                # Строка, ради которой хранится heap_index и вообще пишется этот велосипед:
                self._heap_up(item, item.heap_index)
        else:
            item = QueueElement(key, priority, cost, path.plus(move))
            self[key] = item
            self._heap.append(item)
            self._heap_up(item, len(self)-1)
