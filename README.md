# palabras
(WIP) CLI app to look up Spanish words on Wiktionary

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

Or start from here if you already got the repo and are in the root directory `palabras`:

```
pip install -e
pip install pytest-cov pytest-mock
```

Run tests:

```
pytest --cov --cov-report=term-missing
```

All tests should pass and coverage should be 100%. If not, I apologize for my failure.