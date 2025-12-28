import os

from shell_builtins import builtin


@builtin("pwd")
def builtin_pwd(args, state):
    print(os.getcwd())
    return 0
