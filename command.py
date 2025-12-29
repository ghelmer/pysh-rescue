""" Command to be executed. """
from shell_state import ShellState


class Executable:
    """ Base class for executable types. """
    def execute(self, state):
        raise NotImplementedError


class Command:
    def __init__(self, name, args, stdin=None, stdout=None, append=False,
                 stderr=None, stderr_append=False, redirect_both=False):
        self.name = name
        self.args = args
        self.stdin = stdin        # filename or None

        self.stdout = stdout      # filename or None
        self.append = append      # True for >>

        self.stderr = stderr      # filename or None
        self.stderr_append = stderr_append

        # if True, redirect stdout+stderr to the same file
        self.redirect_both = redirect_both


class CommandNode(Executable):
    """ Implement a simple command as a parsed node. """
    def __init__(self, cmd: Command, executor):
        self.cmd = cmd
        self.executor = executor

    def execute(self, state: ShellState) -> int:
        return self.executor(self.cmd, state) or 0
