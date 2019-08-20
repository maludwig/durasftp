import unittest

from durasftp.common.code_quality import get_all_issues
from durasftp.common.log import get_logger

logger = get_logger(__name__)


class TestCodeQuality(unittest.TestCase):
    def test_all_files_have_quality_code(self):
        issues = get_all_issues(fix_things=False)
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
