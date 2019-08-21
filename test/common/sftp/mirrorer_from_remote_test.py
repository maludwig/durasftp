import unittest
from os import stat, utime, urandom

from durasftp.common import ONE_MB
from durasftp.common.log import get_logger
from durasftp.common.sftp.action_codes import SFTPActionCodes
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

logger = get_logger(__name__)


class TestMirrorerFromRemote(TestMirrorerBase):
    def test_single_file_mirror(self):
        remote_path, local_path, sftp_path = self.make_remote_test_file("/temp.txt")
        self.mirrorer.mirror_from_remote(dry_run=True)
        self.assert_local_missing(remote_path)
        self.mirrorer.mirror_from_remote()
        self.assert_files_match(remote_path)

    def test_triple_file_mirror(self):
        remote_paths = [
            "/temp.txt",
            "/one/two/temp.txt",
            "/one/two/thing.jpg",
            "/one/thing.jpg",
        ]
        all_path_sets = self.make_remote_content(remote_paths)
        self.mirrorer.mirror_from_remote(dry_run=True)
        for remote_path, local_path, sftp_path in all_path_sets:
            self.assert_local_missing(remote_path)

        self.mirrorer.mirror_from_remote()
        for remote_path, local_path, sftp_path in all_path_sets:
            self.assert_files_match(remote_path)

        get_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.GET]
        )
        self.assertEqual(4, len(get_actions))
        lmkdir_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.LMKDIR]
        )
        self.assertEqual(2, len(lmkdir_actions))

    def test_does_not_copy_twice(self):
        remote_paths = [
            "/temp.txt",
            "/one/two/temp.txt",
            "/one/two/thing.jpg",
            "/one/thing.jpg",
        ]
        self.make_remote_content(remote_paths)
        self.mirrorer.mirror_from_remote()

        # Copies new files
        remote_path, local_path, sftp_path = self.make_remote_test_file(
            "/one/newthing.jpg"
        )
        self.mirrorer.mirror_from_remote()
        get_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.GET]
        )
        self.assertEqual(1, len(get_actions))

        # Remembers what was new
        self.mirrorer.mirror_from_remote()
        get_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.GET]
        )
        self.assertEqual(0, len(get_actions))

        remote_file_stat = stat(sftp_path)
        # Copies files with a different length but the same modification time
        with open(sftp_path, "a") as editedfile:
            editedfile.write("!!!")
        utime(sftp_path, (remote_file_stat.st_atime, remote_file_stat.st_mtime))
        self.mirrorer.mirror_from_remote()
        get_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.GET]
        )
        self.assertEqual(1, len(get_actions))

        # Copies files with the same length but a different same modification time
        utime(sftp_path, (remote_file_stat.st_atime, remote_file_stat.st_mtime + 1))
        self.mirrorer.mirror_from_remote()
        get_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.GET]
        )
        self.assertEqual(1, len(get_actions))

    def test_it_handles_huge_files(self):
        random_megabyte = urandom(ONE_MB)
        # Increase this value to test a larger file
        # iterations = 300
        iterations = 3

        remote_path = "/big/huge.csv"
        self.make_remote_test_file(
            remote_path, content=random_megabyte, iterations=iterations
        )
        self.mirrorer.mirror_from_remote()
        self.assert_files_match(remote_path)

    def test_it_handles_empty_directories(self):
        all_path_sets = self.make_remote_content(["/some/nested/dir/"])
        remote_path, local_path, sftp_path = all_path_sets[0]
        self.mirrorer.mirror_from_remote(dry_run=True)
        self.assert_local_missing(remote_path)
        self.mirrorer.mirror_from_remote()
        lmkdir_actions = self.mirrorer.action_list.filtered_items(
            codes=[SFTPActionCodes.LMKDIR]
        )
        self.assertEqual(3, len(lmkdir_actions))
        self.assert_local_has_dir(remote_path)

    def test_it_overwrites_files_with_dirs(self):
        self.make_local_content(["/initially_a_file"])
        all_path_sets = self.make_remote_content(["/initially_a_file/"])
        remote_path, local_path, sftp_path = all_path_sets[0]
        self.mirrorer.mirror_from_remote(dry_run=True)
        self.assert_local_has_file(remote_path)
        self.mirrorer.mirror_from_remote()
        self.assert_local_has_dir(remote_path)

    def test_it_overwrites_dirs_with_files(self):
        self.make_local_content(["/initially_a_dir/"])
        all_path_sets = self.make_remote_content(["/initially_a_dir"])
        remote_path, local_path, sftp_path = all_path_sets[0]
        self.mirrorer.mirror_from_remote(dry_run=True)
        self.assert_local_has_dir(remote_path)
        self.mirrorer.mirror_from_remote()
        self.assert_local_has_file(remote_path)

    def test_it_overwrites_nested_dirs_with_files(self):
        self.make_local_content(["/initially_a_dir/with/nested/stuff.txt"])
        all_path_sets = self.make_remote_content(["/initially_a_dir"])
        remote_path, local_path, sftp_path = all_path_sets[0]
        self.mirrorer.mirror_from_remote(dry_run=True)
        self.assert_local_has_dir(remote_path)
        self.mirrorer.mirror_from_remote()
        self.assert_local_has_file(remote_path)


if __name__ == "__main__":
    unittest.main()
