from time import clock
from subprocess import call

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample

from spectrum import Spectrogram, Comparator, extract_mono, name_split


def file_open(filename):
    name, ext = name_split(filename)
    if ext != 'wav':
        call('ffmpeg -i {0} -vn -ac 1 {1}.wav'.format(filename, name), shell=True)
        filename = name + '.wav'
    rate, data = wavfile.read(filename)
    print("Rate:", rate)
    data = extract_mono(data)
    # sec1, sec2 = 0, 300
    # r1, r2 = 100, 150
    # if 'Y' in filename:
    #    return rate, np.concatenate((data[rate*sec1:rate*r1], data[rate*r2:rate*sec2]))
    return rate, data  # [rate*sec1:rate*sec2]


def main():
    zero_time = clock()
    x, y = (Spectrogram(file, file_open) for file in ('D:/Video/Spazz-6x24.wav', 'D:/Video/YP-1T-06x24.wav'))
    z = Comparator(x, y)
    print("Final path:", z.full_search)
    print("Total time:", clock()-zero_time)


if __name__ == '__main__':
    main()