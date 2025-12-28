""" Registry of builtin commands. """
import os

from exceptions import ShellExit

BUILTINS = {}

def builtin(name):
    """Decorator to register builtins"""
    def wrapper(func):
        BUILTINS[name] = func
        return func
    return wrapper


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


@builtin("echo")
def builtin_echo(args, state) -> int:
    print(" ".join(args))
    return 0


@builtin("exit")
def builtin_exit(args, state):
    status = int(args[0]) if args else 0
    raise ShellExit(status)


@builtin("pwd")
def builtin_pwd(args, state):
    print(os.getcwd())
    return 0


@builtin("[")
@builtin("test")
def builtin_test(args, state):
    """
    Implement basic test functionality.
    Returns 0 (true) or 1 (false).
    """
    # Remove trailing ] if present
    if args and args[-1] == "]":
        args = args[:-1]

    if not args:
        return 1  # Empty test is false

    # String comparisons
    if len(args) == 3:
        left, op, right = args

        if op == "=":
            return 0 if left == right else 1
        elif op == "!=":
            return 0 if left != right else 1
        elif op == "-eq":
            return 0 if int(left) == int(right) else 1
        elif op == "-ne":
            return 0 if int(left) != int(right) else 1
        elif op == "-lt":
            return 0 if int(left) < int(right) else 1
        elif op == "-le":
            return 0 if int(left) <= int(right) else 1
        elif op == "-gt":
            return 0 if int(left) > int(right) else 1
        elif op == "-ge":
            return 0 if int(left) >= int(right) else 1

    # Unary tests
    if len(args) == 2:
        op, path = args

        if op == "-f":
            return 0 if os.path.isfile(path) else 1
        elif op == "-d":
            return 0 if os.path.isdir(path) else 1
        elif op == "-e":
            return 0 if os.path.exists(path) else 1
        elif op == "-z":  # String is empty
            return 0 if not path else 1
        elif op == "-n":  # String is not empty
            return 0 if path else 1

    # Single argument:  test if non-empty string
    if len(args) == 1:
        return 0 if args[0] else 1

    return 1  # Default to false

