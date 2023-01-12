from __future__ import annotations
import json

import re
from dataclasses import dataclass
from typing import Any, List, Optional, Sequence, Tuple, Type, Union

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
    """
    Information about a word, including its language, part of speech, and definitions.
    """

    LANGUAGE = 'Spanish'
    entry: LanguageEntry

    @classmethod
    def from_search(cls, word: str, *, revision: Optional[int] = None):
        """
        Fetch information about a word from Wiktionary and return a WordInfo object.

        Parameters:
            word (str): The word to search for.
            revision (Optional[int]): The revision number of the Wiktionary page to use. If not
                provided, the latest revision will be used.
        """
        entry = WiktionaryPage(word, revision).get_entry(cls.LANGUAGE)
        return cls(entry=entry)

    @property
    def word(self) -> str:
        """The word represented by this WordInfo object, as a string"""
        return self.entry.page.word

    @property
    def definition_strings(self) -> List[str]:
        """Definitions of the word as a list of strings"""
        return [d.text for d in self.entry.definitions]

    @property
    def sections_with_definitions(self) -> List[Section]:
        """List of Section objects that contain definitions"""
        return self.entry.get_sections_with_definitions()

    def definition_output(self) -> str:
        """
        Human-readable multiline string with all definitions listed under its corresponding part of
        speech
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
        definitions_with_bullet = [f'- {d.to_str()}' for d in self.entry.definitions]
        lines = [f'[bold yellow]{self.word}[/]'] + definitions_with_bullet
        return '\n'.join(lines)

    def json_output(self) -> str:
        """
        Return a JSON string representation of all information related to this WordInfo object.
        """
        return json.dumps(self.to_dict(), indent=2)

    def to_dict(self) -> dict:
        """
        Return a dict of all information related to this WordInfo object.
        """
        return dict(
            word=self.word,
            language=self.LANGUAGE,
            definition_sections=[d.to_dict() for d in self.sections_with_definitions],
        )


def _render_section_lead(ss: Section) -> str:
    """
    Render the lead for a section in a string format, including formatting tags for the `rich`
    package used to print to command line.

    The lead for a section consists of the part of speech, the word, the gender (if applicable),
    and any lead extras.

    Parameters:
        ss (Section): The Section object to render the lead for.

    Returns:
        str: The rendered lead for the given section.

    Example:
        >>> section = WiktionaryPage('olvidar').get_entry('Spanish').get_section('Verb')
        >>> _render_section_lead(section)
        '[italic]Verb:[/] [bold yellow]olvidar[/] ([italic]first-person singular present[/] \
[yellow]olvido[/], [italic]first-person singular preterite[/] [yellow]olvidé[/], \
[italic]past participle[/] [yellow]olvidado[/])'
    """
    parts = [f'[italic]{ss.part_of_speech}:[/]', f'[bold yellow]{ss.word}[/]']
    if ss.gender:
        parts.append(ss.gender)
    if ss.lead_extras:
        lead_extra_strings = _render_section_lead_extras(ss.lead_extras)
        parts.append(f"({', '.join(lead_extra_strings)})")
    return ' '.join(parts)


def _render_section_lead_extras(lead_extras: List[dict]) -> List[str]:
    """
    Render the lead extras for a section in a string format, including formatting tags for the
    `rich` package used to print to command line.

    Lead extras are attributes that are listed after the part of speech and word in the lead for
    a section.

    Parameters:
        lead_extras (List[dict]): A list of dictionaries representing the lead extras for a section.

    Returns:
        List[str]: The rendered lead extras for the given section.

    Example:
        >>> _render_section_lead_extras([
        ...     dict(attribute='first-person singular present', value='olvido'),
        ...     dict(attribute='first-person singular preterite', value='olvidé'),
        ...     dict(attribute='past participle', value='olvidado'),
        ... ])
        ['[italic]first-person singular present[/] [yellow]olvido[/]', \
'[italic]first-person singular preterite[/] [yellow]olvidé[/]', \
'[italic]past participle[/] [yellow]olvidado[/]']
    """
    lead_extra_strings = []
    for le in lead_extras:
        if 'value' in le:
            lead_extra_strings.append(
                f'[italic]{le["attribute"]}[/] [yellow]{le["value"]}[/]'
            )
        else:
            lead_extra_strings.append(f'[italic]{le["attribute"]}[/]')
    return lead_extra_strings


class WiktionaryPage:
    """
    Represents a page on Wiktionary, with the page content parsed into a BeautifulSoup object in
    the `soup` attribute.

    Use `get_entry()` to extract a particular LanguageEntry object from the page.
    """

    word: str
    revision: Optional[int] = None

    def __init__(self, word: str, revision: Optional[int] = None):
        """
        Initialize a WiktionaryPage object with a word and an optional revision number.

        Parameters:
            word (str): The word that this Wiktionary page is for.
            revision (Optional[int]): The revision number of the Wiktionary page to use. This is
                the `oldid` parameter in the Wiktionary page URL. If not provided, the latest
                revision will be used.
        """
        self.word = word
        self.revision = revision
        self.soup = BeautifulSoup(
            markup=self.get_page_html(word, revision), features='html.parser'
        )

    def __repr__(self):
        if self.revision is None:
            return f'{self.__class__.__name__}({self.word!r})'
        else:
            return (
                f'{self.__class__.__name__}({self.word!r}, revision={self.revision!r})'
            )

    @staticmethod
    def get_page_html(word, revision=None):
        """
        Retrieve the HTML content of the Wiktionary page for the given word and revision.

        Parameters:
            word (str): The word to retrieve the Wiktionary page for.
            revision (Optional[int]): The revision number of the Wiktionary page to use. If not
                provided, the latest revision will be used.

        Returns:
            str: The HTML content of the Wiktionary page.

        Raises:
            WiktionaryPageNotFound: If the Wiktionary page for the given word cannot be found.
        """
        if revision is None:
            url = f'https://en.wiktionary.org/wiki/{word}'
        else:
            url = f'https://en.wiktionary.org/w/index.php?title={word}&oldid={revision}'
        content = request_url_text(url)
        if 'Wiktionary does not yet have an entry for' in content:
            raise WiktionaryPageNotFound('No Wiktionary page found')
        return content

    def __eq__(self, other) -> bool:
        """
        Check if this WiktionaryPage object is equal to another object.

        Two WiktionaryPage objects are considered equal if they have the same word, revision
        number, and the `soup` BeautifulSoup objects are equal.
        """
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
        """
        Retrieve the language entry for the given language on this Wiktionary page.

        Parameters:
            language (str): The language to retrieve the entry for.

        Returns:
            LanguageEntry: The language entry for the given language on this Wiktionary page.

        Raises:
            LanguageEntryNotFound: If a language entry for the given language cannot be found on
                this Wiktionary page.
        """
        return LanguageEntry(
            soup=_extract_language_entry_soup(self.soup, language=language), page=self
        )


def _extract_language_entry_soup(
    page_soup: BeautifulSoup, language: str
) -> BeautifulSoup:
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
    """
    Find the first `h2` tag in the given BeautifulSoup object representing a Wiktionary page. This
    is used to locate the beginning of the language entry for the word being searched.
    """
    id_tag: bs4.Tag = page_soup.find(id=language)
    if id_tag is None:
        raise LanguageEntryNotFound(f'No {language} entry found from page')
    start_tag = id_tag.parent
    assert start_tag.name == 'h2'
    return start_tag


class LanguageEntry:
    """
    A class representing the information for a single language entry on a Wiktionary page.

    A LanguageEntry object should be generated from a BeautifulSoup object that only contains the
    parsed HTML for one language (not the full page). `WiktionaryPage.get_entry()` does this with
    the `_extract_language_entry_soup()` helper.

    You can get the section through the WiktionaryPage like this:
    >>> entry = WiktionaryPage('empleado').get_entry('Spanish')
    >>> isinstance(entry, LanguageEntry)
    True
    """

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

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self.page == other.page and self.soup == other.soup

    @property
    def sections(self) -> List[Section]:
        """
        Get a list of Section objects inside this language entry.

        Sections correspond to the subheadings under one language entry on the Wiktionary page.
        Some, but not all, of the sections are parts of speech: E.g. the page for 'empleado' has
        sections 'Etymology', 'Pronunciation', 'Adjective', 'Noun', 'Participle', Further reading'.
        """
        level = 'h3'
        subheadings = self.soup.find_all(level)
        tag_sets = [get_heading_siblings_on_level(sh) for sh in subheadings]
        subsoups = [tags_to_soup(tags) for tags in tag_sets]
        return [Section(parent=self, soup=subsoup) for subsoup in subsoups]

    def get_section(self, title: str) -> Section:
        """
        Get a specific section by its title (exact string match).

        Example:
            >>> entry = WiktionaryPage('empleado').get_entry('Spanish')
            >>> section = entry.get_section('Noun')
            >>> isinstance(section, Section)
            True
        """
        for ss in self.sections:
            if ss.title == title:
                return ss
        else:
            raise KeyError(f'No section with title: {title}')

    def get_sections_with_definitions(self) -> List[Section]:
        """Get a list of all sections that contain any definitions."""
        return [sub for sub in self.sections if sub.has_definitions()]

    @property
    def definitions(self) -> List[Definition]:
        """Get a list of all definitions contained in sections of this LanguageEntry"""
        definitions_ = []
        for sub in self.get_sections_with_definitions():
            definitions_.extend(sub.definitions)
        return definitions_


_EMPTY_TAG = bs4.Tag(name='empty')
ConjugationTableDiv = Type[bs4.Tag]
Conjugation = dict


class Section(LanguageEntry):
    def __init__(self, parent: LanguageEntry, soup: BeautifulSoup):
        self.parent = parent
        if not isinstance(parent, LanguageEntry) or isinstance(parent, Section):
            raise TypeError('parent has to be LanguageEntry and cannot be Section')
        self.soup = soup

    def __repr__(self):
        return f'<{self.parent.page} → {self.parent.title!r} → {self.title!r}>'

    def to_dict(self) -> dict[str, Any]:
        if self.has_definitions():
            D: dict[str, Any] = dict(
                part_of_speech=self.part_of_speech,
                word=self.word,
                extras=self.lead_extras,
                definitions=[d.to_dict() for d in self.definitions],
            )
            if self.conjugation is not None:
                D['conjugation'] = self.conjugation
            return D
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

    @property
    def conjugation(self) -> Optional[Conjugation]:
        # TODO raise NotImplemented error if trying for languages other than Spanish
        table_root = self._conjugation_table_root()
        if table_root is None:
            return None

        return ConjugationTable(table_root).to_dict()

    def _conjugation_table_root(self) -> Optional[ConjugationTableDiv]:
        headings = self.soup.find_all('h4')
        candidate_table_headings = [h for h in headings if h.find(string='Conjugation')]
        try:
            table_heading = candidate_table_headings[0]
        except IndexError:
            return None
        return table_heading.find_next('div', class_='NavFrame')

    # TODO write a specific test
    @property
    def gender(self) -> Optional[str]:
        tag = self._lead_p.find(class_='gender')
        if tag is None:
            return None
        return tag.text

    @property
    def lead_extras(self) -> List[dict]:
        """
        Extract attributes from inside parentheses on the lead line (after the word).
        """
        word_tag = self._word_tag
        opening_parenthesis = (
            word_tag.find_next_sibling(string=re.compile(r'\(')) or _EMPTY_TAG
        )

        # take attributes from <i> tags and corresponding values from the following <b> tag
        # TODO this seems quite fragile
        L = []
        for attribute_tag in opening_parenthesis.find_next_siblings('i'):
            value_tag = attribute_tag.find_next_sibling('b')
            D = {'attribute': attribute_tag.text}
            if value_tag:  # only try to extract text if the value tab exists
                D['value'] = value_tag.text
            L.append(D)
        return L

    @property
    def definitions(self) -> List[Definition]:
        """
        Parse definitions from soup and return them as a list of strings.
        """
        return [
            Definition(
                text=self.definition_list_item_to_str(definition_list_item),
                extras=None,
                section=self,
            )
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


class ConjugationTable:

    _ROW_INDEX_INFINITIVE = 0
    _ROW_INDEX_GERUND = 1
    _ROW_SLICE_PAST_PARTICIPLE = slice(3, 5)
    _ROW_SLICE_INDICATIVE = slice(8, 13)
    _ROW_SLICE_SUBJUNCTIVE = slice(15, 19)
    _ROW_SLICE_IMPERATIVE = slice(21, 23)

    def __init__(self, root: ConjugationTableDiv):
        """
        Initialize from a "root" tag, a div that contains the conjugation table
        """
        self.root = root
        self.table = self.root.find('table')

    def to_dict(self):
        return {
            'infinitive': self._parse_simple(self._ROW_INDEX_INFINITIVE),
            'gerund': self._parse_simple(self._ROW_INDEX_GERUND),
            'past participle': self._parse_complex(
                self._ROW_SLICE_PAST_PARTICIPLE, header=('masculine', 'feminine')
            ),
            'indicative': self._parse_complex(
                self._ROW_SLICE_INDICATIVE,
                header=('s1', 's2', 's3', 'pl1', 'pl2', 'pl3'),
            ),
            'subjunctive': self._parse_complex(
                self._ROW_SLICE_SUBJUNCTIVE,
                header=('s1', 's2', 's3', 'pl1', 'pl2', 'pl3'),
            ),
            'imperative': self._parse_complex(
                self._ROW_SLICE_IMPERATIVE,
                header=('s1', 's2', 's3', 'pl1', 'pl2', 'pl3'),
            ),
        }

    def _parse_simple(self, row_index: int):
        tag = self.table.tbody.find_all('tr')[row_index].td
        return tag.get_text().strip()

    def _parse_complex(self, row_slice: slice, header: Sequence[str]):
        d = {}
        for tr in self.table.tbody.find_all('tr')[row_slice]:
            row_key, values_dict = self._parse_row(tr, header)
            d[row_key] = values_dict
        return d

    @staticmethod
    def _parse_row(tr: bs4.Tag, header: Sequence[str]) -> Tuple[str, dict]:
        row_key = tr.th.get_text().strip()
        value_tags = [td for td in tr.find_all('td')]
        values = [ConjugationTable._parse_value_tag(td) for td in value_tags]
        values_dict = {h: v for h, v in zip(header, values)}
        return row_key, values_dict

    @staticmethod
    def _parse_value_tag(td: bs4.Tag) -> Union[str, dict, None]:
        """
        Parse a <td> tag containing one conjugation.

        In the usual case, when the td contains one span, return the text inside it (or None if
        the text is empty). In the tuteo/voseo case, the td contains 2 spans; their texts are
        split in a dict.
        """
        spans = td.find_all('span')
        if len(spans) == 1:
            text = spans[0].get_text().strip() or None
            return text
        elif len(spans) > 1:
            return {
                'tú': spans[0].get_text().strip(),
                'vos': spans[1].get_text().strip(),
            }
        else:
            return None


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
