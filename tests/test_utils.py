import unittest
import os
import tempfile

from claudesync.utils import (
    compute_md5_hash,
    load_gitignore,
    get_local_files,
)


class TestUtils(unittest.TestCase):

    def test_calculate_checksum(self):
        content = "Hello, World!"
        expected_checksum = "65a8e27d8879283831b664bd8b7f0ad4"
        self.assertEqual(compute_md5_hash(content), expected_checksum)

    def test_load_gitignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            gitignore_content = "*.log\n/node_modules\n"
            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write(gitignore_content)

            gitignore = load_gitignore(tmpdir)
            self.assertIsNotNone(gitignore)
            self.assertTrue(gitignore.match_file("test.log"))
            self.assertTrue(gitignore.match_file("node_modules/package.json"))
            self.assertFalse(gitignore.match_file("src/main.py"))

    def test_get_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
                f.write("Content of file1")
            with open(os.path.join(tmpdir, "file2.py"), "w") as f:
                f.write("print('Hello, World!')")
            os.mkdir(os.path.join(tmpdir, "subdir"))
            with open(os.path.join(tmpdir, "subdir", "file3.txt"), "w") as f:
                f.write("Content of file3")

            # Create a .git file
            for vcs in {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS"}:
                os.makedirs(os.path.join(tmpdir, vcs), exist_ok=True)
                with open(os.path.join(tmpdir, vcs, ".gitignore"), "w") as f:
                    f.write("*.log\n")

            # Create a test~ file
            with open(os.path.join(tmpdir, "test~"), "w") as f:
                f.write("*.log\n")

            local_files = get_local_files(tmpdir)

            self.assertIn("file1.txt", local_files)
            self.assertIn("file2.py", local_files)
            self.assertIn(os.path.join("subdir", "file3.txt"), local_files)
            # Ensure ignored files not included
            self.assertEqual(len(local_files), 3)


if __name__ == "__main__":
    unittest.main()
