import os

from shell_builtins import builtin


@builtin("cd")
def builtin_cd(args, state):
    if len(args) == 0:
        target = os.environ.get("HOME", "/")
    else:
        target = args[0]

    try:
        os.chdir(target)
    except FileNotFoundError:
        print(f"cd: no such file or directory: {target}")
    except NotADirectoryError:
        print(f"cd: not a directory: {target}")

    return 0
