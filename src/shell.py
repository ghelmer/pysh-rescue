""" Implement the core of the shell. """
from runner import execute_command
from lexer import tokenize
from parser import parse_command_list, parse_top_level
from exceptions import ShellExit
from shell_state import ShellState
from if_parser import parse_if_to_node


def if_nesting_delta(tokens: list[str]) -> int:
    """ Check to see if a `fi` is in this line. """
    at_cmd_start = True
    delta = 0
    for tok in tokens:
        if tok == ";":
            at_cmd_start = True
            continue
        if at_cmd_start:
            if tok == "if":
                delta += 1
            elif tok == "fi":
                delta -= 1
            at_cmd_start = False
    return delta


def read_until_fi(read_func):
    """
    Read lines until 'fi' is encountered, tracking nesting.
    Uses the provided read_func which handles continuation.
    Returns list of complete logical lines.
    """
    lines = []
    nesting = 1

    while nesting > 0:
        line = read_func(prompt="> ")
        lines.append(line)

        try:
            toks = tokenize(line)

            at_cmd_start = True
            for tok in toks:
                if tok == ";":
                    at_cmd_start = True
                    continue

                if at_cmd_start:
                    if tok == "if":
                        nesting += 1
                    elif tok == "fi":
                        nesting -= 1
                    at_cmd_start = False
                else:
                    # still within command args
                    pass

        except ValueError:
            pass

    return lines


def read_command(prompt="$ "):
    """ Read a command with support for line continuation. """
    lines = []
    while True:
        line = input(prompt)
        if line.endswith("\\"):
            lines.append(line[:-1])
            prompt = "> "
        else:
            lines.append(line)
            break
    return "".join(lines)


class Shell:
    def __init__(self):
        self.state = ShellState()

    def run(self):
        while True:
            try:
                line = read_command()
                tokens = tokenize(line)

                # if-block handling needs to read more lines BEFORE parsing
                if tokens and tokens[0] == "if":
                    nesting = if_nesting_delta(tokens)
                    block_lines = [line]
                    if nesting > 0:
                        block_lines += read_until_fi(read_command)
                    block_text = " ; ".join(block_lines)
                    block_tokens = tokenize(block_text)
                    nodes = [parse_if_to_node(block_tokens, parse_command_list, execute_command)]
                else:
                    nodes = parse_top_level(tokens, self.state, execute_command)

                for node in nodes:
                    status = node.execute(self.state)
                    self.state.set_status(status)
            except ShellExit as e:
                return e.status

            except EOFError:
                print()
                return 0

            except KeyboardInterrupt:
                print()
