""" Parse if/then/elif/else/fi blocks properly. """

import shlex


class IfStatement:
    """ Represents a parsed if statement structure. """

    def __init__(self):
        self.branches = []  # List of (condition_lines, body_lines)
        self.else_body = []  # Lines in else block

    def add_branch(self, condition_lines, body_lines):
        self.branches.append((condition_lines, body_lines))

    def set_else_body(self, body_lines):
        self.else_body = body_lines


def split_on_semicolon_respecting_quotes(line):
    """
    Split a line on semicolons, respecting quotes.
    Returns list of command strings.
    """
    commands = []
    current = []

    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = False
    lexer.whitespace = ' \t\r\n'

    for token in lexer:
        if token == ';':
            if current:
                commands.append(' '.join(current))
                current = []
        else:
            current.append(token)

    if current:
        commands.append(' '.join(current))

    return commands


def parse_if_statement(lines):
    """
    Parse if/then/elif/else/fi structure.

    lines:  List of complete logical lines (with continuations already resolved)

    Returns: IfStatement object with structure, storing raw lines to be
             parsed later when executed.
    """
    stmt = IfStatement()

    # First, flatten lines by splitting on semicolons
    expanded_lines = []
    for line in lines:
        parts = split_on_semicolon_respecting_quotes(line)
        expanded_lines.extend(parts)

    i = 0
    state = 'start'  # start, condition, body, done
    current_condition = []
    current_body = []

    while i < len(expanded_lines):
        line = expanded_lines[i]

        # Tokenize properly to detect keywords
        try:
            tokens = shlex.split(line)
        except ValueError:
            # Quote error - treat as regular line
            tokens = []

        if not tokens:
            i += 1
            continue

        keyword = tokens[0]
        rest_of_line = line[len(keyword):].lstrip()

        if keyword == "if":
            if state != 'start':
                raise SyntaxError("Unexpected 'if'")
            state = 'condition'
            # Check if condition is on the same line
            if rest_of_line:
                current_condition.append(rest_of_line)

        elif keyword == "then":
            if state != 'condition':
                raise SyntaxError("Unexpected 'then'")
            state = 'body'
            # Check if there's a command after 'then' on the same line
            if rest_of_line:
                current_body.append(rest_of_line)

        elif keyword == "elif":
            if state != 'body':
                raise SyntaxError("Unexpected 'elif'")
            # Save previous branch
            stmt.add_branch(current_condition, current_body)
            current_condition = []
            current_body = []
            state = 'condition'
            # Check if condition is on the same line
            if rest_of_line:
                current_condition.append(rest_of_line)

        elif keyword == "else":
            if state != 'body':
                raise SyntaxError("Unexpected 'else'")
            # Save previous branch
            stmt.add_branch(current_condition, current_body)
            current_condition = []
            current_body = []
            state = 'else_body'
            # Check if there's a command after 'else'
            if rest_of_line:
                current_body.append(rest_of_line)

        elif keyword == "fi":
            if state == 'body':
                stmt.add_branch(current_condition, current_body)
            elif state == 'else_body':
                stmt.set_else_body(current_body)
            else:
                raise SyntaxError("Unexpected 'fi'")
            state = 'done'
            break

        else:
            # Regular command line
            if state == 'condition':
                current_condition.append(line)
            elif state == 'body' or state == 'else_body':
                current_body.append(line)
            else:
                raise SyntaxError(f"Unexpected command:   {line}")

        i += 1

    if state != 'done':
        raise SyntaxError("Incomplete if statement")

    return stmt
