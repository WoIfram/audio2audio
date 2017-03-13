from subprocess import call
from os import remove, devnull, path
from collections import defaultdict
from time import clock

from config import Config
from spectrum import Spectrogram, Comparator
from grid_path import Path
from util import Subs, Timing, file_to_text


def delete_files(to_delete):
    for file in to_delete:
        remove(file)


def shift_subs(subs, sub_path):
    """Двигает сабы, в subs объект типа util.Subs, в sub_path типа grid_path.Path
    Предполагается, что в sub_path продолжительности участков указаны в сантисекундах."""
    # TODO: Нужна корректная работа для сабов, выходящих за рамки видео и более быстрая в общем случае.
    ss_to_event = defaultdict(list)
    for event in subs:
        ss_to_event[event.timing.begin_ss].append((event, 'b'))
        ss_to_event[event.timing.end_ss].append((event, 'e'))
    prev_x = -1
    for x, y in sub_path.on_path:
        for event, mark in ss_to_event[x]:
            if mark == 'b':
                event.timing.begin_ss = y
            if mark == 'e' and x != prev_x:
                event.timing.end_ss = y
        prev_x = x
    corrupted_events = []  # События, длительность которых была изменена в результате сдвига
    for event in subs:
        begin, end = event.timing.begin_str, event.timing.end_str
        event.timing.str_update()
        if len(event.timing) != len(Timing(begin, end)):
            corrupted_events.append(repr(event))
    print("Corrupted events: {}".format("\n"+"\n".join(corrupted_events) if corrupted_events else None))
    print("Successful shift!")


def main():
    """В режиме save_wav=True wav-файлы, генерируемые программой во время работы, не удаляются после окончания,
    а используются при повторных запусках в этом же режиме."""
    # inp = input("What files to use?\n")
    print("Processing...")
    dirname = path.dirname(__file__) + '/'
    # Subs.verbose = False  # Можно раскомментарить, чтобы библиотека util не предупреждала о наложениях событий и т.п.
    to_delete, final_path, begin_stamp = set(), None, clock()
    if Config.TEXT_FILE is None:
        media = Config.MEDIA
        if len(media) not in (0, 2):
            print("Error: 0 or 2 media files should be given")
        if len(media) == 2:
            spectrums = []
            for filename in media:
                if not path.isabs(filename):
                    filename = dirname + filename
                tmp = filename.split('.')
                name, ext = ".".join(tmp[:-1]), tmp[-1]
                wav_file = name + '_tmp{}Hz.wav'.format(Config.DEFAULT_HZ)
                if Config.REWRITE_WAV or not path.isfile(wav_file):
                    if path.isfile(wav_file):
                        remove(wav_file)
                    call('ffmpeg -i "{0}" -y -ac 1 -ar {1} {2}'.format(filename, Config.DEFAULT_HZ, wav_file), shell=True,
                         stderr=open(devnull, 'w'))  # Весь вывод FFmpeg идёт в devnull, дабы не засорять консоль
                to_delete.add(wav_file)
                spectrums.append(Spectrogram(wav_file))
            cmp = Comparator(spectrums[0], spectrums[1])
            final_path = cmp.full_search()
            f = open(Config.LOG_FILE, 'wb')
            f.write(str(final_path).encode('utf-8'))
            f.close()
            if not Config.SAVE_WAV:
                delete_files(to_delete)
    else:
        final_path = Path.parse(file_to_text(Config.TEXT_FILE))
    for name in Config.ASS_FILES:
        subs = Subs().parse(name)
        print("Shifting subs in {}".format(name))
        shift_subs(subs, final_path)
        subs.output(name[:-4]+'_shifted.ass', remove_garbage=False, default_styles=False, default_events='full')
    if not Config.ASS_FILES:
        print("No subtitles to shift.")
    print('Total time: {} sec'.format(clock()-begin_stamp))

if __name__ == '__main__':
    main()
