import re

GLOB_CHARS = set("*?[")
VAR_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
# matches: 2>file, 2>>file, &>file, &>>file
REDIR_COMBINED_RX = re.compile(r"^(?P<fd>[0-9]+|&)(?P<op>>>|>)(?P<rest>.*)$")
