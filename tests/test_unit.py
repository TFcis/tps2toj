import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from function import symlinkfolder
from tps2toj import make_tar_xz_with_progress


class HelperTests(unittest.TestCase):
    def test_symlinkfolder_links_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            src = base / "src"
            dst = base / "dst"
            (src / "nested").mkdir(parents=True)
            (src / "nested" / "file.txt").write_text("hello")

            symlinkfolder((src,), (dst,))

            linked = dst / "nested" / "file.txt"
            self.assertTrue(dst.is_symlink())
            self.assertTrue(linked.exists())
            self.assertEqual(linked.read_text(), "hello")

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

    def test_make_tar_xz_with_progress_dereferences_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source"
            source.mkdir()
            (source / "a.txt").write_text("content")

            work = base / "work"
            work.mkdir()
            (work / "linked-dir").symlink_to(source, target_is_directory=True)
            (work / "linked-file.txt").symlink_to(source / "a.txt")

            dest = base / "out.tar.xz"
            make_tar_xz_with_progress(str(work), str(dest))

            with tarfile.open(dest, "r:xz") as tar:
                linked_dir_info = tar.getmember("linked-dir/a.txt")
                linked_file_info = tar.getmember("linked-file.txt")
                self.assertTrue(linked_dir_info.isfile())
                self.assertTrue(linked_file_info.isfile())
                self.assertEqual(tar.extractfile(linked_dir_info).read().decode(), "content")
                self.assertEqual(tar.extractfile(linked_file_info).read().decode(), "content")


if __name__ == "__main__":
    unittest.main()
