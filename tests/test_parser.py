import unittest
from unittest.mock import patch

import parser as parser_mod
from shell_state import ShellState
from command import CommandNode


class TestParser(unittest.TestCase):
    def setUp(self):
        self.state = ShellState()

    # Tests for split_on_semicolons
    def test_split_on_semicolons_basic(self):
        tokens = ["echo", "hi", ";", "ls", ";", "pwd"]
        groups = parser_mod.split_on_semicolons(tokens)
        self.assertEqual([["echo", "hi"], ["ls"], ["pwd"]], groups)

    def test_split_on_semicolons_ignores_empty_segments(self):
        tokens = [";", "echo", "hi", ";", ";", "pwd", ";"]
        groups = parser_mod.split_on_semicolons(tokens)
        self.assertEqual([["echo", "hi"], ["pwd"]], groups)

    # Tests for is_assignment_token
    def test_is_assignment_token_valid(self):
        self.assertTrue(parser_mod.is_assignment_token("X=1"))
        self.assertTrue(parser_mod.is_assignment_token("_X=hello"))
        self.assertTrue(parser_mod.is_assignment_token("X_Y=hello"))

    def test_is_assignment_token_invalid(self):
        self.assertFalse(parser_mod.is_assignment_token("=nope"))
        self.assertFalse(parser_mod.is_assignment_token("9X=bad"))
        self.assertFalse(parser_mod.is_assignment_token("NOEQUALS"))

    # Tests for parse_simple_command - assignments
    # -------------------------
    def test_parse_simple_command_only_assignments_returns_none_and_sets_state(self):
        cmd = parser_mod.parse_simple_command(["A=1", "B=two"], self.state)
        self.assertIsNone(cmd)
        self.assertEqual("1", self.state.get_var("A"))
        self.assertEqual("two", self.state.get_var("B"))

    def test_parse_simple_command_leading_assignments_then_command(self):
        cmd = parser_mod.parse_simple_command(["A=1", "echo", "$A"], self.state)
        self.assertIsNotNone(cmd)
        self.assertEqual("echo", cmd.name)
        self.assertEqual(["1"], cmd.args)  # interpolation after assignment
        self.assertEqual("1", self.state.get_var("A"))

    # Tests for parse_simple_command - interpolation
    # -------------------------
    def test_parse_simple_command_interpolates_vars(self):
        self.state.set_var("X", "hello", export=False)
        cmd = parser_mod.parse_simple_command(["echo", "$X", "world"], self.state)
        self.assertEqual("echo", cmd.name)
        self.assertEqual(["hello", "world"], cmd.args)

    # Tests for parse_simple_command - globbing
    @patch.object(parser_mod.glob, "glob")
    def test_parse_simple_command_globbing_expands_matches(self, mock_glob):
        mock_glob.return_value = ["b.py", "a.py"]
        cmd = parser_mod.parse_simple_command(["ls", "*.py"], self.state)
        # expand_globs sorts matches
        self.assertEqual(["a.py", "b.py"], cmd.args)

    @patch.object(parser_mod.glob, "glob")
    def test_parse_simple_command_globbing_no_matches_keeps_literal(self, mock_glob):
        mock_glob.return_value = []
        cmd = parser_mod.parse_simple_command(["ls", "*.nomatch"], self.state)
        self.assertEqual(["*.nomatch"], cmd.args)

    # Tests for parse_simple_command - stdout redirection
    def test_stdout_redirect_overwrite(self):
        cmd = parser_mod.parse_simple_command(["echo", "hi", ">", "out.txt"], self.state)
        self.assertEqual("out.txt", cmd.stdout)
        self.assertFalse(cmd.append)

    def test_stdout_redirect_append(self):
        cmd = parser_mod.parse_simple_command(["echo", "hi", ">>", "out.txt"], self.state)
        self.assertEqual("out.txt", cmd.stdout)
        self.assertTrue(cmd.append)

    def test_stdout_redirect_missing_filename_raises(self):
        with self.assertRaises(SyntaxError):
            parser_mod.parse_simple_command(["echo", "hi", ">"], self.state)

    # Tests for parse_simple_command - stdin redirection
    def test_stdin_redirect(self):
        cmd = parser_mod.parse_simple_command(["cat", "<", "in.txt"], self.state)
        self.assertEqual("in.txt", cmd.stdin,)

    def test_stdin_redirect_missing_filename_raises(self):
        with self.assertRaises(SyntaxError):
            parser_mod.parse_simple_command(["cat", "<"], self.state)

    # Tests for parse_simple_command - stderr redirection (spaced)
    def test_stderr_redirect_spaced_overwrite(self):
        cmd = parser_mod.parse_simple_command(["ls", "missing", "2", ">", "err.txt"], self.state)
        self.assertEqual("err.txt", cmd.stderr)
        self.assertFalse(cmd.stderr_append)

    def test_stderr_redirect_spaced_append(self):
        cmd = parser_mod.parse_simple_command(["ls", "missing", "2", ">>", "err.txt"], self.state)
        self.assertEqual("err.txt", cmd.stderr)
        self.assertTrue(cmd.stderr_append)

    def test_unsupported_fd_redirection_raises(self):
        with self.assertRaises(SyntaxError):
            parser_mod.parse_simple_command(["echo", "hi", "3", ">", "x.txt"], self.state)

    # Tests for parse_simple_command - combined redirection tokens
    def test_stderr_redirect_combined_no_space(self):
        cmd = parser_mod.parse_simple_command(["ls", "missing", "2>err.txt"], self.state)
        self.assertEqual("err.txt", cmd.stderr)
        self.assertFalse(cmd.stderr_append)

    def test_stderr_redirect_combined_space(self):
        cmd = parser_mod.parse_simple_command(["ls", "missing", "2>", "err.txt"], self.state)
        self.assertEqual("err.txt", cmd.stderr)
        self.assertFalse(cmd.stderr_append)

    def test_both_redirect_combined_no_space(self):
        cmd = parser_mod.parse_simple_command(["ls", "&>both.txt"], self.state)
        self.assertTrue(cmd.redirect_both)
        self.assertEqual("both.txt", cmd.stdout)
        self.assertEqual("both.txt", cmd.stderr)
        self.assertFalse(cmd.append)
        self.assertFalse(cmd.stderr_append)

    def test_both_redirect_combined_append(self):
        cmd = parser_mod.parse_simple_command(["ls", "&>>both.txt"], self.state)
        self.assertTrue(cmd.redirect_both)
        self.assertEqual("both.txt", cmd.stdout)
        self.assertEqual("both.txt", cmd.stderr)
        self.assertTrue(cmd.append)
        self.assertTrue(cmd.stderr_append)

    # Tests for parse_command_list
    def test_parse_command_list_multiple_commands(self):
        tokens = ["A=1", ";", "echo", "$A", ";", "pwd"]
        cmds = parser_mod.parse_command_list(tokens, self.state)
        self.assertEqual(2, len(cmds))  # A=1 returns None
        self.assertEqual("echo", cmds[0].name)
        self.assertEqual(["1"], cmds[0].args)
        self.assertEqual("pwd", cmds[1].name)

    # Test for parse_top_level
    def test_parse_top_level_returns_command_nodes(self):
        def dummy_exec(cmd, state):
            return 0

        nodes = parser_mod.parse_top_level(["echo", "hi", ";", "pwd"], self.state, dummy_exec)
        self.assertEqual(2, len(nodes))
        self.assertTrue(all(isinstance(n, CommandNode) for n in nodes))


if __name__ == "__main__":
    unittest.main()
