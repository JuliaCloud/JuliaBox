#! /usr/bin/env python

from jbox_util import *
import errno

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

if __name__ == "__main__":
    JBoxContainer.backup_all()

