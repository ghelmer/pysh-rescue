""" Execute if statements using the shell's parse and execute functions. """


def evaluate_condition(condition_lines, state, parse_func, execute_func, split_func):
    """
    Evaluate a condition by executing command(s) and checking exit code.
    """
    if not condition_lines:
        return False

    condition_text = " ".join(condition_lines).strip()

    if not condition_text:
        return False

    # Split on semicolons if present
    commands = split_func(condition_text)
    result = 0

    for cmd_text in commands:
        cmd = parse_func(cmd_text, state)
        if cmd:
            result = execute_func(cmd, state)

    # Only the last command's exit code matters for the condition
    return result == 0


def execute_if_statement(stmt, state, parse_func, execute_func, split_func):
    """
    Execute an IfStatement by evaluating conditions and executing bodies.
    """
    # Try each branch
    for condition_lines, body_lines in stmt.branches:
        if evaluate_condition(condition_lines, state, parse_func, execute_func, split_func):
            # Execute this branch
            for body_line in body_lines:
                # Handle semicolons in body lines
                commands = split_func(body_line)
                for cmd_text in commands:
                    cmd = parse_func(cmd_text, state)
                    if cmd:
                        execute_func(cmd, state)
            return  # Branch executed, we're done

    # No branch matched, execute else if present
    if stmt.else_body:
        for body_line in stmt.else_body:
            commands = split_func(body_line)
            for cmd_text in commands:
                cmd = parse_func(cmd_text, state)
                if cmd:
                    execute_func(cmd, state)
