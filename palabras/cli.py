import argparse

from .core import WordInfo


def main(args):
    parser = argparse.ArgumentParser(description='Look up a word')
    parser.add_argument('word', metavar='WORD', type=str, help='a word')
    args = parser.parse_args(args)
    
    print(parse(WordInfo.from_search(args.word)))


def parse(word_info: WordInfo) -> str:
    lines = [word_info.word]
    lines += [f'- {ds}' for ds in word_info.definition_strings]
    return '\n'.join(lines)