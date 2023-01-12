from copy import copy
from typing import Container, List, Union, Sequence, Iterable
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement


def tags_to_soup(tags: Sequence[bs4.Tag], *, features='html.parser') -> BeautifulSoup:
    """
    Given a list of tags, create a new BeautifulSoup object from those tags (copying tags to the
    new soup object in order)
    """
    soup = BeautifulSoup(features=features)
    for element in tags:
        soup.append(copy(element))
    return soup


def get_heading_siblings_on_level(element):
    """
    Return a list of sibling elements until the next occurrence of a heading on the same
    or higher level.
    """
    hierarchy = 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    if element.name not in hierarchy:
        raise ValueError(f'Element with {element.name} (expected one of {hierarchy})')

    same_and_higher = hierarchy[: hierarchy.index(element.name) + 1]
    return get_siblings_until(element, same_and_higher)


def get_siblings_until(
    element: PageElement, until: Union[str, Container[str]]
) -> List[PageElement]:
    """
    Return a list of sibling elements until the next occurrence of a certain tag name (or
    list/tuple/etc. of tag names).

    The `element` itself is included, and the found occurrence of `until` is excluded.
    """
    break_names = [until] if isinstance(until, str) else until
    found = [element]
    for sibling in element.next_siblings:
        if sibling.name in break_names:
            break
        else:
            found.append(sibling)
    return found


def standardize_spaces(s: str) -> str:
    """
    Replace non-breaking space U+00a0 with a space

    >>> standardize_spaces('This\u00a0 \u00a0 has some\u00a0nbsps')
    'This    has some nbsps'
    """
    return s.replace('\u00a0', ' ')


def render_list(strlist: Iterable[str], sep='\n', prefix='- ') -> str:
    """
    Take a list like ['foo', 'bar'] and render it as a multiline string like:
    - foo
    - bar

    >>> print(render_list(['foo', 'bar']))
    - foo
    - bar

    >>> render_list(['world', 'again'], sep='||', prefix='hello')
    'helloworld||helloagain'
    """
    return sep.join(f'{prefix}{s}' for s in strlist)
