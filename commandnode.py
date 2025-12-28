""" Implement a simple command as a parsed node. """
from command import Command
from executable import Executable
from shell_state import ShellState


class CommandNode(Executable):
    def __init__(self, cmd: Command, executor):
        self.cmd = cmd
        self.executor = executor

    def execute(self, state: ShellState) -> int:
        return self.executor(self.cmd, state) or 0
