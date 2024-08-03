import unittest
import os
import tempfile

from claudesync.utils import (
    compute_md5_hash,
    load_gitignore,
    get_local_files,
    load_claudeignore,
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
            with open(os.path.join(tmpdir, "test~"), "w") as f:
                f.write("*.log\n")

            # Create a test~ file
            for vcs in {".git", ".svn", ".hg", ".bzr", "_darcs", "CVS", "claude_chats"}:
                os.mkdir(os.path.join(tmpdir, vcs))
                with open(os.path.join(tmpdir, vcs, "afile"), "w") as f:
                    f.write("*.log\n")

            for buildDir in {"target", "build"}:
                os.mkdir(os.path.join(tmpdir, buildDir))
                with open(os.path.join(tmpdir, buildDir, "output.txt"), "w") as f:
                    f.write("Build output")

            with open(os.path.join(tmpdir, ".gitignore"), "w") as f:
                f.write("*.log\n/build\ntarget")

            local_files = get_local_files(tmpdir)
            print(local_files)

            self.assertIn("file1.txt", local_files)
            self.assertIn("file2.py", local_files)
            self.assertIn(os.path.join("subdir", "file3.txt"), local_files)
            self.assertNotIn(os.path.join("target", "output.txt"), local_files)
            self.assertNotIn(os.path.join("build", "output.txt"), local_files)
            # Ensure ignored files not included
            self.assertEqual(len(local_files), 4)

    def test_load_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            claudeignore_content = "*.log\n/build/\n"
            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:
                f.write(claudeignore_content)

            claudeignore = load_claudeignore(tmpdir)
            self.assertIsNotNone(claudeignore)
            self.assertTrue(claudeignore.match_file("test.log"))
            self.assertTrue(claudeignore.match_file("build/output.txt"))
            self.assertFalse(claudeignore.match_file("src/main.py"))

    def test_get_local_files_with_claudeignore(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            with open(os.path.join(tmpdir, "file1.txt"), "w") as f:
                f.write("Content of file1")
            with open(os.path.join(tmpdir, "file2.log"), "w") as f:
                f.write("Log content")
            os.mkdir(os.path.join(tmpdir, "build"))
            with open(os.path.join(tmpdir, "build", "output.txt"), "w") as f:
                f.write("Build output")

            # Create a .claudeignore file
            with open(os.path.join(tmpdir, ".claudeignore"), "w") as f:
                f.write("*.log\n/build/\n")

            local_files = get_local_files(tmpdir)

            self.assertIn("file1.txt", local_files)
            self.assertNotIn("file2.log", local_files)
            self.assertNotIn(os.path.join("build", "output.txt"), local_files)


if __name__ == "__main__":
    unittest.main()
