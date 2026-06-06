import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from function import copyfolder
from tps2toj import make_tar_xz_with_progress


class HelperTests(unittest.TestCase):
    def test_copyfolder_allows_existing_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "src"
            dst = base / "dst"
            (src / "nested").mkdir(parents=True)
            (src / "nested" / "file.txt").write_text("hello")

            dst.mkdir()

            copyfolder((src,), (dst,))

            copied = dst / "nested" / "file.txt"
            self.assertTrue(copied.exists())
            self.assertEqual(copied.read_text(), "hello")

    def test_make_tar_xz_with_progress_includes_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "src"
            src.mkdir()
            (src / "a.txt").write_text("content")

            dest = base / "out.tar.xz"
            make_tar_xz_with_progress(str(src), str(dest))

            self.assertTrue(dest.exists())
            with tarfile.open(dest, "r:xz") as tar:
                names = tar.getnames()
                self.assertIn("a.txt", names)
                extracted = tar.extractfile("a.txt")
                self.assertIsNotNone(extracted)
                self.assertEqual(extracted.read().decode(), "content")


if __name__ == "__main__":
    unittest.main()
