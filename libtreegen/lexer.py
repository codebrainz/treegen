from . import nodes
from . import report

reserved = {
    "abstract": "ABSTRACT",
    "extern":   "EXTERN",
    "false":    "FALSE",
    "node":     "NODE",
    "null":     "NULL",
    "root":     "ROOT",
    "target":   "TARGET",
    "true":     "TRUE",
    "visitor":  "VISITOR",
    "weak":     "WEAK",
    "list":     "LIST",
}

primitives = {
    "bool":   "BOOL",
    "float":  "FLOAT",
    "int":    "INT",
    "string": "STRING",
}

tokens = [
    'BINLIT',
    'BOOLEAN',
    'CHRLIT',
    'COLON',
    'COMMA',
    'COMMENT',
    'DECLIT',
    'EQUAL',
    'FLOATLIT',
    'HEXLIT',
    'IDENT',
    'INTEGER',
    'LBRACE',
    'LBRACKET',
    'LPAREN',
    'OCTLIT',
    'RBRACE',
    'RBRACKET',
    'RPAREN',
    'SEMICOLON',
    'STRLIT',
] + \
list(reserved.values()) + \
list(primitives.values())

t_COLON     = '\:'
t_COMMA     = '\,'
t_EQUAL     = '\='
t_LBRACE    = '\{'
t_LBRACKET  = '\['
t_LPAREN    = '\('
t_RBRACE    = '\}'
t_RBRACKET  = '\]'
t_RPAREN    = '\)'
t_SEMICOLON = '\;'

def t_COMMENT(t):
    r'//[^\n]*\n|/\*(.+?)\*/'
    t.lexer.lineno += t.value.count('\n')

def t_IDENT(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    if t.value == "true":
        t.type = 'BOOLEAN'
        t.value = True
    elif t.value == "false":
        t.type = 'BOOLEAN'
        t.value = False
    else:
        t.type = reserved.get(t.value, None)
        if t.type is None:
            t.type = primitives.get(t.value, 'IDENT')
    return t

def t_BINLIT(t):
    r'0[bB][0-1_]+'
    t.type = 'INTEGER'
    t.value = int(t.value.replace("_",""), 2)
    return t

def t_HEXLIT(t):
    r'0[xX][a-fA-F0-9_]+'
    t.type = 'INTEGER'
    t.value = int(t.value.replace("_",""), 16)
    return t

def t_OCTLIT(t):
    r'0[oO][0-7]+|0[0-9_]*'
    t.type = 'INTEGER'
    t.value = int(t.value.replace("_",""), 8)
    return t

def t_DECLIT(t):
    r'[1-9][0-9_]*'
    t.type = 'INTEGER'
    t.value = int(t.value.replace("_",""), 10)
    return t

def t_FLOATLIT(t):
    r'[0-9]*\.[0-9]+|[0-9]+\.[0-9]*'
    t.type = 'FLOAT'
    t.value = float(t.value)
    return t

# FIXME
def t_CHRLIT(t):
    r"'(''|[^'])*'"
    return t

# FIXME
def t_STRLIT(t):
    r'"(""|[^"])*"'
    return t

def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

t_ignore = ' \t'

def find_column(input, token, index=1):
    pos = token.lexpos if not callable(token.lexpos) else token.lexpos(index)
    last_cr = input.rfind('\n', 0, pos)
    if last_cr < 0:
        last_cr = 0
    column = (pos - last_cr) + 1
    return column

def t_error(t):
    location = nodes.Location(t.lexer.filename, t.lexer.lineno, find_column(t.lexer.lexdata, t))
    report.error("illegal character '%s'" % t.value[0], location)
