""" A parsed command. """

class Command:
    def __init__(self, name, args, stdout=None, append=False):
        self.name = name
        self.args = args
        self.stdout = stdout      # filename or None
        self.append = append      # True for >>
