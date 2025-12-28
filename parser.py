""" Parse shell commands. """
import glob

from command import Command, Executable, CommandNode
from constants import GLOB_CHARS, VAR_NAME_RX
from shell_state import ShellState


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


def parse_top_level(tokens: list[str], state: ShellState, executor) -> list[Executable]:
    if not tokens:
        return []
    cmds = parse_command_list(tokens, state)
    return [CommandNode(c, executor) for c in cmds]
