import csv
import orjson
import os.path
import pandas as pd
import urllib.parse


# create aliases for common csv file extensions
csv.register_dialect('csv', csv.excel)
csv.register_dialect('tsv', csv.excel_tab)
csv.register_dialect('vcf', csv.excel_tab)
csv.register_dialect('bed', csv.excel_tab)


class Dialect:
    """
    Handles reading/writing data of a known, registered format.
    """

    @property
    def suffix(self):
        raise NotImplementedError

    def read(self, file, limit=None):
        """
        Loads a table into memory from the location.
        """
        raise NotImplementedError

    def write(self, df, file):
        """
        Writes the table to a file.
        """
        raise NotImplementedError

    @staticmethod
    def infer(location):
        """
        Return a format to use for the filename provided.
        """
        url = urllib.parse.urlparse(location)
        path = url.path

        # try and infer using an extension
        while path and '.' in path:
            path, ext = os.path.splitext(path)
            ext = ext[1:].lower()

            # is it JSON?
            if ext.startswith('json'):
                return JSONLines() if 'l' in ext else JSON()

            # is it a registered CSV dialect?
            csv_dialect = csv.get_dialect(ext)
            if csv_dialect is not None:
                return CSV(
                    sep=csv_dialect.delimiter,
                    linesep=csv_dialect.lineterminator,
                    quotechar=csv_dialect.quotechar,
                    escapechar=csv_dialect.escapechar,
                )

        # unablet to infer
        return None


class CSV(Dialect):
    """
    Read CSV/TSV files.
    """

    def __init__(self, sep=',', linesep='\n', quotechar='"', escapechar=None, header=True, comment=None):
        """
        Initialize the dialect.
        """
        self.header = header
        self.sep = sep
        self.linesep = linesep
        self.quotechar = quotechar
        self.escapechar = escapechar
        self.comment = comment

    @property
    def suffix(self):
        return ".csv"

    def read(self, file, limit=None):
        return pd.read_csv(
            file,
            header=0 if self.header else None,
            sep=self.sep,
            quotechar=self.quotechar,
            doublequote=self.escapechar is None,
            escapechar=self.escapechar,
            comment=self.comment,
            delim_whitespace=self.sep is None,
        )

    def write(self, df, file):
        df.to_csv(
            file,
            index=False,
            header=bool(self.header),
            sep=self.sep,
            line_terminator=self.linesep,
            quotechar=self.quotechar,
            doublequote=self.escapechar is None,
            escapechar=self.escapechar,
        )


class JSON(Dialect):
    """
    Read/write JSON files.
    """

    @property
    def suffix(self):
        return ".json"

    def read(self, file):
        data = orjson.loads(file.read())

        # no data is an empty dataframe
        if not data:
            return pd.DataFrame()

        # ensure the data is a list of data
        if not isinstance(data, list):
            data = [data]

        # lists of records should be normalized
        if isinstance(data[0], dict):
            return pd.json_normalize(data)

        # simple frame
        return pd.DataFrame(data)

    def write(self, df, file):
        df.to_json(file, orient='records')

        # output an extra line at the end
        print(file=file)


class JSONLines(Dialect):
    """
    Read/write JSON files as a JSON-lines.
    """

    @property
    def suffix(self):
        return ".json"

    def read(self, file):
        return pd.read_json(file, lines=True)

    def write(self, df, file):
        df.to_json(file, orient='records', lines=True)

        # output an extra line at the end
        print(file=file)


class HTML(Dialect):
    """
    Write HTML files.
    """

    @property
    def suffix(self):
        return ".html"

    def write(self, df, file):
        df.to_html(file, index=False)
