""" Control flow structures and parsing. """


class IfBlock:
    """ Represents an if/elif/else/fi block. """

    def __init__(self):
        self.branches = []  # List of (condition_line, command_lines) tuples
        self.else_commands = []  # Command lines in the else block


def parse_if_block(lines):
    """
    Parse a list of lines into an IfBlock structure.
    Lines should include 'if' at start and 'fi' at end.
    """
    block = IfBlock()

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        tokens = line.split()

        if not tokens:
            i += 1
            continue

        keyword = tokens[0]

        if keyword == "if" or keyword == "elif":
            # Extract condition (everything between if/elif and then)
            condition_lines = []

            # Check if 'then' is on the same line
            if "then" in tokens:
                then_idx = tokens.index("then")
                condition_parts = tokens[1:then_idx]
                condition_lines.append(" ".join(condition_parts))
                i += 1
            else:
                # Condition is on the next line(s) until 'then'
                i += 1
                while i < len(lines):
                    line = lines[i].strip()
                    if line == "then":
                        i += 1
                        break
                    elif line.startswith("then "):
                        # 'then' at start of line, rest is a command
                        i += 1
                        break
                    else:
                        condition_lines.append(line)
                        i += 1

            # Collect commands until next elif/else/fi
            command_lines = []
            while i < len(lines):
                line = lines[i].strip()
                tokens = line.split() if line else []

                if tokens and tokens[0] in ["elif", "else", "fi"]:
                    break

                if line:  # Skip empty lines
                    command_lines.append(line)
                i += 1

            # Combine condition lines into a single condition
            condition = " ".join(condition_lines)
            block.branches.append((condition, command_lines))

        elif keyword == "else":
            i += 1
            # Collect commands until fi
            else_commands = []
            while i < len(lines):
                line = lines[i].strip()
                tokens = line.split() if line else []

                if tokens and tokens[0] == "fi":
                    break

                if line:  # Skip empty lines
                    else_commands.append(line)
                i += 1

            block.else_commands = else_commands

        elif keyword == "fi":
            break

        else:
            i += 1

    return block
