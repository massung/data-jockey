import asyncio
import io
import os
import pandas as pd
import re
import smart_open
import sys
import tempfile

from dataclasses import dataclass
from typing import Union

from .context import Context
from .dialect import Dialect
from .functions import series_function
from .source import SQLSource
from .term import Term
from .utils import create_frame


class Statement:
    """
    Compiled statements to execute with a Context object.
    """

    async def execute(self, context):
        """
        An empty statement.
        """
        pass


@dataclass
class Connect(Statement):
    """
    Establishes a connection to a remote repository of data.

    Once a connection has been established, a table can be read
    from using the SELECT command, with the connection identifier
    prefixed.

    Valid connection types are:

      SQL - connects to any SQL-compliant database

    Syntax:
      CONNECT source TO url AS type

    Examples:
      CONNECT db TO "mysql://username:password@example.com/db" AS SQL
    """
    alias: str
    url: str
    kind: str

    async def execute(self, context):
        assert context.allow_connect, 'CONNECT permission disabled'

        if self.kind == 'SQL':
            source = SQLSource(self.url)

            if source is not None:
                context.register(self.alias, source)


@dataclass
class Create(Statement):
    """
    Declares a literal table.

    Syntax:
      CREATE ident AS dialect ...

    Examples:
      CREATE people AS CSV WITH HEADER << END
      name,age
      Jeff,44
      Isabel,11
      Bob,23
      END
    """
    dialect: Dialect
    block: str

    async def execute(self, context):
        return self.dialect.read(io.StringIO(self.block.strip()))


@dataclass
class Distinct(Statement):
    """
    Removes duplicate records from a table.

    Syntax:
      DISTINCT [table] [BY (* | column, ...)] [KEEP (FIRST | LAST)]

    Examples:
      DISTINCT people BY age FROM people KEEP LAST
      DISTINCT dates
    """
    table: str
    columns: Union[str, list]
    keep: str = None

    async def execute(self, context):
        df = context.frames[self.table]
        subset = None if '*' in self.columns else self.columns

        # default to keeping the first record
        return df.drop_duplicates(subset=subset, keep=self.keep or 'first')


@dataclass
class Drop(Statement):
    """
    Removes columns from a table.

    Syntax:
      DROP column, ... [FROM table]

    Examples:
      DROP age FROM people
    """
    columns: list
    table: str
    into: str = None

    async def execute(self, context):
        return context.frames[self.table].drop(columns=self.columns)


@dataclass
class Explode(Statement):
    """
    Explodes list values of a column from a table into rows.

    Syntax:
      EXPLODE column [FROM table]

    Examples:
      EXPLODE ages FROM people
    """
    column: Union[str,int]
    table: str

    async def execute(self, context):
        return context.frames[self.table].explode(self.column, ignore_index=True)


@dataclass
class Filter(Statement):
    """
    Selects all records from a table matching an expression.

    Syntax:
      FILTER term, ... [FROM table]

    Examples:
      FILTER age > 14 AND gender = 'M' FROM people
    """
    where: Term
    table: str

    async def execute(self, context):
        df = context.frames[self.table]

        # filter the table
        return df[self.where.evaluate(df)]


@dataclass
class Help(Statement):
    """
    Outputs a list of all possible commands.

    HELP [command]
    """
    command: str = None

    def __post_init__(self):
        """
        Force uppercase the command name.
        """
        if self.command is not None:
            self.command = self.command.upper()

    async def execute(self, context):
        commands = Statement.__subclasses__()

        # output all the commands in alphabetical order
        for cls in sorted(commands, key=lambda c: c.__name__):
            name = cls.__name__.upper()
            lines = [s.strip() for s in cls.__doc__.splitlines(keepends=False)]

            # the first line is a help string, the rest are usage examples.
            [help_str, *docs] = lines[1:]

            # show help string of every command?
            if self.command is None:
                print(f'{name:>12}   {help_str}')
            elif self.command == name:
                print(f'{name} {help_str.lower()}')

                # output documentation of statement
                for line in docs:
                    if re.match(r'^[a-z]+:$', line, re.IGNORECASE):
                        print(f'{line}')
                    else:
                        print(f'  {line}')

                # no more help
                return

        # indicate if the command wasn't found
        if self.command:
            print(f'No HELP exists for {self.command}')


@dataclass
class Join(Statement):
    """
    Merges the columns of two tables together.

    If no join type (inner, outer, left, right) is specified,
    then INNER is used.

    Syntax:
            JOIN [table] WITH table [ON column, ...]
      INNER JOIN [table] WITH table [ON column, ...]
      OUTER JOIN [table] WITH table [ON column, ...]
       LEFT JOIN [table] WITH table [ON column, ...]
      RIGHT JOIN [table] WITH table [ON column, ...]

    Examples:
      JOIN employees WITH salaries ON id
      LEFT JOIN WITH people ON gender
    """
    table: str
    how: str
    other: str
    on: list = None

    async def execute(self, context):
        left = context.frames[self.table]
        right = context.frames[self.other]

        # merge into a new table
        return left.merge(right, on=self.on, how=self.how)


@dataclass
class Open(Statement):
    """
    Opens a table in a the default editor.

    Syntax:
      OPEN [table] [AS format]

    See:
      READ for available formats.

    Examples:
      OPEN associations AS JSON
      OPEN AS CSV FIELD DELIMITER TAB
      OPEN people AS HTML
    """
    table: str
    dialect: Dialect = None

    async def execute(self, context):
        df = context.frames[self.table]
        file = tempfile.NamedTemporaryFile(
            suffix=self.dialect.suffix,
            encoding='utf-8',
            mode='w',
            newline='',
            delete=False,
        )

        # write the table to the location
        self.dialect.write(df, file=file)
        file.close()

        # launch editor
        os.startfile(file.name)


@dataclass
class Print(Statement):
    """
    Outputs a single value to the console.

    Syntax:
      PRINT term [FROM table]

    Examples:
      PRINT "$last, $first" from names
    """
    table: str
    term: Term

    async def execute(self, context):
        df = context.frames[self.table]
        x = self.term.evaluate(df)

        if isinstance(x, pd.Series):
            for i in x:
                print(str(i))
        else:
            print(str(x))


@dataclass
class Put(Statement):
    """
    Returns a table.

    This is useful if you need to assign a table to another
    name (e.g. `PUT it INTO x`).

    Syntax:
      PUT table

    Examples:
      PUT it
    """
    table: str

    async def execute(self, context):
        return context.frames[self.table]


@dataclass
class Query(Statement):
    """
    Query a connected, remote data source.

    Both the syntax of the query string and the (optional) table
    name are based on the type of data source registered, and
    can be arbitrary.

    If the table is not provided, it is expected that the registered
    source knows what to do.

    For a SQL data source, the query string is the WHERE clause
    of a SQL SELECT statement and the table name is required.

    Syntax:
      QUERY term FROM source [.table]

    Examples:
      QUERY "age > 40" FROM work.employees
    """
    term: Term
    source: str
    table: str = None

    async def execute(self, context):
        df = context.it
        source = context.sources[self.source]
        query = self.term.evaluate(df)

        # get the resulting data/series
        data = await asyncio.to_thread(self.runquery, query, source, self.table)

        # a single dataframe should be returned as-is
        if isinstance(data, pd.DataFrame):
            return data

        # union results together
        return pd.concat(data.array, ignore_index=True)

    @staticmethod
    @series_function()
    def runquery(q, source, table):
        """
        Execute the query.
        """
        records = source.query(q, table=table)

        # convert the results to a dataframe
        return pd.DataFrame(records)


@dataclass
class Quit(Statement):
    """
    Terminates the console or running script.

    Syntax:
      QUIT
    """

    async def execute(self, context):
        sys.exit(0)


@dataclass
class Read(Statement):
    """
    Loads data from a URI location into a table.

    The URI can be any local file or URI understood by the Python
    library smart_open.

    If no format is provided, the file extension is used to infer
    the format. Otherwise, the format should follow one of the
    following syntax rules:

    .. AS CSV [options]
    .. AS JSON [LINES]

    The CSV format allows for the following, optional arguments
    in any order to be present:

    .. (WITH | NO) HEADER
    .. FIELD DELIMITER string
    .. LINE DELIMITER string
    .. QUOTE string

    If the file extension indicates that it is compressed as either
    gzip and bz2 then it will be decompressed while reading.

    See:
      https://pypi.org/project/smart-open
      https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_json.html

    Syntax:
      READ file_or_uri [FROM table] [AS format]

    Examples:
      READ 'https://hacker-news.firebaseio.com/v0/topstories.json' AS JSON RECORDS
      READ 's3://bucket/table.csv.gz' AS CSV FIELD DELIMITER '|' WITH HEADER
      READ "$_1" FROM file_list
    """
    file_or_url: Term
    table: str
    dialect: Dialect = None

    async def execute(self, context):
        assert context.allow_read, 'READ permission disabled'

        # fetch source file
        df = context.frames[self.table]
        source = self.file_or_url.evaluate(df)

        # get the resulting data/series
        data = await asyncio.to_thread(self.read, source, self.dialect)

        # a single dataframe should be returned as-is
        if isinstance(data, pd.DataFrame):
            return data

        # union results together
        return pd.concat(data.array, ignore_index=True)

    @staticmethod
    @series_function()
    def read(source, dialect):
        if dialect is None:
            dialect = Dialect.infer(source)

        # open the source location
        with smart_open.open(source, encoding='utf-8') as fp:
            df = dialect.read(fp)

        # renamed columns
        columns = {k: f'_{k}' for k in df.columns if isinstance(k, int)}

        # rename any integer columns to strings
        return df.rename(columns=columns)


@dataclass
class Rename(Statement):
    """
    Renames a column in a table.

    Syntax:
      RENANE column TO column [FROM table]

    Examples:
      RENAME :0 TO name
    """
    table: str
    column: str
    to: str

    async def execute(self, context):
        return context.frames[self.table].rename(columns={self.column: self.to})


@dataclass
class Reverse(Statement):
    """
    Inverts the order of records in a table.

    Syntax:
      REVERSE [table]
    """
    table: str

    async def execute(self, context):
        return context.frames[self.table].iloc[::-1]


@dataclass
class Run(Statement):
    """
    Executes a script at the given URI location.

    Syntax:
      RUN file_or_url [, ...] [FROM table]

    Examples:
      RUN 'script.pql'
      RUN 's3://bucket/script.pql', "-c", 10*20
      RUN 'ftp://example.com/script.pql'
      RUN 'http://example.com/script.pql'
    """
    table: str
    args: list

    async def execute(self, context):
        assert context.allow_run, 'RUN permission disabled'

        # fetch the table to interpolate from
        df = context.frames[self.table]

        # explode the arguments and run all rows
        args = [arg.evaluate(df) for arg in self.args]
        data = await self.run(context, *args)

        # empty frame if no result
        if data is None:
            return pd.DataFrame()

        # a single dataframe should be returned as-is
        if isinstance(data, pd.DataFrame):
            return data

        # remove NA results from a series of results
        data = data.dropna()
        if data.empty:
            return pd.DataFrame()

        # union results together
        return pd.concat(data.array, ignore_index=True)

    @staticmethod
    @series_function()
    def run(context, *args):
        from .script import Script

        script = Script(context=Context(parent_context=context, argv=args))
        script.load(args[0])

        return script.run_async()


@dataclass
class Select(Statement):
    """
    Creates a new table of named terms.

    Syntax:
      SELECT (* | term [AS name]), ... [FROM table]

    Examples:
      SELECT 2 * 10 AS twenty
      SELECT age, salary FROM employees
      SELECT name, age > 20, 'test'
    """
    table: str
    expressions: list

    async def execute(self, context):
        df = context.frames[self.table]

        # create a new table for the result
        columns = []

        # add all the other expressions to the resulting frame
        for expr in self.expressions:
            if expr == '*':
                columns.extend((col, df[col]) for col in df.columns)
            else:
                value = expr.evaluate(df)
                column = f'_{len(columns)}'

                # use series name?
                if isinstance(value, pd.Series):
                    column = value.name or column

                # add the resulting value with the column name
                columns.append((expr.alias or column, value))

        # create the resulting frame
        return create_frame(columns)


@dataclass
class Sort(Statement):
    """
    Sorts a table by one or more columns.

    Syntax:
      SORT table [BY column [(ASC | DESC)], ...]

    Examples:
      SORT it BY age
      SORT people BY gender, age DESC
    """
    table: str
    by: list

    async def execute(self, context):
        df = context.frames[self.table]
        by = self.by

        # special case, if no columns, use the first one
        if len(by) == 0:
            by = [(df.columns[0], True)]

        # partition the by ordering into columns and direction
        columns = [b[0] for b in by]
        ascending = [b[1] for b in by]

        return df.sort_values(by=columns, ascending=ascending)


@dataclass
class Take(Statement):
    """
    Returns the first (or last) N records from a table.

    Syntax:
      TAKE [LAST] n [FROM table]

    Examples:
      TAKE 5 FROM people
      TAKE LAST 5
    """
    n: int = 10
    table: str = None
    from_end: bool = False

    async def execute(self, context):
        df = context.frames[self.table or 'it']

        # optionally take from the end
        return df.tail(n=self.n) if self.from_end else df.head(n=self.n)


@dataclass
class Transpose(Statement):
    """
    Exchanges the row and column indices of a table.

    Syntax:
      TRANSPOSE [table]
    """
    table: str

    async def execute(self, context):
        return context.frames[self.table].transpose()


@dataclass
class Union(Statement):
    """
    Concatenates multiple tables together into a single table.

    Syntax:
      UNION table, ...

    Examples:
      UNION a, b, c
    """
    tables: list

    async def execute(self, context):
        return pd.concat(context.frames[table] for table in self.tables)


@dataclass
class Write(Statement):
    """
    Saves the contents of a table to a URI location.

    If the file extension includes '.gz' or 'bz2' the the table
    will be written compressed.

    If no TO destination is specified, then the contents are
    written to standard out.

    Syntax:
      WRITE [table] [TO term] [AS format]

    See:
      READ for available URI locations and file formats.

    Examples:
      WRITE associations TO 'assoc.json' AS JSON LINES
      WRITE TO 's3://bucket/table.tsv.gz' AS CSV FIELD DELIMITER TAB
      WRITE people TO 'workers.csv' AS CSV WITH HEADER
    """
    table: str
    file_or_url: Term = None
    dialect: Dialect = None

    async def execute(self, context):
        df = context.frames[self.table]
        dialect = self.dialect

        if self.file_or_url:
            value = self.file_or_url.evaluate(context.it)
            file_or_url = value[0] if isinstance(value, pd.Series) else value
        else:
            file_or_url = None

        # infer formatter from file extension
        if dialect is None:
            dialect = Dialect.infer(file_or_url)

        # write the table to the location
        if file_or_url is None:
            dialect.write(df, file=sys.stdout)
        else:
            with smart_open.open(file_or_url, encoding='utf-8', mode='w', newline='') as fp:
                dialect.write(df, file=fp)
