from shell_builtins import builtin
from exceptions import ShellExit


@builtin("exit")
def builtin_exit(args, state):
    status = int(args[0]) if args else 0
    raise ShellExit(status)
