""" Implement the core of the shell. """
import contextlib
import glob
import shlex
import subprocess
import sys

from shell_builtins import BUILTINS
from command import Command
from exceptions import ShellExit
from shell_state import ShellState
from block_reader import read_until_fi
from if_parser import parse_if_statement
from if_executor import execute_if_statement


# Import builtin modules to register them
import builtin_cd
import builtin_exit
import builtin_pwd
import builtin_ls
import builtin_test

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


def split_on_semicolon(line):
    """
    Split a line into multiple commands separated by semicolons.
    Respects quoting - semicolons inside quotes are not separators.

    Returns:  List of command strings
    """
    commands = []
    current = []

    # Use shlex to tokenize, which respects quotes
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = False
    lexer.whitespace = ' \t\r\n'  # Don't treat ; as whitespace

    for token in lexer:
        if token == ';':
            # End of command
            if current:
                commands.append(' '.join(current))
                current = []
        else:
            current.append(token)

    # Don't forget the last command
    if current:
        commands.append(' '.join(current))

    return commands


def parse_command(line, state):
    tokens = shlex.split(line)

    tokens = [state.interpolate(tok) for tok in tokens]
    tokens = expand_globs(tokens)

    stdout = None
    append = False
    cleaned = []

    it = iter(tokens)
    for tok in it:
        if tok == ">":
            stdout = next(it)
        elif tok == ">>":
            stdout = next(it)
            append = True
        else:
            cleaned.append(tok)

    if not cleaned:
        return None

    return Command(cleaned[0], cleaned[1:], stdout, append)


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


def execute_command(cmd: Command, shell_state: ShellState):
    with redirect_stdout(cmd.stdout, cmd.append):
        if cmd.name in BUILTINS:
            return BUILTINS[cmd.name](cmd.args, shell_state)

        try:
            subprocess.run([cmd.name] + cmd.args)
        except FileNotFoundError:
            print(f"{cmd.name}: command not found")


class Shell:
    def __init__(self):
        self.state = ShellState()

    def run(self):
        while True:
            try:
                line = read_command()

                # Tokenize to check for control flow keywords
                try:
                    tokens = shlex.split(line)
                except ValueError:
                    tokens = []

                if tokens and tokens[0] == "if":
                    # Read entire block (respects continuation in each line)
                    block_lines = [line] + read_until_fi(read_command)
                    # Parse structure (respects quoting)
                    stmt = parse_if_statement(block_lines)
                    # Execute (defers all interpolation/expansion until needed)
                    execute_if_statement(stmt, self.state, parse_command, execute_command, split_on_semicolon)

                else:
                    cmd = parse_command(line, self.state)
                    if cmd:
                        execute_command(cmd, self.state)

            except ShellExit as e:
                return e.status

            except EOFError:
                print()
                return 0

            except KeyboardInterrupt:
                print()
