import re
import unittest
from os import stat
from stat import S_IEXEC

from common.log import get_logger, arg_parser_with_logs

import os

from test.common.config import REPO_ROOT

SRC_ROOT = os.path.join(REPO_ROOT, 'src')
TEST_ROOT = os.path.join(SRC_ROOT, 'test')

logger = get_logger(__name__)


class TestCodeQuality(unittest.TestCase):

    def test_all_tests_have_unittest_main(self):

        for root, dirs, files in os.walk(TEST_ROOT, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                if re.match(r'.*_test\.py$', file_path):
                    with open(file_path) as python_file:
                        file_content_lines = python_file.readlines()
                        match_found = False
                        for line in file_content_lines:
                            if re.match(' +unittest\.main\(\)', line):
                                logger.info("Has unittest.main(): {}".format(file_path))
                                match_found = True
                                break
                        if not match_found:
                            self.fail("Missing call to unittest.main(): {}".format(file_path))

    def test_all_python_with_main_function_are_executable(self):
        for root, dirs, files in os.walk(TEST_ROOT, topdown=False):
            for name in files:
                file_path = os.path.join(root, name)
                if re.match(r'.*\.py$', file_path):
                    with open(file_path) as python_file:
                        file_content_lines = python_file.readlines()
                        for line in file_content_lines:
                            if "if __name__ == '__main__':" in line:
                                logger.info("Has main guard: {}".format(file_path))
                                is_executable = os.access(file_path, os.X_OK)
                                if not is_executable:
                                    self.fail("Python program is not executable: {}".format(file_path))
                                if not file_content_lines[0] == "#!/usr/bin/env python":
                                    self.fail("Missing shebang: {}".format(file_path))
                                break


if __name__ == "__main__":
    unittest.main()
