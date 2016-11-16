class Config:
    MEDIA = ['D:/Video/YP-1TMP-EQGLOE.mkv', 'D:/Video/YP-1S-EQGLOE.mkv']  # Два исходных видео для обработки
    # если путь уже подсчитан, и надо только подвинуть сабы, оставить этот список пустым
    LOG_FILE = 'log.out'  # файл, в который выводится путь
    TEXT_FILE = None if MEDIA else LOG_FILE   # Вместо указания видео можно взять подсчитанный путь из текстового файла
    ASS_FILES = ['Sub_MLPEqG_LegendOfEverfree_Torrent_English.ass', 'Sub_MLPEqG_LegendOfEverfree_Torrent_Russian.ass']  # Список всех сабов, которые нужно подвинуть
    # TODO: Сделать возможность одновременно двигать и сливать несколько сабов воедино
    REWRITE_WAV = False  # Переписать имеющиеся временные файлы в директории
    SAVE_WAV = True  # Сохранить временные файлы, имеет смысл только если при следующем запуске REWRITE_WAV = False
    DEFAULT_HZ = 4000  # Частота, в которой вынимаются звуковые файлы из видео
    BASE_TICK = 1.  # Размер минимальной единицы, по которой строится спектрограмма, в сантисекундах
    PRECISION = 2   # Точность, с которой нужно прокладывать путь в графе, в BASE_TICK'ах
    # Каждое следующее окно перескается с предыдущим по доле 1-1/OVERLAP_DEGREE
    B_OVERLAP_DEGREE = 3   # при построении спектрограммы по сигналу
    C_OVERLAP_DEGREE = 3   # при взятии среднего по уже полученной спектрограмме
    SAMPLE_SIZE = 3000  # Размер выборки при подсчёте среднего расстояния между векторами
    RADIUS = 6  # В какой окрестности нужно искать путь
    PENALTY = 15  # Штраф за переход с диагонального на вертикальное и наоборот, выраженный в средних расстояниях
    NONDIAGKOEF = 1.3  # Длина любого вертикального или горизонтального ребра в средних расстояниях
    VISUAL = None  # Сохранённая копия картинки в виде numpy-массива, можно использовать из питон-консоли