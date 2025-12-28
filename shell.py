""" Implement the core of the shell. """
import contextlib
import glob
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
