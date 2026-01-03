""" Registry of builtin commands. """
import os
import shutil
import stat
import sys

from exceptions import ShellExit
from constants import VAR_NAME_RX

BUILTINS = {}


def builtin(name):
    """Decorator to register builtins"""
    def wrapper(func):
        BUILTINS[name] = func
        return func
    return wrapper


@builtin("cat")
def builtin_cat(args, state):
    if not args:
        for line in sys.stdin:
            print(line, end="")
        return 0

    rc = 0
    for path in args:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for chunk in f:
                    print(chunk, end="")
        except FileNotFoundError:
            print(f"cat: {path}: No such file or directory", file=sys.stderr)
            rc = 1
        except PermissionError:
            print(f"cat: {path}: Permission denied", file=sys.stderr)
            rc = 1
        except IsADirectoryError:
            print(f"cat: {path}: Is a directory", file=sys.stderr)
            rc = 1

    return rc

@builtin("cd")
def builtin_cd(args, state):
    if len(args) == 0:
        target = os.environ.get("HOME", "/")
    else:
        target = args[0]

    try:
        os.chdir(target)
        return 0
    except FileNotFoundError:
        print(f"cd: no such file or directory: {target}", file=sys.stderr)
    except NotADirectoryError:
        print(f"cd: not a directory: {target}", file=sys.stderr)
    # Indicate failure due to error
    return 1


@builtin("echo")
def builtin_echo(args, state) -> int:
    print(" ".join(args))
    return 0


@builtin("exit")
def builtin_exit(args, state):
    try:
        status = int(args[0]) if args else 0
    except ValueError:
        print("exit: numeric argument required", file=sys.stderr)
        status = 2
    raise ShellExit(status)


@builtin("export")
def builtin_export(args, state):
    """
    export NAME=value
    export NAME
    export   (prints exported vars)
    """
    # No args: display exported environment variables (simple version)
    if not args:
        for k in sorted(os.environ.keys()):
            print(f"{k}={os.environ[k]}")
        return 0

    for arg in args:
        if "=" in arg:
            name, value = arg.split("=", 1)
            if not VAR_NAME_RX.match(name):
                print(f"export: not a valid identifier: {name}", file=sys.stderr)
                return 1
            state.set_var(name, value, export=True)
        else:
            name = arg
            if not VAR_NAME_RX.match(name):
                print(f"export: not a valid identifier: {name}", file=sys.stderr)
                return 1
            # Export current shell var value (or empty if unset)
            value = state.get_var(name)
            state.set_var(name, value, export=True)

    return 0


def parse_ls_args(args):
    options = {
        "long": False,
        "all": False,
    }
    paths = []

    for arg in args:
        if arg.startswith("-"):
            if "l" in arg:
                options["long"] = True
            if "a" in arg:
                options["all"] = True
        else:
            paths.append(arg)

    if not paths:
        paths = ["."]

    return options, paths


def _ls_list_directory(path, show_all, state):
    try:
        entries = os.listdir(path)
    except PermissionError:
        print(f"ls: cannot open directory '{path}'", file=sys.stderr)
        return []

    if not show_all:
        entries = [e for e in entries if not e.startswith(".")]

    return sorted(entries)


def _ls_format_long(path, name):
    full_path = os.path.join(path, name)
    st = os.stat(full_path)

    file_type = "d" if stat.S_ISDIR(st.st_mode) else "-"
    perms = stat.filemode(st.st_mode)[1:]  # strip leading file type
    size = st.st_size

    return f"{file_type}{perms} {size:>8} {name}"


@builtin("ls")
def builtin_ls(args, state) -> int:
    options, paths = parse_ls_args(args)
    multiple = len(paths) > 1

    for path in paths:
        if os.path.isdir(path):
            if multiple:
                print(f"{path}:")

            entries = _ls_list_directory(path, options["all"], state)

            for name in entries:
                if options["long"]:
                    print(_ls_format_long(path, name))
                else:
                    print(name)

            if multiple:
                print()

        elif os.path.exists(path):
            if options["long"]:
                print(_ls_format_long(".", path))
            else:
                print(path)
        else:
            print(f"ls: cannot access '{path}'", file=sys.stderr)
    return 0


@builtin("pwd")
def builtin_pwd(args, state):
    print(os.getcwd())
    return 0


@builtin("rm")
def builtin_rm(args, state):
    """
    rm [-r] [-f] FILE...
      -r  recursive (remove directories)
      -f  force (ignore missing files, suppress most errors)
    """
    recursive = False
    force = False
    paths = []

    # Parse flags
    parsing_opts = True
    for a in args:
        if parsing_opts and a == "--":
            parsing_opts = False
            continue

        if parsing_opts and a.startswith("-") and a != "-":
            # support -r, -f, -rf, -fr
            for ch in a[1:]:
                if ch == "r":
                    recursive = True
                elif ch == "f":
                    force = True
                else:
                    print(f"rm: invalid option -- '{ch}'", file=sys.stderr)
                    return 2
        else:
            parsing_opts = False  # end options at first path (recommended)
            paths.append(a)

    if not paths:
        print("rm: missing operand", file=sys.stderr)
        return 1

    def has_parent_ref(p: str) -> bool:
        # Treat any ".." path component as unsafe
        parts = [x for x in p.split(os.sep) if x not in ("", ".")]
        return ".." in parts

    rc = 0

    for path in paths:
        # Guardrails apply only to recursive removal
        if recursive:
            # 1) forbid '..' components
            if has_parent_ref(path):
                if not force:
                    print(f"rm: refusing to remove '{path}': contains '..'", file=sys.stderr)
                    rc = 1
                continue

            # 2) forbid removing filesystem root (after normalization)
            # - abspath() anchors relative paths to cwd
            # - normpath() collapses things like "a/.."
            # - realpath() resolves symlinks (helps catch "/var/.." -> "/")
            resolved = os.path.realpath(os.path.normpath(os.path.abspath(path)))
            if resolved == os.path.sep:
                if not force:
                    print("rm: refusing to remove '/' recursively", file=sys.stderr)
                    rc = 1
                continue

        try:
            # If it's a directory, only remove if -r
            st = os.lstat(path)  # doesn't follow symlinks
            is_link = stat.S_ISLNK(st.st_mode)
            is_dir = stat.S_ISDIR(st.st_mode)
            if is_dir and not is_link:
                if not recursive:
                    print(f"rm: cannot remove '{path}': Is a directory", file=sys.stderr)
                    rc = 1
                    continue
                shutil.rmtree(path)
            else:
                # file or symlink
                os.remove(path)

        except FileNotFoundError:
            if not force:
                print(f"rm: cannot remove '{path}': No such file or directory", file=sys.stderr)
                rc = 1

        except PermissionError:
            if not force:
                print(f"rm: cannot remove '{path}': Permission denied", file=sys.stderr)
                rc = 1

        except OSError as e:
            # Catches cases like "Directory not empty" without -r, etc.
            if not force:
                print(f"rm: cannot remove '{path}': {e}", file=sys.stderr)
                rc = 1

    return rc


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

