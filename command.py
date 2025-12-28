from shell_state import ShellState


class Executable:
    """ Base class for executable types. """
    def execute(self, state):
        raise NotImplementedError


class Command:
    """ A parsed command. """
    def __init__(self, name, args, stdout=None, append=False):
        self.name = name
        self.args = args
        self.stdout = stdout      # filename or None
        self.append = append      # True for >>


class CommandNode(Executable):
    """ Implement a simple command as a parsed node. """
    def __init__(self, cmd: Command, executor):
        self.cmd = cmd
        self.executor = executor

    def execute(self, state: ShellState) -> int:
        return self.executor(self.cmd, state) or 0
