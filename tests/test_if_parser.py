import unittest

import if_parser
from shell_state import ShellState


class TestIfParserParsing(unittest.TestCase):
    def test_parse_simple_if(self):
        tokens = ["if", "test", "x", "then", "echo", "ok", "fi"]
        stmt = if_parser.parse_if_tokens(tokens)

        self.assertEqual(1, len(stmt.branches))
        cond, body = stmt.branches[0]
        self.assertEqual(["test", "x"], cond)
        self.assertEqual(["echo", "ok"], body)
        self.assertEqual([], stmt.else_body)

    def test_parse_if_with_else(self):
        tokens = ["if", "cond", "then", "a", "else", "b", "fi"]
        stmt = if_parser.parse_if_tokens(tokens)

        self.assertEqual(1, len(stmt.branches))
        self.assertEqual(["cond"], stmt.branches[0][0])
        self.assertEqual(["a"], stmt.branches[0][1])
        self.assertEqual(["b"], stmt.else_body)

    def test_parse_if_with_elif(self):
        tokens = [
            "if", "c1", "then", "b1",
            "elif", "c2", "then", "b2",
            "fi"
        ]
        stmt = if_parser.parse_if_tokens(tokens)

        self.assertEqual(2, len(stmt.branches))
        self.assertEqual(["c1"], stmt.branches[0][0])
        self.assertEqual(["b1"], stmt.branches[0][1])
        self.assertEqual(["c2"], stmt.branches[1][0])
        self.assertEqual(["b2"], stmt.branches[1][1])
        self.assertEqual([], stmt.else_body)

    def test_parse_if_with_elif_and_else(self):
        tokens = [
            "if", "c1", "then", "b1",
            "elif", "c2", "then", "b2",
            "else", "b3",
            "fi"
        ]
        stmt = if_parser.parse_if_tokens(tokens)

        self.assertEqual(2, len(stmt.branches))
        self.assertEqual(["b3"], stmt.else_body)

    def test_trailing_semicolons_after_fi_allowed(self):
        tokens = ["if", "c", "then", "b", "fi", ";", ";"]
        stmt = if_parser.parse_if_tokens(tokens)
        self.assertEqual(1, len(stmt.branches))

    def test_must_start_with_if(self):
        with self.assertRaises(SyntaxError):
            if_parser.parse_if_tokens(["echo", "hi"])

    def test_missing_then(self):
        with self.assertRaises(SyntaxError):
            if_parser.parse_if_tokens(["if", "cond", "echo", "hi", "fi"])

    def test_missing_fi(self):
        with self.assertRaises(SyntaxError):
            if_parser.parse_if_tokens(["if", "cond", "then", "body"])

    def test_unexpected_tokens_after_fi(self):
        with self.assertRaises(SyntaxError):
            if_parser.parse_if_tokens(["if", "c", "then", "b", "fi", "oops"])

    def test_missing_then_after_elif(self):
        with self.assertRaises(SyntaxError):
            if_parser.parse_if_tokens(["if", "c1", "then", "b1", "elif", "c2", "b2", "fi"])


class TestIfNodeExecution(unittest.TestCase):
    def setUp(self):
        self.state = ShellState()

    def test_first_branch_true_executes_body_only(self):
        # if true; then body; elif ...; else ...; fi

        # parse_command_list returns a list of "commands" (here: dicts) representing each token list
        def fake_parse_command_list(tokens, state):
            return [{"tokens": tokens}] if tokens else []

        calls = []
        # executor returns status based on first token of condition
        def fake_executor(cmd, state):
            calls.append(cmd["tokens"])
            # Condition convention in this test:
            # tokens starting with "true" => status 0
            # tokens starting with "false" => status 1
            t = cmd["tokens"]
            if t and t[0] == "true":
                return 0
            if t and t[0] == "false":
                return 1
            return 0

        stmt = if_parser.IfStatement()
        stmt.add_branch(["true"], ["echo", "A"])
        stmt.add_branch(["true"], ["echo", "B"])   # should never be evaluated
        stmt.set_else_body(["echo", "ELSE"])       # should never run

        node = if_parser.IfNode(stmt, fake_parse_command_list, fake_executor)
        rc = node.execute(self.state)

        self.assertEqual(0, rc)

        # Calls should include: condition tokens of first branch, then body tokens of first branch
        self.assertEqual([["true"], ["echo", "A"]], calls)

    def test_first_branch_false_second_true(self):
        def fake_parse_command_list(tokens, state):
            return [{"tokens": tokens}] if tokens else []

        calls = []
        def fake_executor(cmd, state):
            calls.append(cmd["tokens"])
            t = cmd["tokens"]
            if t and t[0] == "true":
                return 0
            if t and t[0] == "false":
                return 1
            return 0

        stmt = if_parser.IfStatement()
        stmt.add_branch(["false"], ["echo", "A"])
        stmt.add_branch(["true"], ["echo", "B"])
        stmt.set_else_body(["echo", "ELSE"])

        node = if_parser.IfNode(stmt, fake_parse_command_list, fake_executor)
        rc = node.execute(self.state)

        self.assertEqual(0, rc)
        # Expected evaluation order:
        # cond1, cond2, body2
        self.assertEqual([["false"], ["true"], ["echo", "B"]], calls)

    def test_else_runs_when_all_false(self):
        def fake_parse_command_list(tokens, state):
            return [{"tokens": tokens}] if tokens else []

        calls = []
        def fake_executor(cmd, state):
            calls.append(cmd["tokens"])
            t = cmd["tokens"]
            if t and t[0] == "false":
                return 1
            return 0

        stmt = if_parser.IfStatement()
        stmt.add_branch(["false"], ["echo", "A"])
        stmt.add_branch(["false"], ["echo", "B"])
        stmt.set_else_body(["echo", "ELSE"])

        node = if_parser.IfNode(stmt, fake_parse_command_list, fake_executor)
        rc = node.execute(self.state)

        self.assertEqual(0, rc)
        self.assertEqual([["false"], ["false"], ["echo", "ELSE"]], calls)

    def test_returns_last_body_command_status(self):
        # Ensure the node returns the last executed body's return code
        def fake_parse_command_list(tokens, state):
            # Make body contain 2 "commands"
            if tokens == ["body"]:
                return [{"tokens": ["cmd1"]}, {"tokens": ["cmd2"]}]
            return [{"tokens": tokens}] if tokens else []

        def fake_executor(cmd, state):
            # cmd1 returns 0, cmd2 returns 7
            if cmd["tokens"] == ["cmd1"]:
                return 0
            if cmd["tokens"] == ["cmd2"]:
                return 7
            if cmd["tokens"] == ["true"]:
                return 0
            return 0

        stmt = if_parser.IfStatement()
        stmt.add_branch(["true"], ["body"])

        node = if_parser.IfNode(stmt, fake_parse_command_list, fake_executor)
        rc = node.execute(self.state)

        self.assertEqual(7, rc)


if __name__ == "__main__":
    unittest.main()
