import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "remediation"))
from common import safe_repo_path

class SafetyTests(unittest.TestCase):
    def test_relative_path_allowed(self):
        self.assertEqual(safe_repo_path("src/app.py"), "src/app.py")

    def test_parent_traversal_rejected(self):
        with self.assertRaises(ValueError):
            safe_repo_path("../outside.txt")

    def test_absolute_path_rejected(self):
        with self.assertRaises(ValueError):
            safe_repo_path("/etc/passwd")

if __name__ == "__main__":
    unittest.main()
