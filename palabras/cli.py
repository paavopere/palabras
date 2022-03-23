import argparse

from .core import lookup


def run():
    parser = argparse.ArgumentParser(description='Look up a word')
    parser.add_argument('word', metavar='WORD', type=str, help='a word')
    args = parser.parse_args()
    print(lookup(args.word))
