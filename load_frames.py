from os import listdir
from os.path import isfile, join



def load_frame_from_file(filename):
    with open(filename, 'r') as fd:
        return fd.read()


def load_multiple_frames(dirnames):
    return [
        load_frame_from_file(join(dirnames, file))
        for file in listdir(dirnames)
        if isfile(join(dirnames, file))
    ]
