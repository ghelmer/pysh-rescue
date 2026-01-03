import unittest
from unittest.mock import patch, MagicMock

import shell
from exceptions import ShellExit
from shell_state import ShellState


class TestShellHelpers(unittest.TestCase):
    def test_if_nesting_delta_simple_if_fi(self):
        self.assertEqual(0, shell.if_nesting_delta(["if", "x", ";", "then", "y", ";", "fi"]))

    def test_if_nesting_delta_if_without_fi(self):
        self.assertEqual(1, shell.if_nesting_delta(["if", "x", "then", "y"]))

    def test_if_nesting_delta_nested(self):
        # if ... ; if ... ; fi ; fi
        toks = ["if", "a", "then", "b", ";", "if", "c", "then", "d", ";", "fi", ";", "fi"]
        self.assertEqual(0, shell.if_nesting_delta(toks))

    def test_if_nesting_delta_ignores_if_in_args(self):
        # command: echo if  (should not count)
        self.assertEqual(0, shell.if_nesting_delta(["echo", "if"]))

    def test_if_nesting_delta_recognizes_if_after_semicolon(self):
        # echo hi ; if ...
        self.assertEqual(1, shell.if_nesting_delta(["echo", "hi", ";", "if", "x"]))


class TestReadCommand(unittest.TestCase):
    def test_read_command_no_continuation(self):
        with patch("builtins.input", side_effect=["echo hi"]):
            self.assertEqual(shell.read_command(), "echo hi")

    def test_read_command_with_continuation(self):
        # First line ends with backslash so prompt becomes "> "
        with patch("builtins.input", side_effect=["echo \\", "hi"]):
            self.assertEqual("echo hi", shell.read_command())


class TestReadUntilFi(unittest.TestCase):
    @patch.object(shell, "tokenize")
    def test_read_until_fi_reads_until_fi_at_command_start(self, mock_tokenize):
        # Simulate 2 lines:
        #   echo hi
        #   fi
        mock_tokenize.side_effect = [
            ["echo", "hi"],
            ["fi"]
        ]

        def fake_read(prompt="$ "):
            # prompt should be "> " within read_until_fi
            return fake_read.lines.pop(0)
        fake_read.lines = ["echo hi", "fi"]

        lines = shell.read_until_fi(fake_read)
        self.assertEqual(["echo hi", "fi"], lines)

    @patch.object(shell, "tokenize")
    def test_read_until_fi_nested_if(self, mock_tokenize):
        # Lines:
        #   if x then
        #   fi
        #   fi
        mock_tokenize.side_effect = [
            ["if", "x", "then"],
            ["fi"],
            ["fi"]
        ]

        def fake_read(prompt="$ "):
            return fake_read.lines.pop(0)
        fake_read.lines = ["if x then", "fi", "fi"]

        lines = shell.read_until_fi(fake_read)
        self.assertEqual(["if x then", "fi", "fi"], lines)

    @patch.object(shell, "tokenize")
    def test_read_until_fi_does_not_count_if_in_args(self, mock_tokenize):
        # echo if  (if is an arg, should not change nesting)
        # fi       (ends)
        mock_tokenize.side_effect = [
            ["echo", "if"],
            ["fi"]
        ]

        def fake_read(prompt="$ "):
            return fake_read.lines.pop(0)
        fake_read.lines = ["echo if", "fi"]

        lines = shell.read_until_fi(fake_read)
        self.assertEqual(["echo if", "fi"], lines)


class TestShellRun(unittest.TestCase):
    def setUp(self):
        self.shell = shell.Shell()
        self.shell.state = ShellState()

    def test_run_executes_nodes_for_non_if(self):
        # Arrange: read_command returns one command then EOFError to exit
        with patch.object(shell, "read_command", side_effect=["echo hi", EOFError]):
            with patch.object(shell, "tokenize", return_value=["echo", "hi"]) as mock_tokenize:
                # parse_top_level returns mock nodes
                n1 = MagicMock()
                n2 = MagicMock()
                with patch.object(shell, "parse_top_level", return_value=[n1, n2]) as mock_parse:
                    rc = self.shell.run()

        self.assertEqual(0, rc)
        mock_tokenize.assert_called()  # tokenized the line
        mock_parse.assert_called_once()
        n1.execute.assert_called_once_with(self.shell.state)
        n2.execute.assert_called_once_with(self.shell.state)

    def test_run_if_one_liner_does_not_call_read_until_fi(self):
        # if ... fi on one line
        line = "if true; then echo hi; fi"

        with patch.object(shell, "read_command", side_effect=[line, EOFError]):
            with patch.object(shell, "tokenize") as mock_tokenize:
                # First tokenize(line) makes tokens[0] == "if"
                # Second tokenize(block_text) for block_tokens
                mock_tokenize.side_effect = [
                    ["if", "true", ";", "then", "echo", "hi", ";", "fi"],  # tokens for line
                    ["if", "true", ";", "then", "echo", "hi", ";", "fi"],  # tokens for block_text
                ]

                with patch.object(shell, "read_until_fi") as mock_read_until:
                    node = MagicMock()
                    with patch.object(shell, "parse_if_to_node", return_value=node) as mock_parse_if:
                        rc = self.shell.run()

        self.assertEqual(0, rc)
        mock_read_until.assert_not_called()
        mock_parse_if.assert_called_once()
        node.execute.assert_called_once_with(self.shell.state)

    def test_run_if_multiline_calls_read_until_fi_and_joins_with_semicolons(self):
        first = "if true; then"
        rest_lines = ["echo hi", "fi"]

        with patch.object(shell, "read_command", side_effect=[first, EOFError]):
            # tokens for first line cause nesting > 0 so it reads more
            with patch.object(shell, "tokenize") as mock_tokenize:
                # 1) tokenize(first) => starts with "if" and no "fi" => nesting > 0
                # 2) tokenize(block_text) => block tokens after join
                mock_tokenize.side_effect = [
                    ["if", "true", ";", "then"],
                    ["if", "true", ";", "then", ";", "echo", "hi", ";", "fi"],
                ]

                with patch.object(shell, "read_until_fi", return_value=rest_lines) as mock_read_until:
                    node = MagicMock()
                    with patch.object(shell, "parse_if_to_node", return_value=node) as mock_parse_if:
                        rc = self.shell.run()

        self.assertEqual(rc, 0)
        mock_read_until.assert_called_once()
        # Ensure block_text got joined with " ; "
        # parse_if_to_node is called with block_tokens from tokenize(block_text)
        args, kwargs = mock_parse_if.call_args
        block_tokens = args[0]
        self.assertEqual(["if", "true", ";", "then", ";", "echo", "hi", ";", "fi"], block_tokens)
        node.execute.assert_called_once_with(self.shell.state)

    def test_run_returns_shell_exit_status(self):
        # Make node.execute raise ShellExit(7)
        n = MagicMock()
        n.execute.side_effect = ShellExit(7)

        with patch.object(shell, "read_command", side_effect=["echo hi"]):
            with patch.object(shell, "tokenize", return_value=["echo", "hi"]):
                with patch.object(shell, "parse_top_level", return_value=[n]):
                    rc = self.shell.run()

        self.assertEqual(7, rc)

    def test_run_keyboard_interrupt_continues(self):
        # First read_command raises KeyboardInterrupt, then EOFError to exit
        with patch.object(shell, "read_command", side_effect=[KeyboardInterrupt, EOFError]):
            rc = self.shell.run()
        self.assertEqual(0, rc)

    def test_shell_run_updates_last_status(self):
        sh = shell.Shell()

        # Make a node that returns a non-zero status
        n1 = MagicMock()
        n1.execute.return_value = 3
        # then a node that returns 0
        n2 = MagicMock()
        n2.execute.return_value = 0

        with patch.object(shell, "read_command", side_effect=["echo hi", EOFError]), \
             patch.object(shell, "tokenize", return_value=["echo", "hi"]), \
             patch.object(shell, "parse_top_level", return_value=[n1, n2]):

            rc = sh.run()

        self.assertEqual(rc, 0)               # shell returns 0 on EOF
        self.assertEqual(sh.state.last_status, 0)  # last executed node was 0


if __name__ == "__main__":
    unittest.main()
