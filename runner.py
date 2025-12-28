""" Execute a shell command. """
import contextlib
import subprocess
import sys

from command import Command
from shell_builtins import BUILTINS
from shell_state import ShellState


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
