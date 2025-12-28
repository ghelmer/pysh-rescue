""" Implement the core of the shell. """
import contextlib
import glob
import shlex
import subprocess
import sys

from commandnode import CommandNode
from executable import Executable
from shell_builtins import BUILTINS
from command import Command
from exceptions import ShellExit
from shell_state import ShellState
from block_reader import read_until_fi
from if_parser import parse_if_to_node


# Import builtin modules to register them
import builtin_cd
import builtin_echo
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


def tokenize(line: str) -> list[str]:
    """ Tokenize a line of shell command. """
    lex = shlex.shlex(line, punctuation_chars=";&><")
    return [lex.get_token()]


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
    tokens = [state.interpolate(tok) for tok in tokens]
    tokens = expand_globs(tokens)

    stdout = None
    append = False
    args = []

    it = iter(tokens)
    for tok in it:
        if tok == ">":
            stdout = next(it)
        elif tok == ">>":
            stdout = next(it)
            append = True
        else:
            args.append(tok)

    if not args:
        return None

    return Command(args[0], args[1:], stdout, append)


def parse_command_list(tokens: list[str], state: ShellState) -> list[Command]:
    command_tokens = split_on_semicolons(tokens)
    return [parse_simple_command(cmd, state) for cmd in command_tokens]


def parse_top_level(tokens: list[str], state: ShellState) -> list[Executable]:
    if not tokens:
        return []

    if tokens[0] == "if":
        return [parse_if_to_node(tokens, state, parse_command_list, )]  # you implement this wrapper

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
                tokens = tokenize(line)

                # if-block handling needs to read more lines BEFORE parsing
                if tokens and tokens[0] == "if":
                    block_lines = [line] + read_until_fi(read_command)
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
