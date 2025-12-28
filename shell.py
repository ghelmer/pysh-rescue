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
