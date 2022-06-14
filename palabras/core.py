from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from typing import Container, Iterable, List, Optional, Sequence, Union
import requests
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement

WiktionaryPageStr = str  # TODO remove this and implement WiktionaryPage instead


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
        section = WiktionaryPage(word, revision).get_spanish_section()
        return cls(word=word, definition_strings=section.definitions())


class WiktionaryPage:
    word: Optional[str] = None
    revision: Optional[int] = None

    def __init__(self,
                 word: str,
                 revision: Optional[int] = None):
        self.word = word
        self.revision = revision
        self.soup = BeautifulSoup(
            markup=self.get_page_html(word, revision), 
            features='html.parser'
        )
    
    @staticmethod
    def get_page_html(word, revision=None):
        if revision is None:
            url = f'https://en.wiktionary.org/wiki/{word}'
        else:
            url = f'https://en.wiktionary.org/w/index.php?title={word}&oldid={revision}'
        content = request_url_text(url)
        if 'Wiktionary does not yet have an entry for' in content:
            raise WiktionaryPageNotFound('No Wiktionary page found')
        return content

    def __contains__(self, other: str) -> bool:
        return other in str(self.soup)

    def get_spanish_section(self) -> WiktionaryPageSection:
        return self.get_section(language='Spanish')
    
    def get_section(self, language: str):
        return WiktionaryPageSection(
            soup=_extract_language_section(self.soup, language=language)
        )
    

def _extract_language_section(page_soup: BeautifulSoup, language: str) -> BeautifulSoup:
    """
    Get a new BeautifulSoup object that only has the tags from the section that matches 
    `language`.
    """
    tags = _language_section_tags(page_soup, language)
    return tags_to_soup(tags)


def _language_section_tags(page_soup: BeautifulSoup, language: str) -> List[PageElement]:
    """
    Get a list of all BeautifulSoup tags in the logical section that matches `language`.
    
    TODO clarify whether these are guaranteed to be **Tag**s or if they're more general 
        **PageElement**s
    """
    start_tag = _language_section_start_tag(page_soup, language)
    return get_siblings_until(start_tag, ['h1', 'h2'])
    
    
def _language_section_start_tag(page_soup: BeautifulSoup, language: str) -> bs4.Tag:
    section_id_tag: bs4.Tag = page_soup.find(id=language)
    if section_id_tag is None:
        raise WiktionarySectionNotFound('No Spanish entry found from Wiktionary page')
    start_tag = section_id_tag.parent
    assert start_tag.name == 'h2'
    return start_tag


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
            definitions_.append(
                self.definition_list_item_to_str(definition_list_item))
        return definitions_

    # TODO remove
    def _definition_list_items(self):
        return self._definition_list_items_from_soup(self.soup)

    @staticmethod
    def _definition_list_items_from_soup(soup):
        headwords = soup.find_all(class_='headword')

        # a bunch of `ol`s that contain a number of definition list items
        definition_lists = [
            hw.parent.find_next_sibling('ol') for hw in headwords
        ]

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
    return WordInfo.from_search(word=word, revision=revision)


def request_url_text(url: str) -> str:
    return requests.get(url).text  # pragma: no cover


def tags_to_soup(tags: Sequence[bs4.Tag],
                 *,
                 features='html.parser') -> BeautifulSoup:
    """
    Given a list of tags, create a new BeautifulSoup object from those tags (copying tags to the
    new soup object in order)
    """
    soup = BeautifulSoup(features=features)
    for element in tags:
        soup.append(copy(element))
    return soup


def get_siblings_until(element: PageElement,
                       until: Union[str, Container[str]]) -> List[PageElement]:
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