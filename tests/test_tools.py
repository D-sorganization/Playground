"""
Tests for the tools package.

These tests verify that our quality checking tools work correctly.
"""

import sys
import tempfile
import unittest
from pathlib import Path

# Add tools to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

from code_quality_check import QualityChecker


class TestQualityChecker(unittest.TestCase):
    """Test the Python code quality checker."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.checker = QualityChecker()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self) -> None:
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_placeholder_detection(self) -> None:
        """Test that placeholders are detected correctly."""
        # Obfuscated to avoid grep false positive in CI placeholder check
        placeholder = "# TO" + "DO: Fix this later"
        test_file = self.temp_path / "test.py"
        test_file.write_text(f"{placeholder}\nprint('hello')")

        self.checker.check_placeholders(test_file)

        # Should find one placeholder issue
        placeholder_issues = [
            issue for issue in self.checker.issues if "placeholder" in issue[1].lower()
        ]
        self.assertEqual(len(placeholder_issues), 1)

    def test_wildcard_import_detection(self) -> None:
        """Test that wildcard imports are detected."""
        test_file = self.temp_path / "test.py"
        test_file.write_text("from os import *\nprint('hello')")

        self.checker.check_imports(test_file)

        # Should find one wildcard import issue
        import_issues = [
            issue for issue in self.checker.issues if issue[1] == "wildcard_import"
        ]
        self.assertEqual(len(import_issues), 1)

    def test_should_skip_file(self) -> None:
        """Test file skipping logic."""
        # Should skip .git files
        git_file = Path(".git/config")
        self.assertTrue(self.checker.should_skip_file(git_file))

        # Should skip markdown files
        md_file = Path("README.md")
        self.assertTrue(self.checker.should_skip_file(md_file))

        # Should not skip Python files
        py_file = Path("test.py")
        self.assertFalse(self.checker.should_skip_file(py_file))


if __name__ == "__main__":
    unittest.main()
