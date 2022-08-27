from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional
import requests
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement

from .utils import tags_to_soup, render_list, get_heading_siblings_on_level, standardize_spaces


class WiktionaryPageNotFound(LookupError):
    pass


class WiktionarySectionNotFound(LookupError):
    pass


@dataclass
class WordInfo:
    LANGUAGE = 'Spanish'
    page_section: WiktionaryPageSection

    @classmethod
    def from_search(cls, word: str, *, revision: Optional[int] = None):
        section = WiktionaryPage(word, revision).get_section(cls.LANGUAGE)
        return cls(page_section=section)

    @property
    def word(self):
        return self.page_section.page.word

    @property
    def definition_strings(self):
        return [d.text for d in self.page_section.definitions()]

    # TODO revise naming
    @property
    def definition_subsections(self) -> List[Subsection]:
        return self.page_section.get_definition_subsections()

    def definition_output(self) -> str:
        """
        Human-readable multiline string with all definitions listed under its
        corresponding part of speech
        """
        outputs = []
        for subsection in self.page_section.get_subsections():
            if subsection.has_definitions():
                sub_output = (
                    f'{subsection.title}: {subsection.lead}\n'
                    f'{render_list(d.to_str() for d in subsection.definitions())}'
                )
                outputs.append(sub_output)
        return '\n\n'.join(outputs)

    def compact_definition_output(self) -> str:
        """
        Human-readable multiline string with word and all definitions listed
        one after one another
        """
        definitions_with_bullet = [
            f'- {d.to_str()}'
            for d in self.page_section.definitions()
        ]
        lines = [self.word] + definitions_with_bullet
        return '\n'.join(lines)

    def to_dict(self) -> dict:
        """Everything related to this WordInfo object as a dict"""
        return dict(
            word=self.word,
            language=self.LANGUAGE,
            definition_subsections=[d.to_dict() for d in self.definition_subsections]
        )


class WiktionaryPage:
    word: str
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

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.word == other.word
            and self.revision == other.revision
            and self.soup == other.soup
        )

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

    def __init__(self, soup: BeautifulSoup, page: WiktionaryPage):
        # self.title = title
        self.page = page
        self.soup = soup

    def __repr__(self):
        return f'<{self.page!r} → {self.title!r}>'

    @property
    def title(self) -> str:
        return self.soup.find(class_='mw-headline').text

    def __contains__(self, other: str) -> bool:
        return other in str(self.soup)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return (
            self.page == other.page
            and self.soup == other.soup
        )

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

    def get_definition_subsections(self, level='h3') -> List[Subsection]:
        return [sub for sub in self.get_subsections(level=level) if sub.has_definitions()]

    def definitions(self) -> List[Definition]:
        definitions_ = []
        for sub in self.get_definition_subsections():
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

    def to_dict(self) -> dict:
        if self.has_definitions():
            return dict(
                part_of_speech=self.title,
                word=self.word,
                extra=self.lead_extra,
                definitions=[d.to_dict() for d in self.definitions()]
            )
        else:
            return dict()

    @property
    def word(self) -> str:
        return self.parent.page.word

    @property
    def lead(self) -> Optional[str]:
        """
        Get the lead, i.e. text of the first <p> under subsection
        """
        p = self.soup.p
        if p:
            return standardize_spaces(p.get_text().strip())
        else:
            return None

    @property
    def lead_extra(self) -> Optional[str]:
        if self.lead is None:
            return None
        return self.lead.replace(self.word, '').strip()


    def definitions(self) -> List[Definition]:
        """
        Parse definitions from soup and return them as a list of strings.
        """
        return [
            Definition(text=self.definition_list_item_to_str(definition_list_item),
                       extra=None,
                       subsection=self)
            for definition_list_item in self._definition_list_items()
        ]

    def has_definitions(self) -> bool:
        return len(self.definitions()) > 0

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
            if e.name not in ('dl', 'ul'):  # exclude nested stuff
                res.append(e.get_text())
        return ''.join(res).strip()


@dataclass
class Definition:
    text: str
    extra: Optional[dict]  # we would put synonyms, antonyms, usage examples, etc. here
    subsection: Subsection

    def to_str(self) -> str:
        return self.text

    def to_dict(self) -> dict:
        return dict(text=self.text)


def request_url_text(url: str) -> str:
    return requests.get(url).text  # pragma: no cover
