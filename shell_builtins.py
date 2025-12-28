""" Registry of builtin commands. """
BUILTINS = {}

def builtin(name):
    """Decorator to register builtins"""
    def wrapper(func):
        BUILTINS[name] = func
        return func
    return wrapper
