import argparse
import json
from typing import Union

import rich.console

from . import __version__
from .core import (
    LanguageEntry,
    RichCLIRenderer,
    WiktionaryPageNotFound,
    LanguageEntryNotFound,
    find_entry,
)


def main(args):
    parser = argparse.ArgumentParser(
        prog='palabras',
        description='Look up a word',
        formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=50),
    )
    parser.add_argument('word', metavar='<word>', type=str, help='A word to look up')
    parser.add_argument(
        '-V', '--version', action='version', version=f'%(prog)s {__version__}'
    )
    parser.add_argument(
        '--language', '-l',
        type=str,
        help='Language to look up',
        default='Spanish',
    )
    parser.add_argument(
        '-r',
        '--revision',
        type=int,
        metavar='<n>',
        help='Wiktionary revision ID (from permalink)',
    )
    parser.add_argument(
        '--compact',
        action='store_true',
        help='List definitions for all parts of speech together',
    )

    parser.add_argument(
        '-e', '--etymology',
        action='store_true',
        help='Show etymology',
    )
    parser.add_argument(
        '-p', '--pronunciation',
        action='store_true',
        help='Show pronunciation',
    )
    parser.add_argument(
        '-c', '--conjugation',
        action='store_true',
        help='Show conjugation',
    )
    parser.add_argument(
        '-x', '--examples',
        action='store_true',
        help='Show examples',
    )

    parser.add_argument(
        '-j', '--json',
        action='store_true',
        dest='output_json',
        help='Output as JSON',
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information',
    )

    arg_dict = vars(parser.parse_args(args))
    lookup_options = {
        k: v
        for k, v in arg_dict.items()
        if k in ('word', 'language', 'revision')}
    render_options = {
        k: v
        for k, v in arg_dict.items()
        if k in ('compact', 'etymology', 'pronunciation', 'conjugation', 'examples', 'output_json')}

    console = rich.console.Console()
    if arg_dict['debug']:
        console.print(arg_dict)  # pragma: no cover

    try:
        entry = find_entry(**lookup_options)
        output = render(entry, **render_options)
        if isinstance(output, str):
            output = [output]
        console.print(*output, crop=False, overflow='ignore', sep='\n')
        return 0
    except (WiktionaryPageNotFound, LanguageEntryNotFound) as exc:
        print(exc)
        return 1


def render(
    entry: LanguageEntry,
    output_json: bool,
    **options
) -> Union[str, list]:
    data = entry.to_dict()
    if output_json:
        return json.dumps(data, indent=2)
    else:
        return RichCLIRenderer(options).render(data)
