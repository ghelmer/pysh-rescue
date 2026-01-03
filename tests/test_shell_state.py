import os
import unittest
from unittest.mock import patch

from shell_state import ShellState


class TestShellState(unittest.TestCase):
    def setUp(self):
        self.state = ShellState()

    def test_set_and_get_shell_var(self):
        self.state.set_var("X", "123")
        self.assertEqual(self.state.get_var("X"), "123")

    def test_get_falls_back_to_environment(self):
        with patch.dict(os.environ, {"ENVX": "abc"}, clear=False):
            self.assertEqual(self.state.get_var("ENVX"), "abc")

    def test_shell_var_overrides_environment(self):
        with patch.dict(os.environ, {"X": "env"}, clear=False):
            self.state.set_var("X", "shell")
            self.assertEqual(self.state.get_var("X"), "shell")

    def test_export_sets_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            self.state.set_var("X", "999", export=True)
            self.assertEqual(os.environ.get("X"), "999")
            self.assertEqual(self.state.get_var("X"), "999")

    def test_get_unset_returns_empty_string(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(self.state.get_var("MISSING"), "")

    # -------------------------
    # interpolate
    # -------------------------
    def test_interpolate_simple(self):
        self.state.set_var("X", "hi")
        self.assertEqual("say:hi", self.state.interpolate("say:$X"))

    def test_interpolate_multiple_vars(self):
        self.state.set_var("A", "1")
        self.state.set_var("B", "2")
        self.assertEqual("1+2", self.state.interpolate("$A+$B"))

    def test_interpolate_unset_var_becomes_empty(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual("x=", self.state.interpolate("x=$NOPE"))

    def test_interpolate_underscore_and_digits(self):
        self.state.set_var("A_1", "ok")
        self.assertEqual("ok!", self.state.interpolate("$A_1!"))

    def test_interpolate_dollar_at_end(self):
        # "$" alone yields empty substitution name -> get_var("") -> "" with current implementation
        self.assertEqual("ends$", self.state.interpolate("ends$"))

    def test_interpolate_dollar_followed_by_non_name_char(self):
        # "$-" => name = "" then "-" copied normally
        self.assertEqual("x$-y", self.state.interpolate("x$-y"))

    def test_interpolate_adjacent_text(self):
        self.state.set_var("X", "Z")
        self.assertEqual("AZB", self.state.interpolate("A${X}B"))

    def test_interpolate_env_fallback(self):
        with patch.dict(os.environ, {"ENVY": "yes"}, clear=False):
            self.assertEqual("ok:yes", self.state.interpolate("ok:$ENVY"))

    def test_interpolate_dollar_at_end_literal(self):
        self.assertEqual("ends$", self.state.interpolate("ends$"))

    def test_interpolate_dollar_followed_by_non_name_char_literal(self):
        self.assertEqual("x$-y", self.state.interpolate("x$-y"))

    def test_interpolate_double_dollar_literal(self):
        self.assertEqual("$$", self.state.interpolate("$$"))

    def test_interpolate_dollar_question_mark(self):
        self.state.set_status(7)
        self.assertEqual(self.state.interpolate("rc=$?"), "rc=7")

    def test_interpolate_dollar_question_mark_adjacent_text(self):
        self.state.set_status(42)
        self.assertEqual(self.state.interpolate("A$?B"), "A42B")

    def test_interpolate_dollar_question_mark_default_zero(self):
        # default last_status is 0
        self.assertEqual(self.state.interpolate("$?"), "0")

if __name__ == "__main__":
    unittest.main()
