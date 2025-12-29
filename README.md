# Rescue Shell in Python

**Rescue Shell** is a minimal, Bourne-style command shell written entirely in Python  
(with assistance from ChatGPT for portions of the implementation).

Its primary goal is **practical portability**: to provide a small, usable shell
in environments where Python is available but a traditional system shell may not be,
such as:

- Minimal containers
- Restricted execution environments
- Educational sandboxes
- Recovery or debugging scenarios

This project is intentionally **not** a full POSIX-compliant shell.
Instead, it focuses on a clean internal design, predictable behavior,
and ease of understanding.

---

## Design Goals

- Minimal dependencies (standard library only)
- Clear separation of concerns (lexer → parser → executor)
- Safe, explicit handling of redirection and execution
- Readable code suitable for learning or extension
- Works consistently across platforms supported by Python

---

## Features

### Variables

* User-defined shell variables:
  ```sh
  X=hello
  echo $X
  ```
* Variable interpolation using `$NAME`
* Exporting variables to the environment:
  ```sh
  export X
  export Y=value
  ```

### Redirection

Supports common input/output redirection operators:

* stdin
  * `< file`
* stdout
  * `> file`
  * `>> file`
* stderr
  * `2> file`
  * `2>> file`
* stdout + stderr
  * `&> file`
  * `&>> file`

Redirection works for both:
* Built-in commands
* External commands executed via `subprocess`

Examples:
```sh
ls > out.txt
ls missing 2> err.txt
cmd &> all.txt
cat < input.txt
```

---

### Built-in Commands

The following commands are implemented directly by the shell:
* `cat` — print file contents or stdin
* `cd` — change directory
* `echo` — print arguments
* `exit [status]` — exit the shell
* `export` — export variables to environment
* `ls` — list directory contents
* `pwd` — print current directory
* `rm` — remove files or directories (`-r`, `-f`)
* `test` — basic conditional testing (useful with `if`)

---

### Control Flow

Supports Bourne-style conditional execution:
```sh
if test -f file.txt; then
    echo "File exists"
elif test -d dir; then
    echo "Directory exists"
else
    echo "Not found"
fi
```
* Nested `if` blocks are supported
* Commands may appear on the same line or across multiple lines
* `;` may be used to separate commands

---

### Command Execution

* External commands are executed using Python’s `subprocess` module
* Redirection is applied correctly to external processes
* Return codes are propagated for use in conditionals

---

### Limitations (By Design)

This shell intentionally does not implement:

* Pipelines (`|`)
* Background execution (`&`)
* Job control
* Globbing beyond basic filename expansion
* Advanced shell expansions (`$(...)`, `${VAR}`, arrays)
* Signal handling beyond basic interruption

These omissions keep the codebase compact and approachable.

---

### Project Structure

The codebase is organized into small, focused modules:

* `lexer.py` — tokenization and operator handling
* `parser.py` — command and redirection parsing
* `runner.py` — command execution and redirection wiring
* `shell.py` — REPL and control flow
* `shell_builtins.py` — builtin command registry
* `if_parser.py` — parsing and execution of if blocks
* `command.py` — command representation
* `shell_state.py` — variable and environment management

---

### Educational Value

This project is well-suited for:
* Teaching shell fundamentals
* Demonstrating interpreters and execution pipelines
* Exploring parsing and tokenization strategies
* Learning safe subprocess execution in Python
* It is also intentionally structured so that features such as pipelines,
job control, or scripting support could be added incrementally.

---

### License

Copyright (c) 2025 Guy Helmer

This code is distributed under the MIT license.
