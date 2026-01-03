#!/usr/bin/env python3
"""
Fetch and execute the pysh-rescue shell directly from GitHub.

This bootstrap script downloads the pysh-rescue source files and runs the shell
without requiring any third-party packages. Only Python standard libraries are used.

SECURITY WARNING:
This script downloads and executes code from GitHub at runtime.
Use the --commit option to pin execution to a specific commit, tag, or ref
to avoid running unexpected or untrusted code.
"""
import argparse
import importlib
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "ghelmer/pysh-rescue"
SRC_DIR = "src"

FILES = [
    "command.py",
    "constants.py",
    "exceptions.py",
    "if_parser.py",
    "lexer.py",
    "main.py",
    "parser.py",
    "runner.py",
    "shell_builtins.py",
    "shell_state.py",
    "shell.py",
]

ENTRY_MODULE = "main"


def raw_base(ref: str) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{ref}/{SRC_DIR}"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "pysh-rescue-bootstrap"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and run pysh-rescue from GitHub without dependencies"
    )
    parser.add_argument(
        "--commit",
        metavar="REF",
        default="refs/heads/main",
        help="Git commit SHA, tag, or ref (default: main)"
    )
    args = parser.parse_args()

    base = raw_base(args.commit)

    with tempfile.TemporaryDirectory(prefix="pysh-rescue-") as tmpdir:
        tmp = Path(tmpdir)

        # Download source files
        for filename in FILES:
            url = f"{base}/{filename}"
            code = fetch_text(url)
            (tmp / filename).write_text(code, encoding="utf-8")

        # Ensure imports resolve from temp dir
        sys.path.insert(0, str(tmp))

        # Import entry module
        mod = importlib.import_module(ENTRY_MODULE)

        # Preferred execution style
        if hasattr(mod, "main"):
            mod.main()
            return

        # Fallback: run Shell directly
        shell_mod = importlib.import_module("shell")
        sh = shell_mod.Shell()
        rc = sh.run()
        raise SystemExit(rc)


if __name__ == "__main__":
    main()
