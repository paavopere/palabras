# palabras
(WIP) CLI app to look up Spanish words on Wiktionary

[![PyPI version](https://badge.fury.io/py/palabras.svg)](https://badge.fury.io/py/palabras)

[![Tests](https://github.com/paavopere/palabras/actions/workflows/tests.yml/badge.svg)](https://github.com/paavopere/palabras/actions/workflows/tests.yml)

## Usage

Call from command line like this:
```
> python -m palabras olvidar
olvidar
- (transitive) to forget (be forgotten by)
- (reflexive, intransitive) to forget, elude, escape
- (with de, reflexive, intransitive) to forget, to leave behind
```

## Install

Install with pip:

```
pip install palabras
```

## Dev setup

You'll probably want to do this in a virtualenv or conda env, or using another isolation method of your choice.

Clone the repo and cd into the root directory:

```
git clone git@github.com:paavopere/palabras.git
cd palabras
```

Or start from here 👇 if you already got the repo and are in the root directory `palabras`.

Install the package from current directory with `[test]` dependencies in editable mode (`-e`):

```
pip install -e '.[test]'
```

### Checks

Run tests:

```
pytest --cov --cov-report=term-missing
```

All tests should pass and coverage should be 100%.

Run type checks:
```
mypy palabras --ignore-missing-imports
```
