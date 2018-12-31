#!/usr/bin/env python

import socket
import unittest

from common import empty_dir
from common.log import get_logger
from common.sftp.action_codes import SFTPActionCodes
from common.sftp.mirrorer import Mirrorer
from test.common.config import LOCAL_BASE, SFTP_BASE, SFTP_HOST, SFTP_USER, SFTP_PASS, SFTP_PORT
from config import REPO_ROOT
from common.networking.port_forwarder import start_forwarding, stop_forwarding
from common.networking import ANY_RANDOM_AVAILABLE_PORT
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


# FORWARDING_PORT = 10022


class TestMirrorerShittyNetwork(TestMirrorerBase):
    """
    This class tests what happens when the remote SFTP servers is flaky
    """

    def setUp(self):
        logger.info("In Shitty setUp")
        # Dangerous function calls
        if not LOCAL_BASE.startswith(REPO_ROOT):
            raise Exception("The local SFTP mirror folder is not in your repo, I'm scared to rmtree")
        if not SFTP_BASE.startswith(REPO_ROOT):
            raise Exception("The SFTP folder mount is not in your repo, I'm scared to rmtree")
        empty_dir(LOCAL_BASE)
        empty_dir(SFTP_BASE)

        # Be sure to do any deletes prior to opening a connection
        self.forwarder = start_forwarding(ANY_RANDOM_AVAILABLE_PORT, SFTP_HOST, SFTP_PORT)
        self.forwarding_port = self.forwarder.local_port
        self.mirrorer = Mirrorer(local_base=LOCAL_BASE, host=SFTP_HOST, username=SFTP_USER, password=SFTP_PASS, port=self.forwarding_port, timeout=3)

    def tearDown(self):
        self.mirrorer.close()
        stop_forwarding()

    def test_it_dies_if_the_connection_dies(self):
        self.make_remote_test_file("/test.txt")
        self.mirrorer.mirror_from_remote()
        logger.info("Stopping forwarders")
        self.forwarder.stop()
        self.forwarder.join()
        logger.info("Stopped forwarders")
        self.expect_sftp_failure(self.mirrorer.mirror_from_remote)

    def test_it_dies_if_the_connection_gets_infinitely_slow(self):
        self.make_remote_test_file("/test.txt")
        self.mirrorer.mirror_from_remote()
        logger.info("Cutting speed to 0kbps")
        self.forwarder.adjust_kbps(0)
        logger.info("Cut speed to 0kbps")
        with self.assertRaises(socket.timeout):
            self.mirrorer.mirror_from_remote()
            self.fail("Mirror did not timeout when the network got infinitely slow")

    def test_callbacks_will_have_all_synced_files_on_disconnect(self):
        new_files = []
        remote_paths = ["/file_{}.txt".format(x) for x in range(9)]

        def callback(action):
            if action.action_code == SFTPActionCodes.GET:
                new_files.append(action.remote_path)
                if action.remote_path == "/file_3.txt":
                    # Die halfway through
                    logger.info("Cutting speed to 0kbps")
                    self.forwarder.adjust_kbps(0)
                    logger.info("Cut speed to 0kbps")

        self.make_remote_content(remote_paths)
        with self.assertRaises(socket.timeout):
            self.mirrorer.mirror_from_remote(callback=callback)
        self.assertEqual(["/file_0.txt", "/file_1.txt", "/file_2.txt", "/file_3.txt"], new_files)
        for new_file_remote_path in new_files:
            self.assert_local_has_file(new_file_remote_path)


if __name__ == "__main__":
    unittest.main()
