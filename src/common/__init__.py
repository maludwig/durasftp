import hashlib
from os import scandir, remove
from shutil import rmtree


ONE_KB = 1024
ONE_MB = ONE_KB * 1024
ONE_GB = ONE_MB * 1024


def empty_dir(local_path):
    """
    Removes all children and descendants of a directory, leaving the directory itself intact
    """
    for entry in scandir(local_path):
        if entry.is_dir():
            rmtree(entry.path)
        else:
            remove(entry.path)


def generate_file_sha1(fetch_file_path, blocksize=2 ** 16):
    m = hashlib.sha1()
    with open(fetch_file_path, "rb") as f:
        while True:
            buf = f.read(blocksize)
            if not buf:
                break
            m.update(buf)
    return m.hexdigest()
