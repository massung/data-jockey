import asyncio
import os
import smart_open

from .context import Context
from .lexer import lexer
from .parser import parser


class Script:
    """
    Script can read/load scripts and execute them.
    """

    def __init__(self, context=None):
        """
        Initialize the script runner.
        """
        self.context = context or Context()
        self.statements = []
        self.source = None

    def load(self, file_or_url):
        """
        Opens a file/URL and reads the script into the script.
        """
        with smart_open.open(file_or_url, encoding='utf-8') as fp:
            self.loads(fp.read(), source=file_or_url)

    def loads(self, string, source=None):
        """
        Parse a script.
        """
        try:
            self.statements = parser.parse(string, lexer=lexer, tracking=True)
            self.source = source
        except SyntaxError as ex:
            raise SyntaxError(f'{source}: {ex}') if source else ex

    def run(self, **run_kwargs):
        """
        Executes the loaded script using the current context.
        """
        return asyncio.run(self.run_async(), **run_kwargs)

    async def run_async(self, env=None):
        """
        Executes the loaded script using the current context asynchronously.
        """
        old_cwd = os.getcwd()
        old_env = dict(os.environ)

        # temporarily update the environment
        if env:
            for k, v in env.items():
                os.environ[k] = v

        try:
            result = None

            # change directory to the current source
            if self.source:
                path = os.path.dirname(self.source)

                if path:
                    os.chdir(path)

            # run all statements
            for line, statement, into in self.statements:
                try:
                    result = await statement.execute(self.context)

                    # update the context
                    if result is not None:
                        self.context.it = result

                        if into is not None:
                            self.context.frames[into] = self.context.it
                except KeyError as ex:
                    raise RuntimeError(f'{self.source} ({line}): Unknown table/column {ex}')
                except Exception as ex:
                    raise RuntimeError(f'{self.source} ({line}): {ex}') if self.source else ex

            return result
        finally:
            os.chdir(old_cwd)
            os.environ = old_env
