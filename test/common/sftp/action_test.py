#!/usr/bin/env python

import unittest
from os import makedirs
from os.path import dirname

from durasftp.common.log import get_logger
from durasftp.common.sftp.action import SFTPAction
from durasftp.common.sftp.action_codes import SFTPActionCodes
from test.common.config import SFTP_BASE
from test.common.sftp.mirrorer_test import TestMirrorerBase

"""
These tests require a running local SFTP server, configured in src.test.common.config
  The unit tests expect to be able to write directly to the test directories.
  This should be fully automated by restart_container()

  To run one by hand with the Docker CLI:
    Run an SFTP server
      - on port 2022
      - mounting the home directory to /Users/mitchell.ludwig/dev/sftping/src/test/_sftp/
      - Username: foo
      - Password: pass123

    Command:
        docker run -p 2022:22 -d --name test_sftp --rm -v /Users/mitchell.ludwig/dev/sftping/src/test/_sftp/:/home atmoz/sftp foo:pass123:::
"""

ONE_KB = 1024
ONE_MB = ONE_KB * 1024
ONE_GB = ONE_MB * 1024

logger = get_logger(__name__)

MAX_ATTEMPTS = 3


def make_test_file(remote_path, content=b"Hello world", iterations=1):
    full_path = SFTP_BASE + remote_path
    parent_dir_path = dirname(full_path)
    makedirs(parent_dir_path, exist_ok=True)
    with open(full_path, "wb") as temp_file:
        for i in range(iterations):
            temp_file.write(content)
    return full_path


def make_test_dir(remote_path):
    full_path = SFTP_BASE + remote_path
    makedirs(full_path, exist_ok=True)
    return full_path


class TestSFTPAction(TestMirrorerBase):
    def test_stat_automatically_populates(self):
        remote_path = "/temp.txt"
        action = SFTPAction(self.mirrorer, SFTPActionCodes.PUT, remote_path)
        self.assertIsNone(action.remote_entry)
        self.assertFalse(action.remote_exists)
        self.assertFalse(action.remote_is_dir)
        self.assertFalse(action.remote_is_file)
        make_test_file(remote_path)
        action = SFTPAction(self.mirrorer, SFTPActionCodes.PUT, remote_path)
        self.assertIsNone(action.remote_entry)
        self.assertFalse(action.remote_exists)
        self.assertFalse(action.remote_is_dir)
        self.assertFalse(action.remote_is_file)

    def test_action_callbacks(self):
        actions = []
        new_files = []

        def counter(action):
            actions.append(action)
            if action.action_code == SFTPActionCodes.GET:
                new_files.append(action.remote_path)

        remote_file_path = "/temp.txt"
        remote_dir_path = "/one/two"
        remote_second_file_path = "/second.txt"
        self.make_remote_content(["/temp.txt", "/one/two/", "/second.txt"])

        self.mirrorer.load_stat_trees()

        remote_entry = self.mirrorer.remote_attr_tree[remote_file_path]
        action = SFTPAction(
            self.mirrorer,
            SFTPActionCodes.GET,
            remote_file_path,
            local_entry=None,
            remote_entry=remote_entry,
        )
        action.run(callback=counter)
        self.assert_local_has_file(remote_file_path)
        self.assertEqual([action], actions)

        remote_entry = self.mirrorer.remote_attr_tree[remote_dir_path]
        action = SFTPAction(
            self.mirrorer,
            SFTPActionCodes.LMKDIR,
            remote_dir_path,
            local_entry=None,
            remote_entry=remote_entry,
        )
        action.run(callback=counter)
        self.assert_local_has_dir(remote_dir_path)
        self.assertEqual(2, len(actions))


if __name__ == "__main__":
    unittest.main()
