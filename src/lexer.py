""" Lexical analysis for shell commands. """
import shlex


def tokenize(line: str) -> list[str]:
    lex = shlex.shlex(line, posix=True, punctuation_chars=";&><|")
    lex.whitespace_split = True
    lex.commenters = ""
    tokens = list(lex)

    result = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and tokens[i] in (">", "<", "&", "|") and tokens[i] == tokens[i + 1]:
            result.append(tokens[i] * 2)  # >>, <<, &&, ||
            i += 2
        else:
            result.append(tokens[i])
            i += 1
    return result
