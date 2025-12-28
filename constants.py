import re

GLOB_CHARS = set("*?[")
VAR_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
