import pandas as pd

from concurrent.futures import ThreadPoolExecutor


class Context:
    """
    Script context.
    """

    def __init__(self, parent_context=None, env=None, argv=None, allow_read=True, allow_connect=True, allow_run=True):
        """
        Initialize the context.

        If the `parent_context` is provided, all the frames and sources of it
        will be inherited by this context.

        The `env` argument initializes the ENV frame with a column per key.

        The `argv` list - if provided - will add an ARGV column to the ENV
        frame with an array of arguments.

        The `allow_*` parameters are for security, allowing you to disable
        script access to the READ, CONNECT, and RUN commands.
        """
        self.frames = (parent_context and parent_context.frames) or {}
        self.sources = (parent_context and parent_context.sources) or {}

        # create the environment dictionary
        self.env = {}
        if parent_context:
            self.env.update(parent_context.env)
        if env:
            self.env.update(env)

        # build the environment frame
        self.frames['ENV'] = pd.DataFrame([self.env.values()], columns=self.env.keys())

        # add arguments column to the environment
        self.frames['ENV']['ARGV'] = pd.Series([argv or []])

        # create the 'it' table
        self.it = pd.DataFrame()

        # execution permissions
        self.allow_read = allow_read
        self.allow_connect = allow_connect
        self.allow_run = allow_run

        # create a thread pool for vectorized commands
        self.thread_pool = parent_context.thread_pool if parent_context else ThreadPoolExecutor(max_workers=20)

    @property
    def it(self):
        """
        Returns the value of it in the context.
        """
        return self.frames['it']

    @it.setter
    def it(self, df):
        """
        Sets the value of it in the context.
        """
        self.frames['it'] = df

    def register(self, name, source):
        """
        Define a named source.
        """
        self.sources[name] = source

    def close(self, name):
        """
        Remove a named source.
        """
        self.sources[name].close()

        # remove the source from the dictionary
        del self.sources[name]
