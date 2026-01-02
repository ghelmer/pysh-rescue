""" Execute a shell command. """
import contextlib
import subprocess
import sys

from command import Command
from shell_builtins import BUILTINS
from shell_state import ShellState


@contextlib.contextmanager
def redirect_stdin(filename):
    if filename is None:
        yield
        return

    with open(filename, "r") as f:
        old_stdin = sys.stdin
        sys.stdin = f
        try:
            yield
        finally:
            sys.stdin = old_stdin


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


@contextlib.contextmanager
def redirect_stderr(filename, append):
    if filename is None:
        yield
        return

    mode = "a" if append else "w"
    with open(filename, mode) as f:
        old = sys.stderr
        sys.stderr = f
        try:
            yield
        finally:
            sys.stderr = old


def execute_command(cmd: Command, shell_state: ShellState) -> int:
    # Builtins: keep Python-level stdin & stdout redirection
    if cmd.name in BUILTINS:
        if cmd.redirect_both and cmd.stdout:
            mode = "a" if cmd.append else "w"
            with open(cmd.stdout, mode) as f:
                old_out, old_err = sys.stdout, sys.stderr
                try:
                    sys.stdout = f
                    sys.stderr = f
                    with redirect_stdin(cmd.stdin):
                        return BUILTINS[cmd.name](cmd.args, shell_state) or 0
                finally:
                    sys.stdout, sys.stderr = old_out, old_err
        with redirect_stdin(cmd.stdin):
            with redirect_stdout(cmd.stdout, cmd.append):
                with redirect_stderr(cmd.stderr, cmd.stderr_append):
                    return BUILTINS[cmd.name](cmd.args, shell_state) or 0

    # External commands: redirect via subprocess
    stdout_handle = None
    stderr_handle = None
    stdin_handle = None
    both_handle = None
    try:
        if cmd.stdin is not None:
            stdin_handle = open(cmd.stdin, "r")

        if cmd.redirect_both and cmd.stdout:
            mode = "a" if cmd.append else "w"
            both_handle = open(cmd.stdout, mode)
            stdout_handle = both_handle
            stderr_handle = both_handle
        else:
            if cmd.stdout:
                mode = "a" if cmd.append else "w"
                stdout_handle = open(cmd.stdout, mode)
            if cmd.stderr:
                mode = "a" if cmd.stderr_append else "w"
                stderr_handle = open(cmd.stderr, mode)

        completed = subprocess.run(
            [cmd.name] + cmd.args,
            stdin=stdin_handle if stdin_handle else None,
            stdout=stdout_handle if stdout_handle else None,
            stderr=stderr_handle if stderr_handle else None,
        )
        return completed.returncode
    except FileNotFoundError:
        print(f"{cmd.name}: command not found", file=sys.stderr)
        return 127
    finally:
        for h in (stdin_handle, stdout_handle, stderr_handle):
            # avoid double-closing when both_handle used
            if h and h is not both_handle:
                h.close()
        if both_handle:
            both_handle.close()
