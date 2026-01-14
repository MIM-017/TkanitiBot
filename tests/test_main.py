import unittest

from pathlib import Path

from main import create_posted_file

class TestMain(unittest.TestCase):
    def test_create_posted_file_creates_file_if_no_file(self):
        posted_path = Path("posted.txt")

        if posted_path.is_file():
            posted_path.unlink()

        create_posted_file()

        self.assertTrue(posted_path.is_file())


    def test_create_posted_file_ignores_if_file_exists(self):
        posted_path = Path("posted.txt")

        if not posted_path.is_file():
            posted_path.touch()

        create_posted_file()

        self.assertTrue(posted_path.is_file())

if __name__ == '__main__':
    unittest.main()
