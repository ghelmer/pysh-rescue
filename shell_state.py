""" Current state of the shell. """
import os

class ShellState:
    def __init__(self):
        self.vars = {}

    def set_var(self, name, value, export=False):
        self.vars[name] = value
        if export:
            os.environ[name] = value

    def get_var(self, name):
        return self.vars.get(name, os.environ.get(name, ""))

    def interpolate(self, token):
        # Simple $VAR substitution
        result = ""
        i = 0
        while i < len(token):
            if token[i] == '$':
                i += 1
                name = ""
                while i < len(token) and (token[i].isalnum() or token[i] == '_'):
                    name += token[i]
                    i += 1
                result += self.get_var(name)
            else:
                result += token[i]
                i += 1
        return result
