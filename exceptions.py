""" Exceptions for the shell. """

class ShellExit(Exception):
    def __init__(self, status=0):
        self.status = status
