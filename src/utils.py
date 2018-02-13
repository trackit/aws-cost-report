import csv
import os

def rows_folder(dirpath):
    for filename in os.listdir(dirpath):
        filepath = os.path.join(dirpath, filename)
        with open(filepath) as f:
            for row in rows(f):
                yield row

def rows(csvfile):
    reader = csv.DictReader(csvfile)
    for row in reader:
        yield row

class csv_folder:
    """csv_folder is to be used in conjunction with the 'with' statement. It is
    an iterator over all the CSV records of all files within a folder."""
    def __init__(self, dirpath, readerclass=csv.DictReader):
        self._dirpath = dirpath
        self._filepaths = (
            os.path.join(self._dirpath, filename)
            for filename in os.listdir(self._dirpath)
            if filename.endswith('.csv')
        )
        self._reader = None
        self._handle = None
        self._readerclass = readerclass

    def __enter__(self):
        return self

    def __iter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self._close()

    def __next__(self):
        if self._reader is None:
            self._open_next()
        try:
            return next(self._reader)
        except StopIteration:
            self._close()
            return self.__next__()

    def _open_next(self):
        filepath = next(self._filepaths)
        self._handle = open(filepath, 'rt')
        self._reader = self._readerclass(self._handle)

    def _close(self):
        if self._handle is not None:
            self._handle.close()
            self._handle = None
            self._reader = None
