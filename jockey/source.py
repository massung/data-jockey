import sqlalchemy


class DataSource:
    """
    A source is any database-like connection that can take
    an arbitrary string and return an array of records.
    """

    def query(self, q, table=None):
        """
        Return a table capable of perform a select query.
        """
        raise NotImplementedError

    def close(self):
        """
        Terminate the connection to the data source.
        """
        pass


class SQLSource(DataSource):
    """
    A SQLAlchemy connection to a database.
    """

    def __init__(self, connection_string):
        """
        Connect to the database.
        """
        self.engine = sqlalchemy.create_engine(connection_string)

        if self.engine is None:
            raise RuntimeError(f'Failed to connect to {connection_string}')

    def query(self, q, table):
        sql = f'SELECT * FROM {table} '
        
        # optional condition
        if q is not None:
            sql += f'WHERE {q}'

        # run the query
        resp = self.engine.execute(sql)

        # convert each record into a dictionary
        return (dict(r) for r in resp.fetchall())

    def close(self):
        """
        Terminate the connection to the data source.
        """
        self.engine.dispose()
