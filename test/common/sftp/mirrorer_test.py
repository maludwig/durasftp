import socket
import unittest
from os import makedirs, stat
from os.path import isfile, isdir, exists, dirname
from stat import S_ISDIR, S_ISREG

from paramiko import SSHException
from pysftp import ConnectionException

from durasftp.common import empty_dir, generate_file_sha1
from durasftp.common.log import get_logger
from durasftp.common.sftp.mirrorer import Mirrorer
from durasftp.config import REPO_ROOT
from test.common.config import (
    LOCAL_BASE,
    SFTP_HOST,
    SFTP_BASE,
    SFTP_PASS,
    SFTP_PORT,
    SFTP_USER,
)
from test.common.sftp.container import get_container

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

logger = get_logger(__name__)

MAX_ATTEMPTS = 3


def paths_from_remote(remote_path):
    if remote_path[-1] == "/":
        remote_path = remote_path[:-1]
    local_path = LOCAL_BASE + remote_path
    sftp_path = SFTP_BASE + remote_path
    return remote_path, local_path, sftp_path


class TestMirrorerBase(unittest.TestCase):
    def assert_local_missing(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertFalse(exists(local_path))

    def assert_local_has_file(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertTrue(isfile(local_path))

    def assert_local_has_dir(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertTrue(isdir(local_path))

    def assert_remote_missing(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertFalse(exists(sftp_path))

    def assert_remote_has_file(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertTrue(isfile(sftp_path))

    def assert_remote_has_dir(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        self.assertTrue(isdir(sftp_path))

    def assert_files_match(self, remote_path):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        local_stat = stat(local_path)
        sftp_stat = stat(local_path)
        self.assertEqual(S_ISDIR(local_stat.st_mode), S_ISDIR(sftp_stat.st_mode))
        self.assertEqual(S_ISREG(local_stat.st_mode), S_ISREG(sftp_stat.st_mode))
        if S_ISREG(local_stat.st_mode):
            self.assertEqual(local_stat.st_size, sftp_stat.st_size)
            local_modification_timestamp = int(local_stat.st_mtime)
            remote_modification_timestamp = int(sftp_stat.st_mtime)
            self.assertEqual(
                local_modification_timestamp, remote_modification_timestamp
            )
            self.assertEqual(
                generate_file_sha1(local_path), generate_file_sha1(sftp_path)
            )

    def make_local_test_file(
        self, remote_path, content=b"Hello world", iterations=1, suppress_check=False
    ):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        parent_dir_path = dirname(local_path)
        makedirs(parent_dir_path, exist_ok=True)
        with open(local_path, "wb") as temp_file:
            for i in range(iterations):
                temp_file.write(content)
        if not suppress_check:
            for content_path in self.entry_with_parents(remote_path):
                self.ensure_local_path_is_visible(content_path)
        return remote_path, local_path, sftp_path

    def make_remote_test_file(
        self, remote_path, content=b"Hello world", iterations=1, suppress_check=False
    ):
        remote_path, local_path, sftp_path = paths_from_remote(remote_path)
        parent_dir_path = dirname(sftp_path)
        makedirs(parent_dir_path, exist_ok=True)
        with open(sftp_path, "wb") as temp_file:
            for i in range(iterations):
                temp_file.write(content)
        if not suppress_check:
            for content_path in self.entry_with_parents(remote_path):
                self.ensure_remote_path_is_visible(content_path)
        return remote_path, local_path, sftp_path

    def make_local_content(self, remote_paths):
        return_list = []
        for content_path in remote_paths:
            remote_path, local_path, sftp_path = paths_from_remote(content_path)
            return_list.append((remote_path, local_path, sftp_path))
            if content_path[-1] == "/":
                makedirs(local_path, exist_ok=True)
            else:
                self.make_local_test_file(remote_path, suppress_check=True)

        for content_path in remote_paths:
            self.ensure_local_path_is_visible(content_path)
        return return_list

    def make_remote_content(self, remote_paths):
        return_list = []
        for content_path in remote_paths:
            remote_path, local_path, sftp_path = paths_from_remote(content_path)
            return_list.append((remote_path, local_path, sftp_path))
            if content_path[-1] == "/":
                makedirs(sftp_path, exist_ok=True)
            else:
                self.make_remote_test_file(remote_path, suppress_check=True)

        all_remote_paths = set()
        for content_path in remote_paths:
            all_remote_paths = all_remote_paths.union(
                self.entry_with_parents(content_path)
            )
        for content_path in all_remote_paths:
            self.ensure_remote_path_is_visible(content_path)
        return return_list

    def entry_with_parents(self, content_path):
        all_content_paths = [content_path]
        current_path = content_path
        while current_path != "/":
            if current_path[-1] == "/":
                current_path = dirname(current_path[:-1])
            else:
                current_path = dirname(current_path)
            if current_path != "/":
                current_path += "/"
            all_content_paths.append(current_path)
        all_content_paths.sort()
        return all_content_paths

    def ensure_remote_path_is_visible(self, content_path):
        # Sometimes it can take a fraction of a moment to create things,
        # this ensures that all entities exist in the cache of the
        # SFTP server
        # This only saves from an exception once in every ~20 runs, so
        # disable it at your peril.
        logger.info("Checking on remote: {}".format(content_path))
        if content_path == "/":
            return True
        for x in range(MAX_ATTEMPTS):
            try:
                if content_path[-1] == "/":
                    self.mirrorer.conn.listdir_attr(content_path[:-1])
                else:
                    self.mirrorer.conn.stat(content_path)
                break
            except FileNotFoundError:
                if x == MAX_ATTEMPTS - 1:
                    raise Exception(
                        "Reached max attempts of {} for path {}".format(
                            MAX_ATTEMPTS, content_path
                        )
                    )

    def ensure_local_path_is_visible(self, content_path):
        # Sometimes it can take a fraction of a moment to create things,
        # this ensures that all entities exist in the cache of the
        # local computer
        # This only saves from an exception once in every ~80 runs, so
        # disable it at your peril.
        logger.info("Checking on local: {}".format(content_path))
        if content_path == "/":
            return True
        remote_path, local_path, sftp_path = paths_from_remote(content_path)
        for x in range(MAX_ATTEMPTS):
            try:
                if content_path[-1] == "/":
                    stat(local_path)
                else:
                    stat(local_path)
                break
            except FileNotFoundError:
                if x == MAX_ATTEMPTS - 1:
                    raise Exception(
                        "Reached max attempts of {} for path {}".format(
                            MAX_ATTEMPTS, content_path
                        )
                    )

    def expect_sftp_failure(self, fn):
        try:
            fn()
            self.fail("Mirror did not except when the server died")
        except OSError as ex:
            self.assertEqual("Socket is closed", str(ex))
            self.mirrorer.conn.close()
        except (SSHException, ConnectionException, EOFError, socket.timeout):
            self.mirrorer.conn.close()

    @classmethod
    def setUpClass(cls):
        # restart_container()
        get_container()
        makedirs(LOCAL_BASE, exist_ok=True)
        makedirs(SFTP_BASE, exist_ok=True)

    def setUp(self):
        # Dangerous function calls
        if not LOCAL_BASE.startswith(REPO_ROOT):
            raise Exception(
                "The local SFTP mirror folder is not in your repo, I'm scared to rmtree"
            )
        if not SFTP_BASE.startswith(REPO_ROOT):
            raise Exception(
                "The SFTP folder mount is not in your repo, I'm scared to rmtree"
            )
        empty_dir(LOCAL_BASE)
        empty_dir(SFTP_BASE)

        # Be sure to do any deletes prior to opening a connection
        self.mirrorer = Mirrorer(
            local_base=LOCAL_BASE,
            host=SFTP_HOST,
            username=SFTP_USER,
            password=SFTP_PASS,
            port=SFTP_PORT,
            timeout=3,
        )

    def tearDown(self):
        self.mirrorer.close()

    def test_entry_with_parents(self):
        all_parents = self.entry_with_parents("/some/nested/thing")
        self.assertEqual(
            ["/", "/some/", "/some/nested/", "/some/nested/thing"], all_parents
        )

        all_parents = self.entry_with_parents("/some/nested/")
        self.assertEqual(["/", "/some/", "/some/nested/"], all_parents)

        all_parents = self.entry_with_parents("/")
        self.assertEqual(["/"], all_parents)


if __name__ == "__main__":
    unittest.main()
