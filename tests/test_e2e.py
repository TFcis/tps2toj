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


def _build_dummy_problem(
    base: Path,
    with_checker: bool = False,
    with_grader: bool = False,
    with_statement: bool = True,
    with_validator: bool = True,
    mapping: str = "s1 a\n",
    subtasks=None,
    testcases=None,
) -> Path:
    input_dir = base / "input"
    (input_dir / "tests").mkdir(parents=True)
    if with_validator:
        (input_dir / "validator").mkdir(parents=True)
    if with_statement:
        (input_dir / "statement").mkdir(parents=True)

    # Minimal required files
    if with_validator:
        (input_dir / "validator" / "placeholder.txt").write_text("validator")
    (input_dir / "tests" / "mapping").write_text(mapping)
    if testcases is None:
        testcases = {"a": ("42\n", "42\n")}
    for name, (input_content, output_content) in testcases.items():
        (input_dir / "tests" / f"{name}.in").write_text(input_content)
        (input_dir / "tests" / f"{name}.out").write_text(output_content)
    if with_statement:
        (input_dir / "statement" / "index.pdf").write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    problem = {
        "time_limit": 1.5,
        "memory_limit": 256,
        "has_checker": with_checker,
        "has_grader": with_grader,
        "name": "sample",
    }
    if subtasks is None:
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


def _run_converter(input_dir: Path, output_base: Path, *extra_args: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPT), *extra_args, str(input_dir), str(output_base)]
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


class E2ETests(unittest.TestCase):
    def test_e2e_creates_archive_without_keep(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base, with_checker=False, with_grader=False)
            output_base = base / "out"

            _run_converter(input_dir, output_base)

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

            _run_converter(input_dir, output_base, "-k")

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
            self.assertTrue((preserved_dir / "res" / "testdata" / "1.in").is_symlink())
            self.assertTrue((preserved_dir / "res" / "testdata" / "1.out").is_symlink())
            self.assertTrue((preserved_dir / "res" / "checker").is_symlink())
            self.assertTrue((preserved_dir / "res" / "grader").is_symlink())

    def test_e2e_skips_comments_malformed_lines_and_unknown_subtasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(
                base,
                mapping="# comment\n\ns1 a\nmalformed\nunknown b\ns2 c\n",
                subtasks={"subtasks": {"s1": {"score": 40}, "s2": {"score": 60}}},
                testcases={
                    "a": ("1\n", "1\n"),
                    "b": ("2\n", "2\n"),
                    "c": ("3\n", "3\n"),
                },
            )
            output_base = base / "out_mapping"

            result = _run_converter(input_dir, output_base)

            self.assertIn("Skipping malformed line", result.stderr)
            self.assertIn("is not defined in subtasks.json", result.stderr)
            tar_path = _find_tar(output_base)
            with tarfile.open(tar_path, "r:xz") as tar:
                names = tar.getnames()
                self.assertIn("res/testdata/1.in", names)
                self.assertIn("res/testdata/2.in", names)
                self.assertNotIn("res/testdata/3.in", names)
                self.assertEqual(tar.extractfile("res/testdata/1.in").read().decode(), "1\n")
                self.assertEqual(tar.extractfile("res/testdata/2.in").read().decode(), "3\n")
                conf = json.load(tar.extractfile("conf.json"))
                self.assertEqual(
                    conf["test"],
                    [{"data": [1], "weight": 40}, {"data": [2], "weight": 60}],
                )

    def test_e2e_omits_optional_statement_and_validator_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(
                base,
                with_statement=False,
                with_validator=False,
            )
            output_base = base / "out_optional"

            _run_converter(input_dir, output_base)

            tar_path = _find_tar(output_base)
            with tarfile.open(tar_path, "r:xz") as tar:
                names = tar.getnames()
                self.assertNotIn("http/cont.pdf", names)
                self.assertNotIn("res/validator/placeholder.txt", names)
                self.assertIn("conf.json", names)

    def test_e2e_no_progress_suppresses_progress_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base)
            output_base = base / "out_no_progress"

            result = _run_converter(input_dir, output_base, "--no-progress")

            self.assertNotIn("Compression Progress", result.stdout)
            self.assertTrue(_find_tar(output_base).exists())

    def test_e2e_rejects_unexpected_subtasks_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base, subtasks={"subtasks": []})
            output_base = base / "out_bad_subtasks"

            cmd = [sys.executable, str(SCRIPT), str(input_dir), str(output_base)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unexpected format", result.stderr)
            self.assertEqual(list(base.glob("*.tar.xz")), [])

    def test_e2e_fails_when_problem_json_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            input_dir = _build_dummy_problem(base)
            (input_dir / "problem.json").unlink()
            output_base = base / "out_missing_problem"

            cmd = [sys.executable, str(SCRIPT), str(input_dir), str(output_base)]
            result = subprocess.run(cmd, capture_output=True, text=True)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("problem.json not found", result.stderr)
            self.assertEqual(list(base.glob("*.tar.xz")), [])


if __name__ == "__main__":
    unittest.main()
