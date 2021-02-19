import asyncio
import click
import dotenv
import os
import sys

from .console import console
from .context import Context
from .script import Script


MAJOR_VERSION=0
MINOR_VERSION=1


async def repl(env=None, show_motd=True):
    """
    Read-eval-print loop.
    """
    if show_motd:
        print(f'Flummox {MAJOR_VERSION}.{MINOR_VERSION}')

    # create a new scripting context
    script = Script(context=Context(env={**os.environ, **(env or {})}))

    while True:
        try:
            # parse the line into the script
            script.loads(console.input('[green]>> [/]'))
            result = await script.run_async()

            if result is not None:
                console.print(result, highlight=False, markup=False, emoji=False)
        except Exception as ex:
            console.print(f'[red]{ex}[/]')


@click.command()
@click.option('--env-file', '-e')
@click.argument('args', nargs=-1)
def cli(env_file, args):
    """
    Entry point.
    """
    env = None

    if env_file:
        env = dotenv.dotenv_values(env_file)

    if not args:
        asyncio.run(repl(env=env))
    else:
        script = Script(context=Context(env=env, argv=args))

        try:
            script.load(args[0])
            script.run()
        except Exception as ex:
            print(ex, file=sys.stderr)


if __name__ == '__main__':
    cli()
