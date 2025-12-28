from shell_builtins import builtin


@builtin("echo")
def builtin_echo(args, state) -> int:
    print(" ".join(args))
    return 0
