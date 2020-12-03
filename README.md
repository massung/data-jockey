# Python/Pandas Query Scripting

PQS is a simple, non-branching, immutable, scripting language that reads tabular data and generates new tabular data from it using simple, SQL-like commands.

__Non-branching__

There are no `IF` statements or loops in PQS. However, all statements are vectorized. This means that if you supply a column of values in to a statement it will execute the statement once per value in the column. For example:

__Immutable__

No table data can be overwritten or changed. Every operation generates a new, immutable table as a result.

## Basics of PQS

At its core a PQS script simply loads tabular data, extracts bits, performs various options or transforms on it, and then either return or write the results to another location.

### An Example

Here's an example script the reads the top 20 stories from Hacker News and outputs them to the terminal in CSV format:

```
READ "https://hacker-news.firebaseio.com/v0/topstories.json"
TAKE 20

# download each story
READ "https://hacker-news.firebaseio.com/v0/item/$_0.json"

# keep stories with links by and sort by score
FILTER type='story' and url is not null
SORT BY score DESC

# output the score and title
SELECT score, title, url

# dump to the terminal
WRITE AS CSV WITH HEADER
```

### Results, it, and named tables

Interesting points of interest from the above script:

* Every command implicitly stores its result in `it`.
* Every command implicitly uses `it` for its input if not provided a table.
* Every command is vectorized; if a parameter is a series, the output will also be.

The output of every command can be redirected to any named variable using `INTO`. For example:

```
SORT employees BY salary DESC INTO `top-salaries`

TAKE 10 FROM `top-salaries` INTO highest_salaried_employees
TAKE LAST 10 FROM `top-salaries` INTO lowest_salaried_employees
```

## Setup

It's not up on PyPI (yet), but you can still install it using pip:

```bash
$ pip install git+git://github.com/massung/python-pqs.git@master#egg=pqs
```

Or, if you can't get that to work, simply clone and install with setup.py:

```bash
$ git clone https://github.com/massung/python-pqs.git
$ cd python-pqs
$ python ./setup.py install
```

## Quickstart

Once installed, you should be able to run the PQS REPL:

```bash
$ pqs
Python/Pandas Query Script 0.1
>> select 1+1
   _0
0   2
```

The HELP command can be used to display the list of all commands available and get detailed syntax and examples for each command:

```bash
>> help
     CONNECT   Establishes a connection to a remote repository of data.
      CREATE   Declares a literal table.
    DISTINCT   Removes duplicate records from a table.
        DROP   Removes columns from a table.
     EXPLODE   Explodes list values of a column from a table into rows.
      FILTER   Selects all records from a table matching an expression.
        HELP   Outputs a list of all possible commands.
        JOIN   Merges the columns of two tables together.
        OPEN   Opens a table in a the default editor.
       PRINT   Outputs a single value to the console.
         PUT   Returns a table.
       QUERY   Query a connected, remote data source.
        QUIT   Terminates the console or running script.
        READ   Loads data from a URI location into a table.
      RENAME   Renames a column in a table.
     REVERSE   Inverts the order of records in a table.
         RUN   Executes a script at the given URI location.
      SELECT   Creates a new table of named terms.
        SORT   Sorts a table by one or more columns.
        TAKE   Returns the first (or last) N records from a table.
   TRANSPOSE   Exchanges the row and column indices of a table.
       UNION   Concatenates multiple tables together into a single table.
       WRITE   Saves the contents of a table to a URI location.

>> help take
TAKE returns the first (or last) n records from a table.

Syntax:
  TAKE [LAST] n [FROM table]

Examples:
  TAKE 5 FROM people
  TAKE LAST 5
```

In addition to the REPL, you can use PQS to run a script and even send arguments to it:

```bash
$ pqs my_script.pqs arg1 arg2 arg3
```

## Loading Data

There are multiple methods of loading/reading data in PQS:

* Declare literal data with the CREATE command;
* Load data with the READ command;
* Fetch data from a connected source with the QUERY command;

### Declare Literal Data

Using the CREATE command, you can create a named table with literal data as if it was read from a file on disk.

```
CREATE snps AS CSV WITH HEADER << END
dbSNP
rs7523141
rs1260326
rs147890266
END
```

_Note: the REPL does not yet support the CREATE command with multi-line blocks._

### Load Data

Using the READ command, you can load local data from disk or even remote data hosted elsewhere (including REST APIs):

```
READ 'data/employees.csv' AS CSV WITH HEADER INTO employees
READ 'https://hacker-news.firebaseio.com/v0/topstories.json' INTO ids
READ 's3://my-bucket/my-file.csv.gz'
```

If no AS clause is provided, then the type of data is inferred from the file extension (or MIME type if a remote request). If the file is compressed, it will be automatically decompressed.

### Fetch From a Connected Source

PQS has an abstract type called `DataSource` that can be subclassed and implemented. This can be used to CONNECT to a named data source (either in script or programatically in Python) and then queried. The meaning of the query is entirely unique to the `DataSource`, but can be any term (number, string, ..).

PQS comes with a very simple `SQLDataSource` that allows for connecting to a SQL database supported by [SQLAlchemy][sqlalchemy] and selecting from a specific table. For example:

```
CONNECT mydb TO "mysql://username:password@host:port/dbname" AS SQL
QUERY "age > 45" FROM mydb.people
```

_Note: The default SQLDataSource makes no effort to sanitize query input or to prevent SQL-injection attacks. The connection requires a username and password, and if the user has that already it doesn't really matter._

## Embedding

While PQS works great as a REPL and a simple scripting language for processing tabular data, it also can be embedded in your own Python projects, giving you and other users the ability to script processing of data.



# Dependencies

* [Python 3.9+][python]
* [setuptools][setuptools]
* [pandas][pandas]
* [python-dotenv][dotenv]
* [click][click]
* [ply][ply]
* [sqlalchemy][sqlalchemy]
* [rich][rich]
* [requests][requests]

# fin.

[python]: https://www.python.org/
[setuptools]: https://setuptools.readthedocs.io/en/latest/
[dotenv]: https://saurabh-kumar.com/python-dotenv/
[click]: https://click.palletsprojects.com/en/7.x/quickstart/
[rich]: https://rich.readthedocs.io/en/latest/
[sqlalchemy]: http://www.sqlalchemy.org/
[requests]: https://requests.readthedocs.io/en/master/
[ply]: https://ply.readthedocs.io/en/latest/index.html
[pandas]: https://pandas.pydata.org/
