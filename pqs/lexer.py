import math
import ply.lex as lex
import string


# lexical tokens
_tokens = (
    'END',

    # identifiers
    'QUOTED_ID',
    'ID',

    # special syntax
    'COLUMN_INDEX',

    # literals
    'STRING',
    'TEMPLATE',
    'RAW',
    'CONSTANT',
    'INTEGER',
    'FLOAT',

    # operators
    'ADD',
    'SUB',
    'MUL',
    'DIV',
    'MOD',
    'POW',
    'EQ',
    'NE',
    'LT',
    'LE',
    'GT',
    'GE',
)


reserved = (
    'AND',
    'AS',
    'ASC',
    'BY',
    'CONNECT',
    'CREATE',
    'CROSS',
    'CSV',
    'DELIMITER',
    'DESC',
    'DISTINCT',
    'DROP',
    'EXPLODE',
    'FIELD',
    'FILTER',
    'FIRST',
    'FROM',
    'HEADER',
    'HELP',
    'HTML',
    'IN',
    'INNER',
    'INTO',
    'IS',
    'JOIN',
    'JSON',
    'KEEP',
    'LAST',
    'LEFT',
    'LIKE',
    'LINE',
    'LINES',
    'NA',
    'NAN',
    'NO',
    'NOT',
    'NULL',
    'ON',
    'OPEN',
    'OR',
    'OUTER',
    'PRINT',
    'PUT',
    'QUERY',
    'QUIT',
    'QUOTE',
    'READ',
    'RENAME',
    'REVERSE',
    'RIGHT',
    'RUN',
    'SELECT',
    'SORT',
    'SQL',
    'TAB',
    'TAKE',
    'TO',
    'TRANSPOSE',
    'UNION',
    'WITH',
    'WRITE',
)


constants = {
    'TRUE': True,
    'FALSE': False,
    'PI': math.pi,
    'E': math.e,
    'TAU': math.tau,
}


# all tokens
tokens = _tokens + reserved


# literal syntax characters
literals = (',', '(', ')', '[', ']', '.')


# lexer states
states = (
    ('block', 'exclusive'),
)


# used when entering the block state
block_end = None


# skip whitespace
t_ignore = ' \t'
t_block_ignore = ''


# operator tokens
t_ADD = r'\+'
t_SUB = r'-'
t_MUL = r'\*'
t_DIV = r'/'
t_MOD = r'%'
t_POW = r'\^'

# comparison tokens (order matters)
t_NE = r'<>'
t_LE = r'<='
t_GE = r'>='
t_LT = r'<'
t_GT = r'>'
t_EQ = r'='


def t_END(t):
    r"(?:[#].*|[\r\n]+)+"
    t.lexer.lineno += t.value.count('\n')
    return t


def t_ID(t):
    r"(?a:[_a-zA-Z][_a-zA-Z0-9]*)"
    kw = t.value.upper()

    # reserved keywords
    if kw in reserved:
        t.type = kw

    # keyword math constants
    if kw in constants:
        t.type = 'CONSTANT'
        t.value = constants[t.value.upper()]

    return t


def t_QUOTED_ID(t):
    r"`[^`]+`"
    t.type = 'ID'
    t.value = t.value.strip('`')
    return t


def t_COLUMN_INDEX(t):
    r":\d+"
    t.value = int(t.value[1:])
    return t


def t_TEMPLATE(t):
    r'"[^"]*"|\'[^\']*\''
    t.value = string.Template(t.value[1:-1])

    # attempt to substitute with nothing, if it works, then it's a simple string
    try:
        t.value = t.value.substitute()
        t.type = 'STRING'
    except KeyError:
        pass

    return t


def t_FLOAT(t):
    r"\d+(?:\.\d+|[eE][+-]?\d+|\.\d+[eE][+-]?\d+)"
    t.value = float(t.value)
    return t


def t_INTEGER(t):
    r"\d+"
    t.value = int(t.value)
    return t


def t_BLOCK(t):
    r'<<(.+)'
    global block_end

    # set the end of the block
    block_end = t.value[2:].strip()
    t.lexer.push_state('block')


def t_block_RAW(t):
    r'.*[\r\n]+'
    global block_end

    # count lines
    t.lexer.lineno += t.value.count('\n')

    # check for end of the block
    if t.value.strip() == block_end:
        t.lexer.pop_state()
        t.type = 'END'
        block_end = None

    return t


def t_error(t):
    """
    Error handler.
    """
    raise SyntaxError(f'Syntax error on line {t.lineno} near {t.value}')


def t_block_error(t):
    """
    Error handler for block state.
    """
    t.lexer.pop_state()
    raise SyntaxError(f'Syntax error on line {t.lineno} near {t.value}')


# Build the lexer
lexer = lex.lex()
