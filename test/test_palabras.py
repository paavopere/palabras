
from bs4 import BeautifulSoup
import pytest
import palabras.core


def test_lookup_returns_str():
    word = 'despacito'
    result = palabras.core.lookup(word)
    assert isinstance(result, palabras.core.WordInfo)


def test_get_wiktionary_page_returns_str():
    word = 'despacito'
    result = palabras.core.get_wiktionary_page(word)
    assert isinstance(result, str)


def test_get_wiktionary_page_nonexistent():
    word = 'thispageaintexistent'
    with pytest.raises(palabras.core.WiktionaryPageNotFound):
        palabras.core.get_wiktionary_page(word)


def test_get_wiktionary_page_contains_translation():
    word = 'culpar'
    translation = 'blame'
    result = palabras.core.get_wiktionary_page(word)
    assert translation in result


def test_get_wiktionary_page_contains_portuguese_conjugation():
    word = 'culpar'
    expected_contains = 'culpou'  # Portuguese 3rd person preterite
    result = palabras.core.get_wiktionary_page(word)
    assert expected_contains in result


def test_get_wiktionary_spanish_section_return_type():
    word = 'culpar'
    result = palabras.core.get_wiktionary_spanish_section(word)
    assert isinstance(result, palabras.core.WiktionaryPageSection)


def test_no_spanish_definition():
    word = 'kauppa'  # a word that has Wiktionary page but no Spanish definition
    with pytest.raises(palabras.core.WiktionarySectionNotFound):
        palabras.core.get_wiktionary_spanish_section(word)


def test_get_wiktionary_spanish_section_does_not_contain_portuguese():
    word = 'culpar'
    portuguese_conjugation = 'culpou'  # Portuguese 3rd person preterite
    section = palabras.core.get_wiktionary_spanish_section(word)
    assert portuguese_conjugation not in section


def test_definition_list_item_to_str():
    li = BeautifulSoup('''
    <li>parse <a href="foo">this</a><dl><dd><span>Whatever</span>...</dd></dl></li>
    ''').li
    str_definition = palabras.core.WiktionaryPageSection.definition_list_item_to_str(li)
    assert str_definition == 'parse this'


def test_lookup_definition():
    word = 'culpar'
    word_info = palabras.core.lookup(word)
    assert word_info.definitions[0] == 'to blame'


def test_lookup_definition_complicated():
    word = 'empleado'  # this word has definitions for adjective, noun, and verb
    revision = 62175311
    word_info = palabras.core.lookup(word, revision=revision)
    assert word_info.definitions == [
        'employed',
        'employee',
        'Masculine singular past participle of emplear.'
    ]


def test_lookup_different_definitions_in_history():
    word = 'olvidar'
    revision_1 = 62345284
    revision_2 = 66217360
    expected_definitions_1 = [
        'to forget; to elude, escape (be forgotten by)',
        '(reflexive) to forget',
        '(reflexive) to leave behind'
    ]
    expected_definitions_2 = [
        '(transitive) to forget (be forgotten by)',
        '(reflexive, intransitive) to forget, elude, escape',
        '(with de, reflexive, intransitive) to forget, to leave behind'
    ]

    assert palabras.core.lookup(word, revision=revision_1).definitions == expected_definitions_1
    assert palabras.core.lookup(word, revision=revision_2).definitions == expected_definitions_2