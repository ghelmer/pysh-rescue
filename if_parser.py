""" Parse if/then/elif/else/fi blocks properly. """

from command import Executable
from shell_state import ShellState


class IfStatement:
    """ Represents an if/then/elif/else/fi block. """
    def __init__(self):
        self.branches: list[tuple[list[str], list[str]]] = []
        self.else_body: list[str] = []

    def add_branch(self, condition_tokens, body_tokens):
        self.branches.append((condition_tokens, body_tokens))

    def set_else_body(self, body_tokens):
        self.else_body = body_tokens


class IfNode(Executable):
    """ Implement if/then/elif/else/fi blocks as an executable node. """
    def __init__(self, stmt: IfStatement, parse_command_list, executor):
        self.stmt = stmt
        self.parse_command_list = parse_command_list
        self.executor = executor  # e.g., execute_command

    def execute(self, state: ShellState) -> int:
        # Evaluate each condition branch in order.
        for cond_tokens, body_tokens in self.stmt.branches:
            # "condition" is a command list too (often just one command)
            cond_cmds = self.parse_command_list(cond_tokens, state)
            status = 0
            for c in cond_cmds:
                status = self.executor(c, state) or 0

            if status == 0:  # shell convention: 0 = true
                body_cmds = self.parse_command_list(body_tokens, state)
                for c in body_cmds:
                    status = self.executor(c, state) or 0
                return status

        # Else branch if no condition matched
        if self.stmt.else_body:
            status = 0
            else_cmds = self.parse_command_list(self.stmt.else_body, state)
            for c in else_cmds:
                status = self.executor(c, state) or 0
            return status

        return 0


KEYWORDS = {"if", "then", "elif", "else", "fi"}

def _consume_until(tokens: list[str], i: int, stop_words: set[str]) -> tuple[list[str], int]:
    """Consume tokens until the next token is in stop_words (not consuming stop token)."""
    out = []
    while i < len(tokens) and tokens[i] not in stop_words:
        out.append(tokens[i])
        i += 1
    return out, i


def _strip_leading_semicolons(tokens: list[str], i: int) -> int:
    while i < len(tokens) and tokens[i] == ";":
        i += 1
    return i


def parse_if_tokens(block_tokens: list[str]) -> IfStatement:
    """
    Parse: if <cond> then <body> (elif <cond> then <body>)* (else <body>)? fi
    All parts are token lists (may include ';').
    """
    tokens = block_tokens
    i = 0
    stmt = IfStatement()

    if i >= len(tokens) or tokens[i] != "if":
        raise SyntaxError("if block must start with 'if'")
    i += 1

    # IF condition: tokens until 'then'
    cond, i = _consume_until(tokens, i, {"then"})
    if i >= len(tokens) or tokens[i] != "then":
        raise SyntaxError("missing 'then'")
    i += 1

    # IF body: until elif/else/fi
    body, i = _consume_until(tokens, i, {"elif", "else", "fi"})
    stmt.add_branch(cond, body)

    # ELIF branches
    while i < len(tokens) and tokens[i] == "elif":
        i += 1
        cond, i = _consume_until(tokens, i, {"then"})
        if i >= len(tokens) or tokens[i] != "then":
            raise SyntaxError("missing 'then' after 'elif'")
        i += 1
        body, i = _consume_until(tokens, i, {"elif", "else", "fi"})
        stmt.add_branch(cond, body)

    # ELSE
    if i < len(tokens) and tokens[i] == "else":
        i += 1
        else_body, i = _consume_until(tokens, i, {"fi"})
        stmt.set_else_body(else_body)

    # FI
    if i >= len(tokens) or tokens[i] != "fi":
        raise SyntaxError("missing 'fi'")
    i += 1

    # Optional: allow trailing semicolons after fi
    i = _strip_leading_semicolons(tokens, i)

    if i != len(tokens):
        # Could be extra tokens after fi, decide if you want to allow that
        raise SyntaxError(f"unexpected tokens after fi: {tokens[i:]}")

    return stmt


def parse_if_to_node(block_tokens: list[str], parse_command_list, executor) -> Executable:
    """ Parse if/then/elif/else/fi blocks properly. """
    stmt = parse_if_tokens(block_tokens)
    return IfNode(stmt, parse_command_list, executor)
