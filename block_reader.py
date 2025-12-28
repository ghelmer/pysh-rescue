""" Read multi-line control structures. """

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

        # Parse just enough to detect keywords
        # Use shlex to respect quoting when checking for keywords
        import shlex
        try:
            tokens = shlex. split(line)
            if tokens:
                if tokens[0] == "if":
                    nesting += 1
                elif tokens[0] == "fi":
                    nesting -= 1
        except ValueError:
            # Incomplete quoting, not a keyword line
            pass

    return lines
