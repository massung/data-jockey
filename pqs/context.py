import pandas as pd


from .utils import create_frame


class Context:
    """
    Script context.
    """

    def __init__(self, parent_context=None, argv=None, allow_read=True, allow_connect=True, allow_run=True):
        """
        Initialize the context. If present, data should be a list of
        (value, column_name) tuples.
        """
        self.frames = (parent_context and parent_context.frames) or {}
        self.sources = (parent_context and parent_context.sources) or {}

        # create the ARGV list for the 'it' frame
        self.it = pd.DataFrame([(argv or [],)], columns=['ARGV'])

        # execution permissions
        self.allow_read = allow_read
        self.allow_connect = allow_connect
        self.allow_run = allow_run

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

    def clear(self):
        """
        Reset the context and connected sources.
        """
        self.frames = dict(it=pd.DataFrame())
        self.sources = dict()

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
