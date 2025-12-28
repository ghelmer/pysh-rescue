""" Base class for executable types. """

class Executable:
    def execute(self, state):
        raise NotImplementedError
