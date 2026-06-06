import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SCRIPT = ROOT / "tps2toj.py"


def _build_dummy_problem(base: Path, with_checker: bool = False, with_grader: bool = False) -> Path:
    input_dir = base / "input"
    (input_dir / "tests").mkdir(parents=True)
    (input_dir / "validator").mkdir(parents=True)
    (input_dir / "statement").mkdir(parents=True)

    # Minimal required files
    (input_dir / "validator" / "placeholder.txt").write_text("validator")
    (input_dir / "tests" / "mapping").write_text("s1 a\n")
    (input_dir / "tests" / "a.in").write_text("42\n")
    (input_dir / "tests" / "a.out").write_text("42\n")
    (input_dir / "statement" / "index.pdf").write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    problem = {
        "time_limit": 1.5,
        "memory_limit": 256,
        "has_checker": with_checker,
        "has_grader": with_grader,
        "name": "sample",
    }
    subtasks = {"subtasks": {"s1": {"score": 100}}}

    (input_dir / "problem.json").write_text(json.dumps(problem))
    (input_dir / "subtasks.json").write_text(json.dumps(subtasks))

    if with_checker:
        (input_dir / "checker").mkdir()
        (input_dir / "checker" / "checker.cpp").write_text("// checker\n")

    if with_grader:
        (input_dir / "grader").mkdir()
        (input_dir / "grader" / "grader.txt").write_text("grader\n")

    return input_dir


def _find_tar(output_base: Path):
    prefixes = (output_base.name + "_")
    tar_candidates = [p for p in output_base.parent.glob("*.tar.xz") if p.name.startswith(prefixes)]
    assert tar_candidates, "No tar.xz output found"
    return tar_candidates[0]


def _find_output_dir(output_base: Path):
    prefixes = (output_base.name + "(", output_base.name + "_")
    dirs = [p for p in output_base.parent.iterdir() if p.is_dir() and p.name.startswith(prefixes)]
    return dirs[0] if dirs else None


class E2ETests(unittest.TestCase):
    def test_e2e_creates_archive_without_keep(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base, with_checker=False, with_grader=False)
            output_base = base / "out"

            cmd = [sys.executable, str(SCRIPT), str(input_dir), str(output_base)]
            subprocess.run(cmd, check=True)

            tar_path = _find_tar(output_base)
            with tarfile.open(tar_path, "r:xz") as tar:
                names = tar.getnames()
                self.assertIn("conf.json", names)
                self.assertIn("res/testdata/1.in", names)
                self.assertIn("res/testdata/1.out", names)
                conf = json.load(tar.extractfile("conf.json"))
                self.assertEqual(conf["timelimit"], 1500)
                self.assertEqual(conf["memlimit"], 256 * 1024)
                self.assertEqual(conf["test"], [{"data": [1], "weight": 100}])

            preserved_dir = _find_output_dir(output_base)
            self.assertIsNone(preserved_dir)  # should be cleaned when keep flag is not set

    def test_e2e_preserves_directory_with_keep(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base, with_checker=True, with_grader=True)
            output_base = base / "out_keep"

            cmd = [sys.executable, str(SCRIPT), "-k", str(input_dir), str(output_base)]
            subprocess.run(cmd, check=True)

            tar_path = _find_tar(output_base)
            with tarfile.open(tar_path, "r:xz") as tar:
                names = tar.getnames()
                self.assertIn("conf.json", names)
                self.assertIn("res/checker/checker.cpp", names)
                self.assertIn("res/grader/grader.txt", names)
                conf = json.load(tar.extractfile("conf.json"))
                self.assertTrue(conf["has_grader"])
                self.assertEqual(conf["check"], "cms")

            preserved_dir = _find_output_dir(output_base)
            self.assertIsNotNone(preserved_dir)
            self.assertTrue((preserved_dir / "conf.json").exists())
            self.assertTrue((preserved_dir / "res" / "testdata" / "1.in").exists())
            self.assertTrue((preserved_dir / "res" / "checker" / "checker.cpp").exists())
            self.assertTrue((preserved_dir / "res" / "grader" / "grader.txt").exists())


if __name__ == "__main__":
    unittest.main()
