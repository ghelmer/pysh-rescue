"""Implement the test/[ builtin for conditionals"""

from shell_builtins import builtin
import os


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
