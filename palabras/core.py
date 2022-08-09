from __future__ import annotations

from copy import copy
from dataclasses import dataclass, field
from typing import Container, List, Optional, Sequence, Union
import requests
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement


Definition = str  # TODO make a class out of this, with ability to carry extra info like synonyms


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
        
    def __repr__(self):
        if self.revision is None:
            return f'{self.__class__.__name__}({self.word!r})'
        else:
            return f'{self.__class__.__name__}({self.word!r}, revision={self.revision!r})'
    
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
            soup=_extract_language_section(self.soup, language=language),
            page=self
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
    return get_heading_siblings_on_level(start_tag)
    
    
def _language_section_start_tag(page_soup: BeautifulSoup, language: str) -> bs4.Tag:
    section_id_tag: bs4.Tag = page_soup.find(id=language)
    if section_id_tag is None:
        raise WiktionarySectionNotFound('No Spanish entry found from Wiktionary page')
    start_tag = section_id_tag.parent
    assert start_tag.name == 'h2'
    return start_tag


class WiktionaryPageSection:

    # TODO clear up the hierarchy and inheritance between WiktionaryPageSection and Subsection.
    
    def __init__(self, soup: BeautifulSoup, page: Optional[WiktionaryPage] = None):
        # self.title = title
        self.page = page
        self.soup = soup
        
    def __repr__(self):
        return f'<{self.page!r} → {self.title!r}>'
    
    @property
    def title(self):
        return self.soup.find(class_='mw-headline').text

    def __contains__(self, other: str) -> bool:
        return other in str(self.soup)
    
    def get_subsections(self, level='h3') -> List[Subsection]:
        subheadings = self.soup.find_all(level)
        tag_sets = [get_heading_siblings_on_level(sh) for sh in subheadings]
        subsoups = [tags_to_soup(tags) for tags in tag_sets]
        return [Subsection(parent=self, soup=subsoup) for subsoup in subsoups]
    
    def get_subsection(self, title, *, level='h3') -> Subsection:
        subsections = self.get_subsections(level=level)
        for ss in subsections:
            if ss.title == title:
                return ss
        else:
            raise KeyError(f'No section with title: {title}')
    
    def definitions(self):
        definitions_ = []
        for sub in self.get_subsections():
            definitions_.extend(sub.definitions())
        return definitions_


class Subsection(WiktionaryPageSection):
    def __init__(self, parent: WiktionaryPageSection, soup: BeautifulSoup):
        self.parent = parent
        if not isinstance(parent, WiktionaryPageSection) or isinstance(parent, Subsection):
            raise TypeError('parent has to be WiktionaryPageSection and cannot be Subsection')
        self.soup = soup
        
    def __repr__(self):
        return f'<{self.parent.page} → {self.parent.title!r} → {self.title!r}>'
    
    def content_string(self) -> str:
        """
        Render contents as a human-readable string.
        """
        lines = []
        p = self.soup.p
        if p:
            lines.append(self.soup.p.get_text().strip())
        for definition in self.definitions():
            lines.append(f'- {definition}')
        lines.append('')  # add with empty line
        return '\n'.join(lines)
    
    def definitions(self) -> List[Definition]:
        """
        Parse definitions from soup and return them as a list of strings.
        """
        definitions_ = []
        for definition_list_item in self._definition_list_items():
            definitions_.append(
                self.definition_list_item_to_str(definition_list_item))
        return definitions_

    def _definition_list_items(self) -> List[bs4.Tag]:
        return self._definition_list_items_from_soup(self.soup)

    @staticmethod
    def _definition_list_items_from_soup(soup: BeautifulSoup) -> List[bs4.Tag]:  
        """
        Extract <li> tags that contain definitions
        """      
        dlis = []
        for ol in soup.find_all('ol', recursive=False):
            for child in ol.find_all('li', recursive=False):
                dlis.append(child)
        return dlis

    @staticmethod
    def definition_list_item_to_str(li: bs4.Tag) -> str:
        """
        Parse the contents of the given definition `li` tag.
        """
        res = []
        for e in li.children:
            if e.name not in ('dl', 'ul'):  #  exclude nested stuff
                res.append(e.get_text())
        return ''.join(res).strip()
        

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


def get_heading_siblings_on_level(element):
    """
    Return a list of sibling elements until the next occurrence of a heading on the same 
    or higher level.
    """
    hierarchy = 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'
    if element.name not in hierarchy:
        raise ValueError(
            f'Element with {element.name} (expected one of {hierarchy})')
    
    same_and_higher = hierarchy[:hierarchy.index(element.name) + 1]
    return get_siblings_until(element, same_and_higher)


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
