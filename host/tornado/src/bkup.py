#! /usr/bin/env python

from jdockutil import *
import errno

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

if __name__ == "__main__":
    JDockContainer.backup_all()

