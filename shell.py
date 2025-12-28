""" Implement the core of the shell. """
import contextlib
import glob
import re
import shlex
import subprocess
import sys

from command import CommandNode, Executable
from shell_builtins import BUILTINS
from command import Command
from exceptions import ShellExit
from shell_state import ShellState
from if_parser import parse_if_to_node

# Import builtin modules to register them
import builtin_ls

GLOB_CHARS = set("*?[")

def expand_globs(tokens):
    """ Expand glob expressions. """
    expanded = []

    for token in tokens:
        if any(c in token for c in GLOB_CHARS):
            matches = glob.glob(token)
            if matches:
                expanded.extend(sorted(matches))
            else:
                # POSIX behavior: leave token unchanged
                expanded.append(token)
        else:
            expanded.append(token)

    return expanded


def if_nesting_delta(tokens: list[str]) -> int:
    """ Check to see if a `fi` is in this line. """
    at_cmd_start = True
    delta = 0
    for tok in tokens:
        if tok == ";":
            at_cmd_start = True
            continue
        if at_cmd_start:
            if tok == "if":
                delta += 1
            elif tok == "fi":
                delta -= 1
            at_cmd_start = False
    return delta


def read_until_fi(read_func):
    """
    Read lines until 'fi' is encountered, tracking nesting.
    Uses the provided read_func which handles continuation.
    Returns list of complete logical lines.
    """
    lines = []
    nesting = 1

    while nesting > 0:
        line = read_func(prompt="> ")
        lines.append(line)

        try:
            toks = tokenize(line)

            at_cmd_start = True
            for tok in toks:
                if tok == ";":
                    at_cmd_start = True
                    continue

                if at_cmd_start:
                    if tok == "if":
                        nesting += 1
                    elif tok == "fi":
                        nesting -= 1
                    at_cmd_start = False
                else:
                    # still within command args
                    pass

        except ValueError:
            pass

    return lines


def read_command(prompt="$ "):
    """ Read a command with support for line continuation. """
    lines = []
    while True:
        line = input(prompt)
        if line.endswith("\\"):
            lines.append(line[:-1])
            prompt = "> "
        else:
            lines.append(line)
            break
    return "".join(lines)


def tokenize(line: str) -> list[str]:
    lex = shlex.shlex(line, posix=True, punctuation_chars=";&><|")
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)

    result = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i] in (">", "<", "&", "|") and tokens[i] == tokens[i + 1]:
            result.append(tokens[i] * 2)  # >>, <<, &&, ||
            i += 2
        else:
            result.append(tokens[i])
            i += 1
    return result


VAR_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

def is_assignment_token(tok: str) -> bool:
    """ Return True if tok looks like NAME=value with a valid NAME. """
    if "=" not in tok or tok.startswith("="):
        return False
    name, _ = tok.split("=", 1)
    return bool(VAR_NAME_RX.match(name))


def split_on_semicolons(tokens: list[str]):
    """ Split commands where semicolon tokens are found. """
    commands = []
    current = []

    for tok in tokens:
        if tok == ";":
            if current:
                commands.append(current)
                current = []
        else:
            current.append(tok)

    if current:
        commands.append(current)

    return commands


def parse_simple_command(tokens: list[str], state: ShellState) -> Command|None:
    """ Parse a simple shell command. """
    if not tokens:
        return None

    # Handle variable assignments as a pre-command step.
    # Supports: NAME=value
    # Also supports multiple leading assignments: A=1 B=2 cmd ...
    idx = 0
    while idx < len(tokens) and is_assignment_token(tokens[idx]):
        name, value = tokens[idx].split("=", 1)
        # Store raw value; interpolation happens when used ($NAME)
        state.set_var(name, value, export=False)
        idx += 1

    # If the line was only assignments, there's no command to execute.
    if idx >= len(tokens):
        return None
    tokens = tokens[idx:]

    tokens = [state.interpolate(tok) for tok in tokens]
    tokens = expand_globs(tokens)

    stdout = None
    append = False
    args = []

    it = iter(tokens)
    for tok in it:
        if tok == ">":
            stdout = next(it, None)
            if stdout is None:
                raise SyntaxError("syntax error: expected filename after '>'")
        elif tok == ">>":
            stdout = next(it, None)
            if stdout is None:
                raise SyntaxError("syntax error: expected filename after '>>'")
            append = True
        else:
            args.append(tok)

    if not args:
        return None

    return Command(args[0], args[1:], stdout, append)


def parse_command_list(tokens: list[str], state: ShellState) -> list[Command]:
    command_tokens = split_on_semicolons(tokens)
    cmds = []
    for cmd_tokens in command_tokens:
        cmd = parse_simple_command(cmd_tokens, state)
        if cmd is not None:
            cmds.append(cmd)
    return cmds


def parse_top_level(tokens: list[str], state: ShellState) -> list[Executable]:
    if not tokens:
        return []
    cmds = parse_command_list(tokens, state)
    return [CommandNode(c, execute_command) for c in cmds]


@contextlib.contextmanager
def redirect_stdout(filename, append):
    if filename is None:
        yield
        return

    mode = "a" if append else "w"
    with open(filename, mode) as f:
        old_stdout = sys.stdout
        sys.stdout = f
        try:
            yield
        finally:
            sys.stdout = old_stdout


def execute_command(cmd: Command, shell_state: ShellState) -> int:
    # Builtins: keep Python-level stdout redirection
    if cmd.name in BUILTINS:
        with redirect_stdout(cmd.stdout, cmd.append):
            return BUILTINS[cmd.name](cmd.args, shell_state) or 0

    # External commands: redirect via subprocess stdout
    stdout_handle = None
    try:
        if cmd.stdout is not None:
            mode = "a" if cmd.append else "w"
            stdout_handle = open(cmd.stdout, mode)

        completed = subprocess.run(
            [cmd.name] + cmd.args,
            stdout=stdout_handle if stdout_handle else None,
        )
        return completed.returncode
    except FileNotFoundError:
        # This should go to stderr ideally; print is OK for now
        print(f"{cmd.name}: command not found")
        return 127
    finally:
        if stdout_handle:
            stdout_handle.close()


class Shell:
    def __init__(self):
        self.state = ShellState()

    def run(self):
        while True:
            try:
                line = read_command()
                tokens = tokenize(line)

                # if-block handling needs to read more lines BEFORE parsing
                if tokens and tokens[0] == "if":
                    nesting = if_nesting_delta(tokens)
                    block_lines = [line]
                    if nesting > 0:
                        block_lines += read_until_fi(read_command)
                    block_text = " ; ".join(block_lines)
                    block_tokens = tokenize(block_text)
                    nodes = [parse_if_to_node(block_tokens, parse_command_list, execute_command)]
                else:
                    nodes = parse_top_level(tokens, self.state)

                for node in nodes:
                    node.execute(self.state)
            except ShellExit as e:
                return e.status

            except EOFError:
                print()
                return 0

            except KeyboardInterrupt:
                print()
