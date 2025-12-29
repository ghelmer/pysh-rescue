""" Parse shell commands. """
import glob

from command import Command, Executable, CommandNode
from constants import GLOB_CHARS, VAR_NAME_RX, REDIR_COMBINED_RX
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

    stdin = None
    stdout = None
    append = False
    stderr = None
    stderr_append = False
    redirect_both = False

    def require_filename(next_tok, msg):
        if next_tok is None or next_tok == "":
            raise SyntaxError(msg)
        return next_tok

    args = []
    i = 0

    while i < len(tokens):
        tok = tokens[i]
        # --- handle plain operators <, >, >>
        if tok == "<":
            i += 1
            stdin = require_filename(tokens[i] if i < len(tokens) else None,
                                     "syntax error: expected filename after '<'")
            i += 1
            continue
        if tok in (">", ">>"):
            i += 1
            filename = require_filename(tokens[i] if i < len(tokens) else None,
                                        f"syntax error: expected filename after '{tok}'")
            stdout = filename
            append = (tok == ">>")
            i += 1
            continue

        # --- handle spaced fd redirection: 2 > file or 2 >> file
        if tok.isdigit() and i + 1 < len(tokens) and tokens[i + 1] in (">", ">>"):
            fd = tok
            op = tokens[i + 1]
            i += 2
            filename = require_filename(tokens[i] if i < len(tokens) else None,
                                        f"syntax error: expected filename after '{fd}{op}'")
            if fd == "2":
                stderr = filename
                stderr_append = (op == ">>")
            elif fd == "1":
                stdout = filename
                append = (op == ">>")
            else:
                # optional: treat other fds as error for now
                raise SyntaxError(f"unsupported fd redirection: {fd}{op}")
            i += 1
            continue

        # --- handle combined tokens: 2>file, 2>>file, &>file, &>>file
        m = REDIR_COMBINED_RX.match(tok)
        if m:
            fd = m.group("fd")  # "2" or "&" etc.
            op = m.group("op")  # ">" or ">>"
            rest = m.group("rest")  # maybe filename, maybe empty

            # filename may be in the same token (2>file) or next token (2> file)
            if rest:
                filename = rest
                i += 1
            else:
                i += 1
                filename = require_filename(tokens[i] if i < len(tokens) else None,
                                            f"syntax error: expected filename after '{fd}{op}'")
                i += 1

            if fd == "&":
                redirect_both = True
                stdout = filename
                append = (op == ">>")
                stderr = filename
                stderr_append = (op == ">>")
            elif fd == "2":
                stderr = filename
                stderr_append = (op == ">>")
            elif fd == "1":
                stdout = filename
                append = (op == ">>")
            else:
                raise SyntaxError(f"unsupported fd redirection: {fd}{op}")

            continue

        # normal arg
        args.append(tok)
        i += 1

    if not args:
        return None

    return Command(
        args[0],
        args[1:],
        stdin=stdin,
        stdout=stdout,
        append=append,
        stderr=stderr,
        stderr_append=stderr_append,
        redirect_both=redirect_both,
    )

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
