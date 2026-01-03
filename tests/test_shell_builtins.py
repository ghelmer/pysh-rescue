import io
import os
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import shell_builtins
from exceptions import ShellExit
from shell_state import ShellState


class TestShellBuiltins(unittest.TestCase):
    def setUp(self):
        self.state = ShellState()

        # Work in a temp dir for filesystem-related builtins
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir.name)
        self.addCleanup(lambda: os.chdir(self.old_cwd))

        # Create a file and a directory for test -f/-d/-e
        self.test_file = os.path.join(self.tmpdir.name, "file.txt")
        with open(self.test_file, "w", encoding="utf-8") as f:
            f.write("hello\n")

        self.test_dir = os.path.join(self.tmpdir.name, "dir")
        os.mkdir(self.test_dir)

    # -----------------------
    # Registry / decorator
    # -----------------------
    def test_registry_contains_expected_builtins(self):
        # Based on your current shell_builtins.py
        for name in ("cat", "cd", "echo", "exit", "export", "pwd", "rm", "test", "["):
            self.assertIn(name, shell_builtins.BUILTINS)

    # ----------------------
    # cat
    # ----------------------
    def test_cat_reads_stdin_when_no_args(self):
        fake_stdin = io.StringIO("a\nb\n")
        out = io.StringIO()
        err = io.StringIO()

        with patch.object(sys, "stdin", fake_stdin), patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["cat"]([], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "a\nb\n")
        self.assertEqual(err.getvalue(), "")

    def test_cat_outputs_file_contents(self):
        with open("f1.txt", "w", encoding="utf-8") as f:
            f.write("hello\nworld\n")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["cat"](["f1.txt"], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "hello\nworld\n")
        self.assertEqual(err.getvalue(), "")

    def test_cat_multiple_files_concatenates(self):
        with open("a.txt", "w", encoding="utf-8") as f:
            f.write("A\n")
        with open("b.txt", "w", encoding="utf-8") as f:
            f.write("B\n")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["cat"](["a.txt", "b.txt"], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue(), "A\nB\n")
        self.assertEqual(err.getvalue(), "")

    def test_cat_missing_file_sets_rc_1_and_writes_stderr(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["cat"](["missing.txt"], self.state)

        self.assertEqual(rc, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("cat: missing.txt: No such file or directory", err.getvalue())

    def test_cat_directory_sets_rc_1_and_writes_stderr(self):
        os.mkdir("adir")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["cat"](["adir"], self.state)

        self.assertEqual(rc, 1)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("cat: adir: Is a directory", err.getvalue())

    # -----------------------
    # echo
    # -----------------------
    def test_echo_prints_joined_args(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = shell_builtins.BUILTINS["echo"](["hello", "world"], self.state)
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "hello world\n")

    def test_echo_no_args_prints_blank_line(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = shell_builtins.BUILTINS["echo"]([], self.state)
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue(), "\n")

    # -----------------------
    # pwd
    # -----------------------
    def test_pwd_prints_current_working_dir(self):
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            rc = shell_builtins.BUILTINS["pwd"]([], self.state)
        self.assertEqual(rc, 0)
        self.assertEqual(buf.getvalue().strip(), os.getcwd())

    # -----------------------
    # cd
    # -----------------------
    def test_cd_changes_directory(self):
        rc = shell_builtins.BUILTINS["cd"](["dir"], self.state)
        self.assertEqual(rc, 0)
        self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.test_dir))

    def test_cd_no_args_uses_home(self):
        # Patch HOME to point to our temp dir
        with patch.dict(os.environ, {"HOME": self.test_dir}):
            rc = shell_builtins.BUILTINS["cd"]([], self.state)
        self.assertEqual(rc, 0)
        self.assertEqual(os.path.realpath(os.getcwd()), os.path.realpath(self.test_dir))

    def test_cd_nonexistent_prints_error(self):
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            rc = shell_builtins.BUILTINS["cd"](["nope"], self.state)
        self.assertEqual(rc, 1)
        self.assertIn("cd: no such file or directory: nope", buf.getvalue())

    def test_cd_not_a_directory_prints_error(self):
        # file.txt exists but isn't a directory
        buf = io.StringIO()
        with patch("sys.stderr", buf):
            rc = shell_builtins.BUILTINS["cd"](["file.txt"], self.state)
        self.assertEqual(rc, 1)
        self.assertIn("cd: not a directory: file.txt", buf.getvalue())

    # -----------------------
    # exit
    # -----------------------
    def test_exit_no_args_exits_with_0(self):
        with self.assertRaises(ShellExit) as ctx:
            shell_builtins.BUILTINS["exit"]([], self.state)
        self.assertEqual(ctx.exception.status, 0)

    def test_exit_with_status(self):
        with self.assertRaises(ShellExit) as ctx:
            shell_builtins.BUILTINS["exit"](["7"], self.state)
        self.assertEqual(ctx.exception.status, 7)

    # ----------------------
    # export
    # ----------------------
    def test_export_name_value_sets_state_and_env(self):
        out = io.StringIO()
        err = io.StringIO()

        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["export"](["X=123"], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(self.state.get_var("X"), "123")
        self.assertEqual(os.environ.get("X"), "123")

    def test_export_name_exports_existing_state_value(self):
        self.state.set_var("Y", "hello", export=False)

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["export"](["Y"], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(os.environ.get("Y"), "hello")

    def test_export_invalid_identifier_returns_1_and_writes_stderr(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["export"](["9BAD=1"], self.state)

        self.assertEqual(rc, 1)
        self.assertIn("export: not a valid identifier: 9BAD", err.getvalue())

    def test_export_no_args_prints_environment(self):
        # Put a known env var in place to assert it appears
        with patch.dict(os.environ, {"RESCUE_TEST_VAR": "OK"}, clear=False):
            out = io.StringIO()
            err = io.StringIO()
            with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
                rc = shell_builtins.BUILTINS["export"]([], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")
        # output includes many env vars; check ours is present
        self.assertIn("RESCUE_TEST_VAR=OK", out.getvalue())

    # ----------------------
    # rm
    # ----------------------
    def test_rm_removes_file(self):
        with open("t.txt", "w", encoding="utf-8") as f:
            f.write("x")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["t.txt"], self.state)

        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists("t.txt"))
        self.assertEqual(err.getvalue(), "")

    def test_rm_missing_file_returns_1(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["missing.txt"], self.state)

        self.assertEqual(rc, 1)
        self.assertIn("rm: cannot remove 'missing.txt': No such file or directory", err.getvalue())

    def test_rm_missing_file_with_force_returns_0(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["-f", "missing.txt"], self.state)

        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")

    def test_rm_directory_without_r_returns_1(self):
        os.mkdir("d")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["d"], self.state)

        self.assertEqual(rc, 1)
        self.assertTrue(os.path.exists("d"))
        self.assertIn("rm: cannot remove 'd': Is a directory", err.getvalue())

    def test_rm_directory_with_r_removes(self):
        os.mkdir("d")
        with open(os.path.join("d", "f.txt"), "w", encoding="utf-8") as f:
            f.write("x")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["-r", "d"], self.state)

        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists("d"))
        self.assertEqual(err.getvalue(), "")

    def test_rm_directory_with_rf_removes(self):
        os.mkdir("d2")
        with open(os.path.join("d2", "f.txt"), "w", encoding="utf-8") as f:
            f.write("x")

        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["-rf", "d2"], self.state)

        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists("d2"))
        self.assertEqual(err.getvalue(), "")

    def test_rm_invalid_option_returns_2(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["-z", "whatever"], self.state)

        self.assertEqual(rc, 2)
        self.assertIn("rm: invalid option -- 'z'", err.getvalue())

    def test_rm_missing_operand_returns_1(self):
        out = io.StringIO()
        err = io.StringIO()
        with patch.object(sys, "stdout", out), patch.object(sys, "stderr", err):
            rc = shell_builtins.BUILTINS["rm"]([], self.state)

        self.assertEqual(rc, 1)
        self.assertIn("rm: missing operand", err.getvalue())


    def test_rm_r_dotdot_is_refused_and_does_not_delete(self):
        err = io.StringIO()

        # Patch deletion primitives so nothing can be deleted even if buggy.
        with patch.object(shell_builtins.os, "remove") as mock_remove, \
             patch.object(shell_builtins.shutil, "rmtree") as mock_rmtree, \
             patch("sys.stderr", err):

            rc = shell_builtins.BUILTINS["rm"](["-r", ".."], self.state)

        # Should refuse and return non-zero
        self.assertEqual(rc, 1)
        self.assertIn("rm: refusing to remove '..': contains '..'", err.getvalue())
        self.assertIn("..", err.getvalue())

        mock_remove.assert_not_called()
        mock_rmtree.assert_not_called()

    def test_rm_r_root_is_refused_and_does_not_delete(self):
        err = io.StringIO()

        # We *don't* want this test to ever touch the real filesystem.
        # Simulate that the resolved path is "/" regardless of input.
        with patch.object(shell_builtins.os, "remove") as mock_remove, \
             patch.object(shell_builtins.shutil, "rmtree") as mock_rmtree, \
             patch.object(shell_builtins.os.path, "abspath", return_value="/"), \
             patch.object(shell_builtins.os.path, "normpath", return_value="/"), \
             patch.object(shell_builtins.os.path, "realpath", return_value="/"), \
             patch("sys.stderr", err):

            rc = shell_builtins.BUILTINS["rm"](["-r", "/"], self.state)

        self.assertEqual(rc, 1)
        self.assertIn("rm: refusing to remove '/' recursively", err.getvalue())

        mock_remove.assert_not_called()
        mock_rmtree.assert_not_called()

    def test_rm_double_dash_allows_dash_leading_filename(self):
        err = io.StringIO()

        # We want to ensure it treats "-rf" as a PATH, not flags, when preceded by "--".
        # We'll simulate that "-rf" is a regular file by making lstat return a non-dir.
        fake_stat = os.stat_result((stat.S_IFREG,) + (0,) * 9)

        # Safe tests: patch os.remove and shutil.rmtree to prevent filesystem destruction
        with patch.object(shell_builtins.os, "lstat", return_value=fake_stat) as mock_lstat, \
             patch.object(shell_builtins.os, "remove") as mock_remove, \
             patch.object(shell_builtins.shutil, "rmtree") as mock_rmtree, \
             patch("sys.stderr", err):

            rc = shell_builtins.BUILTINS["rm"](["--", "-rf"], self.state)

        self.assertEqual(rc, 0)
        # It should attempt to remove the literal filename "-rf"
        mock_lstat.assert_called_once_with("-rf")
        mock_remove.assert_called_once_with("-rf")
        mock_rmtree.assert_not_called()
        self.assertEqual(err.getvalue(), "")

    def test_rm_stops_parsing_options_at_first_path(self):
        err = io.StringIO()

        # Simulate both "file" and "-rf" are regular files
        fake_stat = os.stat_result((stat.S_IFREG,) + (0,) * 9)

        with patch.object(shell_builtins.os, "lstat", return_value=fake_stat) as mock_lstat, \
                patch.object(shell_builtins.os, "remove") as mock_remove, \
                patch.object(shell_builtins.shutil, "rmtree") as mock_rmtree, \
                patch("sys.stderr", err):
            rc = shell_builtins.BUILTINS["rm"](["file", "-rf"], self.state)

        self.assertEqual(rc, 0)
        # Both should be treated as paths and removed
        mock_remove.assert_any_call("file")
        mock_remove.assert_any_call("-rf")
        self.assertEqual(mock_remove.call_count, 2)
        mock_rmtree.assert_not_called()
        self.assertEqual(err.getvalue(), "")


    # -----------------------
    # test / [
    # -----------------------
    def test_test_empty_args_is_false(self):
        rc = shell_builtins.BUILTINS["test"]([], self.state)
        self.assertEqual(rc, 1)

    def test_test_single_arg_nonempty_is_true(self):
        rc = shell_builtins.BUILTINS["test"](["abc"], self.state)
        self.assertEqual(rc, 0)

    def test_test_single_arg_empty_is_false(self):
        rc = shell_builtins.BUILTINS["test"]([""], self.state)
        self.assertEqual(rc, 1)

    # String comparisons
    def test_test_string_equal(self):
        self.assertEqual(shell_builtins.BUILTINS["test"](["a", "=", "a"], self.state), 0)
        self.assertEqual(shell_builtins.BUILTINS["test"](["a", "=", "b"], self.state), 1)

    def test_test_string_not_equal(self):
        self.assertEqual(shell_builtins.BUILTINS["test"](["a", "!=", "b"], self.state), 0)
        self.assertEqual(shell_builtins.BUILTINS["test"](["a", "!=", "a"], self.state), 1)

    # Numeric comparisons
    def test_test_numeric_ops(self):
        t = shell_builtins.BUILTINS["test"]
        self.assertEqual(t(["3", "-eq", "3"], self.state), 0)
        self.assertEqual(t(["3", "-ne", "4"], self.state), 0)
        self.assertEqual(t(["3", "-lt", "4"], self.state), 0)
        self.assertEqual(t(["3", "-le", "3"], self.state), 0)
        self.assertEqual(t(["4", "-gt", "3"], self.state), 0)
        self.assertEqual(t(["4", "-ge", "4"], self.state), 0)

        self.assertEqual(t(["3", "-gt", "4"], self.state), 1)

    # Unary file tests
    def test_test_unary_file_ops(self):
        t = shell_builtins.BUILTINS["test"]

        self.assertEqual(t(["-f", "file.txt"], self.state), 0)
        self.assertEqual(t(["-f", "dir"], self.state), 1)

        self.assertEqual(t(["-d", "dir"], self.state), 0)
        self.assertEqual(t(["-d", "file.txt"], self.state), 1)

        self.assertEqual(t(["-e", "file.txt"], self.state), 0)
        self.assertEqual(t(["-e", "dir"], self.state), 0)
        self.assertEqual(t(["-e", "missing"], self.state), 1)

    # Unary string tests
    def test_test_unary_string_ops(self):
        t = shell_builtins.BUILTINS["test"]
        self.assertEqual(t(["-z", ""], self.state), 0)
        self.assertEqual(t(["-z", "x"], self.state), 1)
        self.assertEqual(t(["-n", "x"], self.state), 0)
        self.assertEqual(t(["-n", ""], self.state), 1)

    def test_bracket_form_strips_trailing_bracket(self):
        # "[" is registered to the same function as "test"
        rc = shell_builtins.BUILTINS["["](["a", "=", "a", "]"], self.state)
        self.assertEqual(rc, 0)

        rc2 = shell_builtins.BUILTINS["["](["a", "=", "b", "]"], self.state)
        self.assertEqual(rc2, 1)


if __name__ == "__main__":
    unittest.main()
