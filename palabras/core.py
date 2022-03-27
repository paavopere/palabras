from copy import copy
from dataclasses import dataclass, field
from typing import List
import requests
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement


WiktionaryPage = str
WiktionaryPageSection = str


class WiktionaryPageNotFound(LookupError):
    pass


class WiktionarySectionNotFound(LookupError):
    pass


class WiktionaryPageSection:
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup

    def __contains__(self, other: str) -> bool:
        return other in str(self.soup)


@dataclass
class WordInfo:
    word: str
    definition: list = field(default_factory=list)


def lookup(word: str) -> WordInfo:
    return WordInfo(word)


def get_wiktionary_spanish_section(word: str) -> WiktionaryPageSection:
    page = get_wiktionary_page(word)
    return extract_spanish_section(page)


def get_wiktionary_page(word: str) -> WiktionaryPage:
    r = requests.get(f'https://en.wiktionary.org/wiki/{word}')
    if 'Wiktionary does not yet have an entry for' in r.text:
        raise WiktionaryPageNotFound('Wiktionary page not found for {word}')
    return r.text


def extract_spanish_section(page: WiktionaryPage) -> WiktionaryPageSection:
    page_soup = BeautifulSoup(page, features='html.parser')

    section_soup = BeautifulSoup()
    for element in _spanish_section_tags(page_soup):
        section_soup.append(copy(element))

    return WiktionaryPageSection(soup=section_soup)


def _spanish_section_tags(page_soup: BeautifulSoup) -> List[PageElement]:
    """ Get a list of all BeautifulSoup tags in the logical "Spanish" section.
    TODO clarify whether these are guaranteed to be **Tag**s or if they're more general **PageElement**s
    """
    start_tag = _get_spanish_section_start_tag(page_soup)
    return _get_next_siblings_until_h1_or_h2(start_tag)


def _get_spanish_section_start_tag(page_soup: BeautifulSoup) -> bs4.Tag:
    section_id_tag: bs4.Tag = page_soup.find(id='Spanish')
    if section_id_tag is None:
        raise WiktionarySectionNotFound()
    start_tag = section_id_tag.parent
    assert start_tag.name == 'h2'
    return start_tag
    

def _get_next_siblings_until_h1_or_h2(element: PageElement) -> List[PageElement]:
    section_tags = [element]
    for sibling in element.next_siblings:
        if sibling.name in ('h1', 'h2'):
            break
        else:
            section_tags.append(sibling)
    return section_tags