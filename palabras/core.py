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


@dataclass
class WordInfo:
    word: str
    definition: list = field(default_factory=list)


def lookup(word: str) -> WordInfo:
    return WordInfo(word)


def get_wiktionary_spanish_section(word: str) -> WiktionaryPageSection:
    return extract_spanish_section(get_wiktionary_page(word))


def get_wiktionary_page(word: str) -> WiktionaryPage:
    r = requests.get(f'https://en.wiktionary.org/wiki/{word}')
    if 'Wiktionary does not yet have an entry for' in r.text:
        raise WiktionaryPageNotFound('Wiktionary page not found for {word}')
    return r.text


def extract_spanish_section(page: WiktionaryPage) -> WiktionaryPageSection:
    soup = BeautifulSoup(page, features='html.parser')
    section_id_element = soup.find(id='Spanish')
    if section_id_element is None:
        raise WiktionarySectionNotFound()
    start_element = section_id_element.parent
    assert start_element.name == 'h2'
    elements = _get_siblings_until_h1_or_h2(start_element)
    return '\n'.join(map(str, elements))
    

def _get_siblings_until_h1_or_h2(element: PageElement) -> List[PageElement]:
    section_tags = [element]
    for sibling in element.next_siblings:
        if sibling.name in ('h1', 'h2'):
            break
        else:
            section_tags.append(sibling)
    
    return section_tags