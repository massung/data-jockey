import asyncio
import click
import dotenv
import sys

from .console import console
from .context import Context
from .script import Script


MAJOR_VERSION=0
MINOR_VERSION=1


async def repl(show_motd=True):
    """
    Read-eval-print loop.
    """
    if show_motd:
        print(f'Python/Pandas Query Script {MAJOR_VERSION}.{MINOR_VERSION}')

    # create a new scripting context
    script = Script()

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
@click.option('--debug', '-d')
@click.argument('args', nargs=-1)
def cli(env_file, debug, args):
    """
    Entry point.
    """
    if env_file:
        dotenv.load_dotenv(env_file)

    if not args:
        asyncio.run(repl())
    else:
        script = Script(context=Context(argv=args))

        try:
            script.load(args[0])
            script.run()
        except Exception as ex:
            print(ex, file=sys.stderr)


if __name__ == '__main__':
    cli()
