""" Evaluate conditions for control flow. """


def evaluate_condition(condition_line, shell_state, parse_func, execute_func):
    """
    Execute a condition command using the shell's parse and execute functions.
    Returns True if exit code is 0 (success).
    """
    if not condition_line.strip():
        return False

    # Use the shell's own parse_command
    cmd = parse_func(condition_line, shell_state)
    if not cmd:
        return False

    # Execute and get return code
    result = execute_func(cmd, shell_state)

    # In shell, 0 means true/success
    return result == 0
