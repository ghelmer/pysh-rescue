""" Implement ls as a builtin command. """
import os
import stat

from shell_builtins import builtin


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


def list_directory(path, show_all):
    try:
        entries = os.listdir(path)
    except PermissionError:
        print(f"ls: cannot open directory '{path}'")
        return []

    if not show_all:
        entries = [e for e in entries if not e.startswith(".")]

    return sorted(entries)


def format_long(path, name):
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

            entries = list_directory(path, options["all"])

            for name in entries:
                if options["long"]:
                    print(format_long(path, name))
                else:
                    print(name)

            if multiple:
                print()

        elif os.path.exists(path):
            if options["long"]:
                print(format_long(".", path))
            else:
                print(path)
        else:
            print(f"ls: cannot access '{path}'")
    return 0
