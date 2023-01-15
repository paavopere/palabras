import argparse
import json

import rich.console

from . import __version__
from .core import LanguageEntry, WiktionaryPageNotFound, LanguageEntryNotFound, find_entry


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
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args(args)

    console = rich.console.Console()

    try:
        entry = find_entry(word=args.word, language='Spanish', revision=args.revision)
        output = parse(entry, compact=args.compact, use_json=args.json)
        console.print(output, crop=False, overflow='ignore')
        return 0
    except (WiktionaryPageNotFound, LanguageEntryNotFound) as exc:
        print(exc)
        return 1


def parse(entry: LanguageEntry, compact: bool, use_json: bool) -> str:
    if use_json:
        return json.dumps(entry.to_dict(), indent=2)
    elif compact:
        return entry.compact_definition_output()
    else:
        return entry.definition_output()
