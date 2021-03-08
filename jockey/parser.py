import operator
import ply.yacc as yacc
import uuid

from .dialect import *
from .functions import *
from .lexer import tokens, literals
from .term import *
from .statement import *


# unary operators
unary_ops = {
    '-': operator.neg,
    'NOT': operator.not_,
}

# binary operators
binary_ops = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
    '%': operator.mod,
    '^': operator.pow,
    '<': operator.lt,
    '>': operator.gt,
    '<=': operator.le,
    '>=': operator.ge,
    '<>': operator.ne,
    '=': operator.eq,
    'AND': operator.and_,
    'OR': operator.or_,
}


# callable functions
function_ops = {
    'exp': series_function()(math.exp),
    'float': series_function()(float),
    'if': if_,
    'ifnull': if_na,
    'int': series_function()(int),
    'iota': iota,
    'log': series_function()(math.log),
    'log10': series_function()(math.log10),
    'split': series_function()(lambda s, sep: s.split(sep)),
    'uuid': lambda: str(uuid.uuid4()),
}


precedence = (
    ('left', 'AND', 'OR'),
    ('left', 'IS', 'IN'),
    ('left', 'LIKE', 'EQ', 'NE', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'ADD', 'SUB'),
    ('left', 'MUL', 'DIV', 'MOD', 'POW'),
    ('right', 'NEG'),
    ('right', 'NOT'),
)


def clause(p, symbol, default=None):
    """
    Lookup the parse value of an optional, parsed keyword argument.
    """
    for i in p.slice[1:]:
        if isinstance(i, yacc.YaccSymbol) and i.type == symbol:
            return i.value

    return default


def p_ident(p):
    """
    ident : ID
          | QUOTED_ID
    """
    p[0] = p[1]


def p_string(p):
    """
    string : STRING
    """
    p[0] = p[1]


def p_string_tab(p):
    """
    string : TAB
    """
    p[0] = '\t'
    
    
def p_string_whitespace(p):
    """
    string : WHITESPACE
    """
    p[0] = '\s+'


def p_literal(p):
    """
    literal : CONSTANT
            | FLOAT
            | INTEGER
            | string
    """
    p[0] = Literal(p[1])


def p_template(p):
    """
    template : TEMPLATE
    """
    p[0] = Template(p[1])


def p_na(p):
    """
    na : NA
       | NAN
       | NULL
    """
    p[0] = Literal(float('nan'))


def p_columnid(p):
    """
    columnid : ident
             | COLUMN_INDEX
    """
    p[0] = p[1]


def p_column(p):
    """
    column : columnid
    """
    p[0] = Column(p[1])


def p_paren(p):
    """
    paren : '(' term ')'
    """
    p[0] = p[2]


def p_emptylist(p):
    """
    emptylist :
    """
    p[0] = []


def p_list(p):
    """
    list : '[' emptylist ']'
         | '[' termlist ']'
    """
    p[0] = TermList(p[2])


def p_primary(p):
    """
    primary : literal
            | template
            | na
            | column
            | paren
            | list
    """
    p[0] = p[1]


def p_term_primary(p):
    """
    term : primary
    """
    p[0] = p[1]


def p_term_unary(p):
    """
    term : SUB term %prec NEG
         | NOT term
    """
    p[0] = UnaryTerm(term=p[2], op=unary_ops[p[1]])


def p_term_isna(p):
    """
    term : term IS NA
         | term IS NAN
         | term IS NULL
    """
    p[0] = UnaryTerm(term=p[1], op=is_na)


def p_term_isnotna(p):
    """
    term : term IS NOT NA
         | term IS NOT NAN
         | term IS NOT NULL
    """
    p[0] = UnaryTerm(term=p[1], op=is_not_na)


def p_term_binary(p):
    """
    term : term ADD term
         | term SUB term
         | term MUL term
         | term DIV term
         | term MOD term
         | term POW term
         | term EQ term
         | term NE term
         | term LT term
         | term LE term
         | term GT term
         | term GE term
         | term AND term
         | term OR term
    """
    p[0] = BinaryTerm(l=p[1], r=p[3], op=binary_ops[p[2].upper()])


def p_term_in(p):
    """
    term : term IN term
    """
    p[0] = BinaryTerm(l=p[1], r=p[3], op=is_in)


def p_term_not_in(p):
    """
    term : term NOT IN term
    """
    p[0] = BinaryTerm(l=p[1], r=p[4], op=not_in)


def p_term_like(p):
    """
    term : term LIKE term
    """
    p[0] = BinaryTerm(l=p[1], r=p[3], op=lambda a, b: is_in(a, b, regex=True))


def p_term_not_like(p):
    """
    term : term NOT LIKE term
    """
    p[0] = BinaryTerm(l=p[1], r=p[4], op=lambda a, b: not_in(a, b, regex=True))


def p_term_function(p):
    """
    term : ident '(' emptylist ')'
         | ident '(' termlist ')'
    """
    p[0] = FunctionTerm(f=function_ops.get(p[1].lower(), unknown_function(p[1])), args=p[3])


def p_term_index(p):
    """
    term : term '[' term ']'
    """
    p[0] = IndexedTerm(term=p[1], index=p[3])


def p_termlist_multi(p):
    """
    termlist : term ',' termlist
    """
    p[0] = [p[1], *p[3]]


def p_termlist(p):
    """
    termlist : term
    """
    p[0] = [p[1]]


def p_expr_term(p):
    """
    expr : term
    """
    p[0] = Expression(term=p[1])


def p_expr_alias(p):
    """
    expr : term AS ident
    """
    p[0] = Expression(term=p[1], alias=p[3])


def p_exprlist_multi(p):
    """
    exprlist : expr ',' exprlist
             | MUL ',' exprlist
    """
    p[0] = [p[1], *p[3]]


def p_exprlist(p):
    """
    exprlist : expr
             | MUL
    """
    p[0] = [p[1]]


def p_identlist_multi(p):
    """
    identlist : ident ',' identlist
    """
    p[0] = [p[1], *p[3]]


def p_identlist(p):
    """
    identlist : ident
    """
    p[0] = [p[1]]


def p_columnlist_multi(p):
    """
    columnlist : columnid ',' columnlist
    """
    p[0] = [p[1], *p[3]]


def p_columnlist(p):
    """
    columnlist : columnid
               | MUL
    """
    p[0] = [p[1]]


def p_how(p):
    """
    how : INNER JOIN
        | OUTER JOIN
        | LEFT JOIN
        | RIGHT JOIN
    """
    p[0] = p[1].lower()


def p_how_join(p):
    """
    how : JOIN
    """
    p[0] = 'inner'


def p_on(p):
    """
    on : ON columnlist
    """
    p[0] = p[2]


def p_by(p):
    """
    by : BY columnlist
    """
    p[0] = p[2]


def p_orderby(p):
    """
    orderby : BY ordering
    """
    p[0] = p[2]


def p_ordering_multi(p):
    """
    ordering : order ',' ordering
    """
    p[0] = [p[1], *p[3]]


def p_ordering(p):
    """
    ordering : order
    """
    p[0] = [p[1]]


def p_order(p):
    """
    order : columnid
    """
    p[0] = (p[1], True)


def p_order_dir(p):
    """
    order : ident ASC
          | ident DESC
    """
    p[0] = (p[1], p[2].upper() == 'ASC')


def p_asinputformat(p):
    """
    asinputformat : AS csv
                  | AS json
    """
    p[0] = p[2]
    
    
def p_asoutputformat(p):
    """
    asoutputformat : AS csv
                   | AS json
                   | AS html
    """
    p[0] = p[2]


def p_block(p):
    """
    block : RAW block
    """
    p[0] = p[1] + p[2]


def p_block_end(p):
    """
    block :
    """
    p[0] = ''


def p_csv(p):
    """
    csv : CSV csvopts
    """
    p[0] = CSV(**p[2])


def p_csvopts_none(p):
    """
    csvopts :
    """
    p[0] = {}


def p_csvopts_header(p):
    """
    csvopts : WITH HEADER csvopts
            | NO HEADER csvopts
    """
    p[0] = {'header': p[1] == 'WITH', **p[3]}


def p_csvopts_sep(p):
    """
    csvopts : FIELD DELIMITER string csvopts
    """
    p[0] = {'sep': p[3], **p[4]}


def p_csvopts_line(p):
    """
    csvopts : LINE DELIMITER string csvopts
    """
    p[0] = {'linesep': p[3], **p[4]}


def p_csvopts_quote(p):
    """
    csvopts : QUOTE string csvopts
    """
    p[0] = {'quotechar': p[2], **p[3]}


def p_json(p):
    """
    json : JSON
    """
    p[0] = JSON()


def p_json_lines(p):
    """
    json : JSON LINES
    """
    p[0] = JSONLines()


def p_html(p):
    """
    html : HTML
    """
    p[0] = HTML()


def p_to(p):
    """
    to : TO string
    """
    p[0] = p[2]


def p_with(p):
    """
    with : WITH ident
    """
    p[0] = p[2]


def p_keep(p):
    """
    keep : KEEP FIRST
         | KEEP LAST
    """
    p[0] = p[2].lower()


def p_sourcetype(p):
    """
    sourcetype : SQL
    """
    p[0] = p[1]


def p_keyword(p):
    """
    keyword : CONNECT
            | CROSS
            | CREATE
            | DISTINCT
            | DROP
            | EXPLODE
            | FILTER
            | HELP
            | JOIN
            | OPEN
            | PLOT
            | PRINT
            | PUT
            | QUERY
            | QUIT
            | READ
            | RENAME
            | REVERSE
            | RUN
            | SELECT
            | SH
            | SORT
            | TAKE
            | TRANSPOSE
            | UNION
            | WRITE
    """
    p[0] = p[1]


def p_connect(p):
    """
    connect : CONNECT ident TO string AS sourcetype
    """
    p[0] = Connect(alias=p[2], url=p[4], typ=p[6])


def p_cross(p):
    """
    cross : CROSS ident WITH ident
    """
    p[0] = Cross(table=p[2], other=p[4])


def p_cross_it(p):
    """
    cross : CROSS WITH ident
    """
    p[0] = Cross(table='it', other=p[3])


def p_distinct(p):
    """
    distinct : DISTINCT ident by keep
             | DISTINCT ident by
             | DISTINCT ident
    """
    p[0] = Distinct(table=p[2], columns=clause(p, 'by', '*'), keep=clause(p, 'keep', 'first'))


def p_distinct_it(p):
    """
    distinct : DISTINCT by keep
             | DISTINCT by
             | DISTINCT
    """
    p[0] = Distinct(table='it', columns=clause(p, 'by', '*'), keep=clause(p, 'keep', 'first'))


def p_drop(p):
    """
    drop : DROP columnlist FROM ident
    """
    p[0] = Drop(table=p[4], columns=p[2])


def p_drop_it(p):
    """
    drop : DROP columnlist
    """
    p[0] = Drop(table='it', columns=p[2])


def p_explode(p):
    """
    explode : EXPLODE columnid FROM ident
    """
    p[0] = Explode(table=p[4], column=p[42])


def p_explode_it(p):
    """
    explode : EXPLODE columnid
    """
    p[0] = Explode(table='it', column=p[2])


def p_filter(p):
    """
    filter : FILTER term FROM ident
    """
    p[0] = Filter(table=p[4], where=p[2])


def p_filter_it(p):
    """
    filter : FILTER term
    """
    p[0] = Filter(table='it', where=p[2])


def p_help(p):
    """
    help : HELP
         | HELP ident
         | HELP keyword
    """
    p[0] = Help(command=p[2] if len(p) > 2 else None)


def p_join(p):
    """
    join : how ident WITH ident on
         | how ident WITH ident
    """
    p[0] = Join(table=p[2], other=p[4], how=p[1], on=clause(p, 'on'))


def p_join_it(p):
    """
    join : how WITH ident on
         | how WITH ident
    """
    p[0] = Join(table='it', other=p[3], how=p[1], on=clause(p, 'on'))


def p_open(p):
    """
    open : OPEN ident asinputformat
    """
    p[0] = Open(table=p[2], dialect=p[3])


def p_open_it(p):
    """
    open : OPEN asoutputformat
    """
    p[0] = Open(table='it', dialect=p[2])


def p_plot(p):
    """
    plot : PLOT ident to with
         | PLOT ident to
         | PLOT ident with
         | PLOT ident
    """
    p[0] = Plot(table=p[2], file_or_url=clause(p, 'to'), options=clause(p, 'with'))


def p_plot_it(p):
    """
    plot : PLOT to with
         | PLOT to
         | PLOT with
         | PLOT
    """
    p[0] = Plot(table='it', file_or_url=clause(p, 'to'), options=clause(p, 'with'))


def p_print(p):
    """
    print : PRINT term FROM ident
    """
    p[0] = Print(table=p[4], term=p[2])


def p_print_it(p):
    """
    print : PRINT term
    """
    p[0] = Print(table='it', term=p[2])


def p_put(p):
    """
    put : PUT ident
    """
    p[0] = Put(table=p[2])


def p_put_it(p):
    """
    put : PUT
    """
    p[0] = Put(table='it')


def p_query(p):
    """
    query : QUERY term FROM ident
          | QUERY MUL FROM ident
    """
    p[0] = Query(term=p[2] if p[2] != '*' else None, source=p[4])


def p_query_table(p):
    """
    query : QUERY term FROM ident '.' ident
          | QUERY MUL FROM ident '.' ident
    """
    p[0] = Query(term=p[2] if p[2] != '*' else None, source=p[4], table=p[6])


def p_quit(p):
    """
    quit : QUIT
    """
    p[0] = Quit()


def p_read(p):
    """
    read : READ term FROM ident
         | READ term FROM ident asinputformat
    """
    p[0] = Read(file_or_url=p[2], table=p[4], dialect=clause(p, 'as'))


def p_read_it(p):
    """
    read : READ term
         | READ term asinputformat
    """
    p[0] = Read(file_or_url=p[2], table='it', dialect=clause(p, 'as'))


def p_rename(p):
    """
    rename : RENAME columnid TO columnid FROM ident
    """
    p[0] = Rename(table=p[6], column=p[2], to=p[4])


def p_rename_it(p):
    """
    rename : RENAME columnid TO columnid
    """
    p[0] = Rename(table='it', column=p[2], to=p[4])


def p_reverse(p):
    """
    reverse : REVERSE ident
    """
    p[0] = Transpose(table=p[2])


def p_reverse_it(p):
    """
    reverse : REVERSE
    """
    p[0] = Transpose(table='it')


def p_run(p):
    """
    run : RUN termlist FROM ident
    """
    p[0] = Run(args=p[2], table=p[4])


def p_run_it(p):
    """
    run : RUN termlist
    """
    p[0] = Run(args=p[2], table='it')


def p_select(p):
    """
    select : SELECT exprlist FROM ident
    """
    p[0] = Select(expressions=p[2], table=p[4])


def p_select_it(p):
    """
    select : SELECT exprlist
    """
    p[0] = Select(expressions=p[2], table='it')
    
    
def p_sh(p):
    """
    sh : SH term FROM ident asinputformat
       | SH term FROM ident
    """
    p[0] = Shell(command=p[2], table=p[4], dialect=clause(p, 'as'))


def p_sh_it(p):
    """
    sh : SH term asinputformat
       | SH term
    """
    p[0] = Shell(command=p[2], table='it', dialect=clause(p, 'as'))


def p_sort(p):
    """
    sort : SORT ident
         | SORT ident orderby
    """
    p[0] = Sort(table=p[2], by=clause(p, 'orderby'))


def p_sort_it(p):
    """
    sort : SORT orderby
    """
    p[0] = Sort(table='it', by=clause(p, 'orderby'))


def p_take(p):
    """
    take : TAKE INTEGER FROM ident
    """
    p[0] = Take(table=p[4], n=p[2])


def p_take_it(p):
    """
    take : TAKE INTEGER
    """
    p[0] = Take(table='it', n=p[2])


def p_take_last(p):
    """
    take : TAKE LAST INTEGER FROM ident
    """
    p[0] = Take(table=p[5], n=p[3], from_end=True)


def p_take_last_it(p):
    """
    take : TAKE LAST INTEGER
    """
    p[0] = Take(table='it', n=p[3], from_end=True)


def p_transpose(p):
    """
    transpose : TRANSPOSE ident
    """
    p[0] = Transpose(table=p[2])


def p_transpose_it(p):
    """
    transpose : TRANSPOSE
    """
    p[0] = Transpose(table='it')


def p_union(p):
    """
    union : UNION ident WITH identlist
    """
    p[0] = Union(tables=[p[2], *p[4]])


def p_union_it(p):
    """
    union : UNION WITH identlist
    """
    p[0] = Union(tables=['it', *p[4]])


def p_write(p):
    """
    write : WRITE ident to asoutputformat
          | WRITE ident to
          | WRITE ident asoutputformat
          | WRITE ident
    """
    p[0] = Write(table=p[2], file_or_url=clause(p, 'to'), dialect=clause(p, 'as'))


def p_write_it(p):
    """
    write : WRITE to asoutputformat
          | WRITE to
          | WRITE asoutputformat
          | WRITE
    """
    p[0] = Write(table='it', file_or_url=clause(p, 'to'), dialect=clause(p, 'as'))


def p_statement(p):
    """
    statement : connect
              | cross
              | distinct
              | drop
              | explode
              | filter
              | help
              | join
              | open
              | plot
              | print
              | put
              | query
              | quit
              | read
              | rename
              | reverse
              | run
              | select
              | sh
              | sort
              | take
              | transpose
              | union
              | write
    """
    p[0] = p[1]


def p_command(p):
    """
    command : statement
    """
    p[0] = (p.lineno(1), p[1], None)


def p_command_into(p):
    """
    command : statement INTO ident
    """
    p[0] = (p.lineno(1), p[1], p[3])


def p_command_create(p):
    """
    command : CREATE ident asinputformat block
            | CREATE ident asinputformat string
    """
    p[0] = (p.lineno(1), Create(dialect=p[3], block=p[4]), p[2])


def p_program(p):
    """
    program : command END program
    """
    p[0] = [p[1], *p[3]]


def p_program_skip(p):
    """
    program : END program
    """
    p[0] = p[2]


def p_program_single(p):
    """
    program : command
    """
    p[0] = [p[1]]


def p_program_empty(p):
    """
    program :
    """
    p[0] = []


def p_error(p):
    """
    Report a syntax error.
    """
    if p is None:
        raise SyntaxError(f'Unexpected end of line {p.lineno}')
    else:
        raise SyntaxError(f'Syntax error on line {p.lineno} near "{p.value}"')


# build the parser
parser = yacc.yacc(start='program', debug=False, write_tables=False)
