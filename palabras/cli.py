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
        '--experimental',
        action='store_true',
        help='Use experimental features (may be unstable)',
    )
    parser.add_argument('--json', action='store_true', help='Output as JSON')
    args = parser.parse_args(args)

    console = rich.console.Console()

    try:
        entry = find_entry(word=args.word, language='Spanish', revision=args.revision)
        parsed = parse(
            entry,
            compact=args.compact,
            use_json=args.json,
            experimental=args.experimental,
        )
        if isinstance(parsed, str):
            parsed = [parsed]
        console.print(*parsed, crop=False, overflow='ignore', sep='\n')
        return 0
    except (WiktionaryPageNotFound, LanguageEntryNotFound) as exc:
        print(exc)
        return 1


def parse(
    entry: LanguageEntry, compact: bool, use_json: bool, experimental: bool
) -> Union[str, list]:
    if use_json:
        return json.dumps(entry.to_dict(), indent=2)
    elif compact:
        return RichCLIRenderer().render_compact(entry.to_dict())
    elif experimental:
        return "nothing experimental at the moment"  # pragma: no cover
    else:
        return RichCLIRenderer().render(entry.to_dict())
