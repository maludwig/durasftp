import os

from os.path import dirname, isdir, join

REPO_ROOT = dirname(dirname(__file__))

if not isdir(join(REPO_ROOT, ".git")):
    raise Exception(
        "Bad repo root mapping, could not find .git under: {}".format(REPO_ROOT)
    )

SRC_ROOT = os.path.join(REPO_ROOT, "src")
TEST_ROOT = os.path.join(SRC_ROOT, "test")
