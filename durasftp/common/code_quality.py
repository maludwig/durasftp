#!/usr/bin/env python

import os
import re
from stat import S_IXUSR

from durasftp.common.log import arg_parser_with_logs, get_logger
from durasftp.config import REPO_ROOT

SHEBANG_LINE = "#!/usr/bin/env python\n"

fix_things = False

logger = get_logger(__name__)


class FixableIssue:
    def __init__(self, file_path):
        self.file_path = file_path
        with open(self.file_path) as python_file:
            self.file_content_lines = python_file.readlines()

    def has_issue(self):
        pass

    def fix_issue(self):
        pass


class ExecutabilityIssue(FixableIssue):
    def has_issue(self):
        if re.match(r".*\.py$", self.file_path):
            if self.has_main_guard():
                logger.debug("Has main guard: {}".format(self.file_path))
                is_executable = os.access(self.file_path, os.X_OK)
                if not is_executable:
                    return "Python program is not executable"
                if not self.has_shebang():
                    return "Missing shebang"
                if not self.has_newline_after_shebang():
                    return "Missing shebang newline"
        return False

    def has_main_guard(self):
        for line in self.file_content_lines:
            if "if __name__ == '__main__':" in line:
                return True
            if 'if __name__ == "__main__":' in line:
                return True

    def has_shebang(self):
        return self.file_content_lines[0] == SHEBANG_LINE

    def has_newline_after_shebang(self):
        return self.file_content_lines[1] == "\n"

    def fix_issue(self):
        file_stat = os.stat(self.file_path)
        os.chmod(self.file_path, S_IXUSR | file_stat.st_mode)
        if not self.has_shebang():
            self.file_content_lines = [SHEBANG_LINE, "\n"] + self.file_content_lines
            with open(self.file_path, "w") as python_file:
                python_file.writelines(self.file_content_lines)
        elif not self.has_newline_after_shebang():
            self.file_content_lines = [SHEBANG_LINE, "\n"] + self.file_content_lines[1:]
            with open(self.file_path, "w") as python_file:
                python_file.writelines(self.file_content_lines)


UNITTEST_CALL = """
if __name__ == "__main__":
    unittest.main()
"""
UNITTEST_CALL_LINES = UNITTEST_CALL.splitlines(keepends=True)


class TestSuiteIssue(FixableIssue):
    def has_issue(self):
        if re.match(r".*_test\.py$", self.file_path):
            for line in self.file_content_lines:
                if re.match(r" +unittest\.main\(\)", line):
                    return False
            return "Missing unittest.main()"
        return False

    def fix_issue(self):
        self.file_content_lines = self.file_content_lines + UNITTEST_CALL_LINES
        with open(self.file_path, "w") as python_file:
            python_file.writelines(self.file_content_lines)


def get_fixable_issue_classes():
    return [ExecutabilityIssue, TestSuiteIssue]


def get_python_file_paths():
    python_file_paths = []
    for root, dirs, files in os.walk(REPO_ROOT, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            if re.match(r".*\.py$", file_path):
                python_file_paths.append(file_path)
    return python_file_paths[0:4]


def get_all_issues(fix_things=False):
    all_python_file_paths = get_python_file_paths()
    all_issues = []
    for python_file_path in all_python_file_paths:
        logger.debug("Checking: {}".format(python_file_path))
        for fixable_issue_class in get_fixable_issue_classes():
            fixable = fixable_issue_class(python_file_path)
            issue_msg = fixable.has_issue()
            if issue_msg:
                logger.warning("{}: {}".format(issue_msg, python_file_path))
                all_issues.append(fixable)
                if fix_things:
                    fixable.fix_issue()
    return all_issues


if __name__ == "__main__":
    parser = arg_parser_with_logs()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()
    print(vars(args))
    get_all_issues(args.fix)
