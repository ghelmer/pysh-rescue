import io
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import runner
from command import Command
from shell_state import ShellState


class TestRunner(unittest.TestCase):
    def setUp(self):
        self.state = ShellState()
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(lambda: os.chdir(self.cwd))

    # Helpers
    def read_file(self, name: str) -> str:
        with open(os.path.join(self.tmpdir.name, name), "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, name: str, content: str) -> str:
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    # Builtins Tests
    def test_builtin_runs_and_returns_status(self):
        def fake_builtin(args, state):
            return 5

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command("foo", ["a", "b"])
            rc = runner.execute_command(cmd, self.state)
            self.assertEqual(5, rc)

    def test_builtin_stdout_redirection_overwrite(self):
        def fake_builtin(args, state):
            print("hello")
            return 0

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command("foo", [], stdout="out.txt", append=False)
            rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        self.assertEqual("hello\n", self.read_file("out.txt"))

    def test_builtin_stdout_redirection_append(self):
        self.write_file("out.txt", "first\n")

        def fake_builtin(args, state):
            print("second")
            return 0

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command("foo", [], stdout="out.txt", append=True)
            rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        self.assertEqual("first\nsecond\n", self.read_file("out.txt"))

    def test_builtin_stderr_redirection(self):
        def fake_builtin(args, state):
            print("oops", file=runner.sys.stderr)
            return 0

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command("foo", [], stderr="err.txt", stderr_append=False)
            rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        self.assertEqual("oops\n", self.read_file("err.txt"))

    def test_builtin_redirect_both_stdout_and_stderr(self):
        def fake_builtin(args, state):
            print("OUT")
            print("ERR", file=runner.sys.stderr)
            return 0

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command(
                "foo", [],
                stdout="both.txt",
                append=False,
                redirect_both=True
            )
            rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        # both go to same file; ordering should be OUT then ERR for this function
        self.assertEqual("OUT\nERR\n", self.read_file("both.txt"))

    def test_builtin_stdin_redirection(self):
        self.write_file("in.txt", "line1\nline2\n")

        def fake_builtin(args, state):
            # Read from stdin and echo back to stdout
            data = runner.sys.stdin.read()
            print(data, end="")
            return 0

        with patch.object(runner, "BUILTINS", {"foo": fake_builtin}):
            cmd = Command("foo", [], stdin="in.txt", stdout="out.txt", append=False)
            rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        self.assertEqual("line1\nline2\n", self.read_file("out.txt"))

    # Test External commands
    @patch.object(runner.subprocess, "run")
    def test_external_command_calls_subprocess_run(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        cmd = Command("ext", ["a", "b"])
        rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(["ext", "a", "b"], args[0])
        self.assertIsNone(kwargs.get("stdin"))
        self.assertIsNone(kwargs.get("stdout"))
        self.assertIsNone(kwargs.get("stderr"))

    @patch.object(runner.subprocess, "run")
    def test_external_command_stdout_redirect(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        cmd = Command("ext", ["x"], stdout="out.txt", append=False)
        rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        args, kwargs = mock_run.call_args
        self.assertEqual(["ext", "x"], args[0])
        self.assertIsNotNone(kwargs.get("stdout"))
        self.assertIsNone(kwargs.get("stderr"))

        # verify file exists and is writable by handle (the runner created it)
        self.assertTrue(os.path.exists("out.txt"))

    @patch.object(runner.subprocess, "run")
    def test_external_command_stderr_redirect(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        cmd = Command("ext", [], stderr="err.txt", stderr_append=False)
        rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        args, kwargs = mock_run.call_args
        self.assertIsNotNone(kwargs.get("stderr"))
        self.assertTrue(os.path.exists("err.txt"))

    @patch.object(runner.subprocess, "run")
    def test_external_command_redirect_both(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        cmd = Command("ext", [], stdout="both.txt", append=False, redirect_both=True)
        rc = runner.execute_command(cmd, self.state)

        self.assertEqual(rc, 0)
        args, kwargs = mock_run.call_args
        # stdout and stderr should be the same handle object
        self.assertIs(kwargs.get("stdout"), kwargs.get("stderr"))
        self.assertTrue(os.path.exists("both.txt"))

    @patch.object(runner.subprocess, "run")
    def test_external_command_stdin_redirect(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        self.write_file("in.txt", "abc\n")

        cmd = Command("ext", ["arg"], stdin="in.txt")
        rc = runner.execute_command(cmd, self.state)

        self.assertEqual(0, rc)
        args, kwargs = mock_run.call_args
        self.assertIsNotNone(kwargs.get("stdin"))

    def test_external_command_not_found_returns_127_and_writes_stderr(self):
        # Capture sys.stderr output for the duration of the call
        buf = io.StringIO()
        with patch.object(runner, "BUILTINS", {}), patch.object(runner.subprocess, "run", side_effect=FileNotFoundError):
            with patch.object(runner.sys, "stderr", buf):
                cmd = Command("nope", [])
                rc = runner.execute_command(cmd, self.state)

        self.assertEqual(127, rc)
        self.assertIn("nope: command not found", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
