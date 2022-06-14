import argparse

from .core import WordInfo, WiktionaryPageNotFound, WiktionarySectionNotFound


def main(args):
    formatter = lambda prog: argparse.HelpFormatter(prog, max_help_position=50)
    parser = argparse.ArgumentParser(description='Look up a word', formatter_class=formatter)
    parser.add_argument('word', metavar='<word>', type=str, help='A word to look up')
    parser.add_argument('-r', '--revision', type=int, metavar='<n>', help='Wiktionary revision ID (from permalink)')
    args = parser.parse_args(args)
    
    try:
        print(parse(WordInfo.from_search(args.word, revision=args.revision)))
        return 0
    except (WiktionaryPageNotFound, WiktionarySectionNotFound) as exc:
        print(exc)
        return 1


def parse(word_info: WordInfo) -> str:
    lines = [word_info.word]
    lines += [f'- {ds}' for ds in word_info.definition_strings]
    return '\n'.join(lines)