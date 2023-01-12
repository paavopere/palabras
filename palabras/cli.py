import argparse

import rich.console

from . import __version__
from .core import WordInfo, WiktionaryPageNotFound, LanguageEntryNotFound


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
        word_info = WordInfo.from_search(args.word, revision=args.revision)
        output = parse(word_info, compact=args.compact, json=args.json)
        console.print(output, crop=False, overflow='ignore')
        return 0
    except (WiktionaryPageNotFound, LanguageEntryNotFound) as exc:
        print(exc)
        return 1


def parse(word_info: WordInfo, compact: bool, json: bool) -> str:
    if json:
        return word_info.json_output()
    elif compact:
        return word_info.compact_definition_output()
    else:
        return word_info.definition_output()
