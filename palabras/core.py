from __future__ import annotations
import json

import re
from dataclasses import dataclass
from typing import List, Optional

import requests
import bs4
from bs4 import BeautifulSoup
from bs4.element import PageElement

from .utils import tags_to_soup, render_list, get_heading_siblings_on_level


class WiktionaryPageNotFound(LookupError):
    pass


class LanguageEntryNotFound(LookupError):
    pass


@dataclass
class WordInfo:
    LANGUAGE = 'Spanish'
    entry: LanguageEntry

    @classmethod
    def from_search(cls, word: str, *, revision: Optional[int] = None):
        entry = WiktionaryPage(word, revision).get_entry(cls.LANGUAGE)
        return cls(entry=entry)

    @property
    def word(self):
        return self.entry.page.word

    @property
    def definition_strings(self):
        return [d.text for d in self.entry.definitions]

    @property
    def definition_sections(self) -> List[Section]:
        return self.entry.get_definition_sections()

    def definition_output(self) -> str:
        """
        Human-readable multiline string with all definitions listed under its
        corresponding part of speech
        """
        outputs = []
        for section in self.entry.sections:
            if section.has_definitions():
                outputs.append(
                    f'{_render_section_lead(section)}\n'
                    f'{render_list(d.to_str() for d in section.definitions)}'
                )
        return '\n\n'.join(outputs)

    def compact_definition_output(self) -> str:
        """
        Human-readable multiline string with word and all definitions listed
        one after one another
        """
        definitions_with_bullet = [
            f'- {d.to_str()}'
            for d in self.entry.definitions
        ]
        lines = [f'[bold yellow]{self.word}[/]'] + definitions_with_bullet
        return '\n'.join(lines)

    def json_output(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        """Everything related to this WordInfo object as a dict"""
        return dict(
            word=self.word,
            language=self.LANGUAGE,
            definition_sections=[d.to_dict() for d in self.definition_sections]
        )


def _render_section_lead(ss: Section) -> str:
    parts = [
        f'[italic]{ss.part_of_speech}:[/]',
        f'[bold yellow]{ss.word}[/]'
    ]
    if ss.gender:
        parts.append(ss.gender)
    if ss.lead_extras:
        parts.append(f'({_render_section_lead_extras(ss.lead_extras)})')
    return ' '.join(parts)


def _render_section_lead_extras(lead_extras: List[dict]) -> str:
    lead_extra_strings = [
        f'[italic]{le["attribute"]}[/] [yellow]{le["value"]}[/]'
        for le in lead_extras
    ]
    return ', '.join(lead_extra_strings)


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

    def get_spanish_entry(self) -> LanguageEntry:
        return self.get_entry(language='Spanish')

    def get_entry(self, language: str) -> LanguageEntry:
        return LanguageEntry(
            soup=_extract_language_entry(self.soup, language=language),
            page=self
        )


def _extract_language_entry(page_soup: BeautifulSoup, language: str) -> BeautifulSoup:
    """
    Get a new BeautifulSoup object that only has the tags from the entry that matches
    `language`.
    """
    tags = _language_entry_tags(page_soup, language)
    return tags_to_soup(tags)


def _language_entry_tags(page_soup: BeautifulSoup, language: str) -> List[PageElement]:
    """
    Get a list of all BeautifulSoup elements since under the heading that matches `language`.
    """
    start_tag = _entry_start_tag(page_soup, language)
    return get_heading_siblings_on_level(start_tag)


def _entry_start_tag(page_soup: BeautifulSoup, language: str) -> bs4.Tag:
    id_tag: bs4.Tag = page_soup.find(id=language)
    if id_tag is None:
        raise LanguageEntryNotFound(f'No {language} entry found from page')
    start_tag = id_tag.parent
    assert start_tag.name == 'h2'
    return start_tag


class LanguageEntry:

    # TODO clear up the hierarchy and inheritance between LanguageEntry and Section.

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

    @property
    def sections(self) -> List[Section]:
        level = 'h3'
        subheadings = self.soup.find_all(level)
        tag_sets = [get_heading_siblings_on_level(sh) for sh in subheadings]
        subsoups = [tags_to_soup(tags) for tags in tag_sets]
        return [Section(parent=self, soup=subsoup) for subsoup in subsoups]

    def get_section(self, title) -> Section:
        for ss in self.sections:
            if ss.title == title:
                return ss
        else:
            raise KeyError(f'No section with title: {title}')

    def get_definition_sections(self) -> List[Section]:
        return [sub for sub in self.sections if sub.has_definitions()]

    @property
    def definitions(self) -> List[Definition]:
        definitions_ = []
        for sub in self.get_definition_sections():
            definitions_.extend(sub.definitions)
        return definitions_


_EMPTY_TAG = bs4.Tag(name='empty')


class Section(LanguageEntry):

    def __init__(self, parent: LanguageEntry, soup: BeautifulSoup):
        self.parent = parent
        if not isinstance(parent, LanguageEntry) or isinstance(parent, Section):
            raise TypeError('parent has to be LanguageEntry and cannot be Section')
        self.soup = soup

    def __repr__(self):
        return f'<{self.parent.page} → {self.parent.title!r} → {self.title!r}>'

    def to_dict(self) -> dict:
        if self.has_definitions():
            return dict(
                part_of_speech=self.part_of_speech,
                word=self.word,
                extras=self.lead_extras,
                definitions=[d.to_dict() for d in self.definitions]
            )
        else:
            return dict()

    @property
    def part_of_speech(self) -> str:
        return self.title

    @property
    def word(self) -> str:
        return self._word_tag.text

    @property
    def _word_tag(self) -> bs4.Tag:
        return self._lead_p.find(class_='headword') or _EMPTY_TAG

    @property
    def _lead_p(self) -> bs4.Tag:
        return self.soup.p or _EMPTY_TAG

    # TODO write a specific test
    @property
    def gender(self) -> Optional[str]:
        tag = self._lead_p.find(class_='gender')
        if tag is None:
            return None
        return tag.text

    @property
    def lead_extras(self) -> List[dict]:
        word_tag = self._word_tag
        opening_parenthesis = word_tag.find_next_sibling(string=re.compile(r'\(')) or _EMPTY_TAG

        # take attributes from <i> tags and corresponding values from the following <b> tag
        # TODO this seems quite fragile
        L = []
        for attribute_tag in opening_parenthesis.find_next_siblings('i'):
            value_tag = attribute_tag.find_next_sibling('b')
            L.append({'attribute': attribute_tag.text,
                      'value': value_tag.text})
        return L

    @property
    def definitions(self) -> List[Definition]:
        """
        Parse definitions from soup and return them as a list of strings.
        """
        return [
            Definition(text=self.definition_list_item_to_str(definition_list_item),
                       extras=None,
                       section=self)
            for definition_list_item in self._definition_list_items()
        ]

    def has_definitions(self) -> bool:
        return len(self.definitions) > 0

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
    extras: Optional[dict]  # we would put synonyms, antonyms, usage examples, etc. here
    section: Section

    def to_str(self) -> str:
        return self.text

    def to_dict(self) -> dict:
        return dict(text=self.text)


def request_url_text(url: str) -> str:
    return requests.get(url).text  # pragma: no cover
