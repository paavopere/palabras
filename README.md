# palabras
(WIP) CLI app to look up Spanish words on Wiktionary

[![PyPI version](https://badge.fury.io/py/palabras.svg)](https://badge.fury.io/py/palabras)

[![Tests](https://github.com/paavopere/palabras/actions/workflows/tests.yml/badge.svg)](https://github.com/paavopere/palabras/actions/workflows/tests.yml)

## Usage

Call from command line like this:

```
python -m palabras ser
```

```
Verb: ser (first-person singular present soy, first-person singular preterite fui, past participle sido)
- to be (essentially or identified as)
- to be (in the passive voice sense)
- to exist; to occur

Noun: ser m (plural seres)
- a being, organism
- nature, essence
- value, worth
```

For more compact output:

```
python -m palabras ser --compact
```

```
ser
- to be (essentially or identified as)
- to be (in the passive voice sense)
- to exist; to occur
- a being, organism
- nature, essence
- value, worth
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

Run tests, linter, and type checks:

```
pytest --cov --cov-report=term-missing
flake8
mypy palabras --ignore-missing-imports
```

... or in one go:

```
tox
```

All checks should pass and test coverage should be 100% of lines.
