from copy import copy
from dataclasses import dataclass, field
from typing import List, Optional
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
    definition_strings: List[str] = field(default_factory=list)

    @classmethod
    def from_search(cls, word: str, *, revision: Optional[int] = None):
        section = get_wiktionary_spanish_section(word, revision)
        return cls(word=word, definition_strings=section.definitions())


class WiktionaryPageSection:
    def __init__(self, soup: BeautifulSoup):
        self.soup = self._clean_soup(soup)

    @staticmethod
    def _clean_soup(soup: BeautifulSoup):
        """ Return a copy of soup, some elements thrown away """
        soup = copy(soup)  # TODO assert that the original soup is unchanged
        for e in soup.find_all(class_='wiktQuote'):
            e.parent.decompose()
        
        # remove nested lists from definition list items
        for li in WiktionaryPageSection._definition_list_items_from_soup(soup):
            for e in li.find_all('ul'):
                e.decompose()
            
        
        return soup

    def __contains__(self, other: str) -> bool:
        return other in str(self.soup)

    def definitions(self) -> List[str]:
        definitions_ = []
        for definition_list_item in self._definition_list_items():
            definitions_.append(self.definition_list_item_to_str(definition_list_item))
        return definitions_

    # TODO remove
    def _definition_list_items(self):
        return self._definition_list_items_from_soup(self.soup)
    
    @staticmethod
    def _definition_list_items_from_soup(soup):
        headwords = soup.find_all(class_='headword')

        # a bunch of `ol`s that contain a number of definition list items
        definition_lists = [hw.parent.find_next_sibling('ol') for hw in headwords]

        # a bunch of `li`s that contain one definition "line"
        definition_list_items = []
        for dl in definition_lists:
            for dli in dl.find_all('li'):
                definition_list_items.append(dli)

        return definition_list_items
    
    
    @staticmethod
    def definition_list_item_to_str(li: bs4.Tag) -> str:
        """
        Parse the contents of the given definition `li` tag.
        """
        str_ = ''
        for element in li.contents:
            if element.name != 'dl':  #  exclude usage examples and synonyms (etc.?), which are under <dl>
                str_ += ''.join(element.strings)
        str_ = str_.replace('\n', '')
        return str_


def get_word_info(word: str, revision: Optional[int] = None):
    section = get_wiktionary_spanish_section(word, revision)
    return WordInfo(word, definition_strings=section.definitions())


def get_wiktionary_spanish_section(word: str, revision: Optional[int] = None) -> WiktionaryPageSection:
    page = get_wiktionary_page(word, revision)
    return extract_spanish_section(page)


def get_wiktionary_page(word: str, revision: Optional[int] = None) -> WiktionaryPage:
    if revision is None:
        r = requests.get(f'https://en.wiktionary.org/wiki/{word}')
    else:
        r = requests.get(f'https://en.wiktionary.org/w/index.php?title={word}&oldid={revision}')
    if 'Wiktionary does not yet have an entry for' in r.text:
        raise WiktionaryPageNotFound('No Wiktionary page found')
    return r.text


def extract_spanish_section(page: WiktionaryPage) -> WiktionaryPageSection:
    page_soup = BeautifulSoup(page, features='html.parser')
    section_soup = _spanish_section_soup(page_soup)
    return WiktionaryPageSection(soup=section_soup)


def _spanish_section_soup(page_soup: BeautifulSoup) -> BeautifulSoup:
    """ Get a new BeautifulSoup object that only has the tags from the Spanish section. """
    section_soup = BeautifulSoup(features='html.parser')
    for element in _spanish_section_tags(page_soup):
        section_soup.append(copy(element))
    return section_soup
    


def _spanish_section_tags(page_soup: BeautifulSoup) -> List[PageElement]:
    """ Get a list of all BeautifulSoup tags in the logical "Spanish" section.
    TODO clarify whether these are guaranteed to be **Tag**s or if they're more general **PageElement**s
    """
    start_tag = _get_spanish_section_start_tag(page_soup)
    return _get_next_siblings_until_h1_or_h2(start_tag)


def _get_spanish_section_start_tag(page_soup: BeautifulSoup) -> bs4.Tag:
    section_id_tag: bs4.Tag = page_soup.find(id='Spanish')
    if section_id_tag is None:
        raise WiktionarySectionNotFound('No Spanish entry found from Wiktionary page')
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