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
from matlab_utilities.scripts.matlab_quality_check import MatlabQualityChecker


class TestQualityChecker(unittest.TestCase):
    """Test the Python code quality checker."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = QualityChecker()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_placeholder_detection(self):
        """Test that placeholders are detected correctly."""
        # Create a file with a TODO
        test_file = self.temp_path / "test.py"
        test_file.write_text("# TODO: Fix this later\nprint('hello')")

        self.checker.check_placeholders(test_file)

        # Should find one placeholder issue
        placeholder_issues = [
            issue for issue in self.checker.issues if issue[1] == "placeholder"
        ]
        self.assertEqual(len(placeholder_issues), 1)

    def test_wildcard_import_detection(self):
        """Test that wildcard imports are detected."""
        test_file = self.temp_path / "test.py"
        test_file.write_text("from os import *\nprint('hello')")

        self.checker.check_imports(test_file)

        # Should find one wildcard import issue
        import_issues = [
            issue for issue in self.checker.issues if issue[1] == "wildcard_import"
        ]
        self.assertEqual(len(import_issues), 1)

    def test_should_skip_file(self):
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


class TestMatlabQualityChecker(unittest.TestCase):
    """Test the MATLAB code quality checker."""

    def setUp(self):
        """Set up test fixtures."""
        self.checker = MatlabQualityChecker()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_find_matlab_files(self):
        """Test MATLAB file discovery."""
        # Create some test files
        (self.temp_path / "test.m").write_text("% MATLAB function")
        (self.temp_path / "backup.asv").write_text("% Backup file")
        (self.temp_path / "script.py").write_text("# Python file")

        matlab_files = self.checker.find_matlab_files(self.temp_path)

        # Should find only the .m file, not .asv or .py
        self.assertEqual(len(matlab_files), 1)
        self.assertEqual(matlab_files[0].name, "test.m")

    def test_function_detection(self):
        """Test function vs script detection."""
        # Create a function file
        func_file = self.temp_path / "myfunction.m"
        func_content = (
            "function result = myfunction(x)\n"
            "% A test function\n"
            "result = x * 2;\n"
            "end"
        )
        func_file.write_text(func_content)

        file_info = self.checker.analyze_file(func_file)

        self.assertEqual(file_info["type"], "function")
        self.assertEqual(len(file_info["functions"]), 1)
        self.assertEqual(file_info["functions"][0]["name"], "myfunction")

    def test_script_detection(self):
        """Test script detection."""
        # Create a script file
        script_file = self.temp_path / "myscript.m"
        script_file.write_text("% A test script\nx = 1:10;\ny = x.^2;\nplot(x, y);")

        file_info = self.checker.analyze_file(script_file)

        self.assertEqual(file_info["type"], "script")


if __name__ == "__main__":
    unittest.main()
