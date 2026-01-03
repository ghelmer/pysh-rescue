""" Current state of the shell. """
import os

class ShellState:
    def __init__(self):
        self.vars = {}
        self.last_status = 0

    def set_var(self, name, value, export=False):
        self.vars[name] = value
        if export:
            os.environ[name] = value

    def get_var(self, name):
        return self.vars.get(name, os.environ.get(name, ""))

    def set_status(self, status: int):
        # normalize like shells do
        self.last_status = int(status) if status is not None else 0

    def interpolate(self, token: str) -> str:
        result = ""
        i = 0
        n = len(token)

        while i < n:
            if token[i] != "$":
                result += token[i]
                i += 1
                continue

            # token[i] == '$'
            if i + 1 < n and token[i + 1] == "?":
                result += str(self.last_status)
                i += 2
                continue

            if i + 1 < n and token[i + 1] == "{":
                # Parse ${VAR}
                j = i + 2
                name = ""
                while j < n and (token[j].isalnum() or token[j] == "_"):
                    name += token[j]
                    j += 1
                if j < n and token[j] == "}" and name:
                    result += self.get_var(name)
                    i = j + 1
                else:
                    # Not a valid ${...} form; treat '$' literally
                    result += "$"
                    i += 1
                continue

            # Parse $VAR (only if next char can start a name)
            if i + 1 < n and (token[i + 1].isalpha() or token[i + 1] == "_"):
                i += 1
                name = ""
                while i < n and (token[i].isalnum() or token[i] == "_"):
                    name += token[i]
                    i += 1
                result += self.get_var(name)
            else:
                # Literal '$'
                result += "$"
                i += 1

        return result
