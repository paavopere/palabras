
import json
from pathlib import Path
from textwrap import dedent

import pytest
from bs4 import BeautifulSoup
from pytest_mock import MockerFixture

import palabras.core
import palabras.cli
from palabras.core import WiktionaryPage, WordInfo, get_siblings_until, request_url_text


MOCK_CACHE_FILE_PATH = Path(__file__).parent / '../data/mock_cache.json'


@pytest.fixture()
def mocked_request_url_text(mocker: MockerFixture):
    """
    Mock palabras.core.request_url_text to read URL -> content (HTML) mappings from a pre-populated
    file instead of over the internet.
    """
    with open(MOCK_CACHE_FILE_PATH) as fp:
        mock_cache: dict = json.load(fp)['url_contents']
    mocker.patch('palabras.core.request_url_text', side_effect=mock_cache.get)


def test_get_word_info_return_type(mocked_request_url_text):
    word = 'despacito'
    wi = palabras.core.get_word_info(word)
    assert isinstance(wi, palabras.core.WordInfo)


def test_get_word_info_from_search_return_type(mocked_request_url_text):
    word = 'despacito'
    wi = WordInfo.from_search(word)
    assert isinstance(wi, palabras.core.WordInfo)


def test_get_word_info_equals_but_is_not_word_info_from_search(mocked_request_url_text):
    word = 'despacito'
    wi1 = palabras.core.get_word_info(word)
    wi2 = WordInfo.from_search(word)
    assert wi1 == wi2
    assert wi1 is not wi2


def test_get_wiktionary_page_nonexistent(mocked_request_url_text):
    word = 'thispageaintexistent'
    with pytest.raises(palabras.core.WiktionaryPageNotFound):
        palabras.core.WiktionaryPage(word)


def test_get_wiktionary_page_contains_translation(mocked_request_url_text):
    word = 'culpar'
    translation = 'blame'
    page = palabras.core.WiktionaryPage(word)
    assert translation in page


def test_wiktionary_page_contains_portuguese_conjugation(mocked_request_url_text):
    word = 'culpar'
    expected_contains = 'culpou'  # Portuguese 3rd person preterite
    page = palabras.core.WiktionaryPage(word)
    assert expected_contains in page


def test_spanish_section_type(mocked_request_url_text):
    word = 'culpar'
    result = WiktionaryPage(word).get_spanish_section()
    assert isinstance(result, palabras.core.WiktionaryPageSection)


def test_no_spanish_definition(mocked_request_url_text):
    word = 'kauppa'  # a word that has Wiktionary page but no Spanish definition
    with pytest.raises(palabras.core.WiktionarySectionNotFound):
        WiktionaryPage(word).get_spanish_section()


def test_spanish_section_does_not_contain_portuguese(mocked_request_url_text):
    word = 'culpar'
    portuguese_conjugation = 'culpou'  # Portuguese 3rd person preterite
    section = WiktionaryPage(word).get_spanish_section()
    assert portuguese_conjugation not in section


def test_definition_list_item_to_str(mocked_request_url_text):
    li = BeautifulSoup('''
    <li>parse <a href="foo">this</a><dl><dd><span>Whatever</span>...</dd></dl></li>
    ''', features='html.parser').li
    str_definition = palabras.core.WiktionaryPageSection.definition_list_item_to_str(li)
    assert str_definition == 'parse this'


def test_lookup_definition(mocked_request_url_text):
    word = 'culpar'
    word_info = palabras.core.get_word_info(word)
    assert word_info.definition_strings[0] == 'to blame'


def test_lookup_definition_complicated(mocked_request_url_text):
    word = 'empleado'  # this word has definitions for adjective, noun, and verb
    revision = 62175311
    word_info = palabras.core.get_word_info(word, revision=revision)
    assert word_info.definition_strings == [
        'employed',
        'employee',
        'Masculine singular past participle of emplear.'
    ]


def test_lookup_different_definitions_in_history(mocked_request_url_text):
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

    assert palabras.core.get_word_info(word, revision=revision_1).definition_strings \
        == expected_definitions_1
    assert palabras.core.get_word_info(word, revision=revision_2).definition_strings \
        == expected_definitions_2

    
def test_cli(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['olvidar']
    palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = dedent('''
        olvidar
        - (transitive) to forget (be forgotten by)
        - (reflexive, intransitive) to forget, elude, escape
        - (with de, reflexive, intransitive) to forget, to leave behind
    ''').lstrip()
    assert captured.out == expected
    

def test_cli_revision(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args1 = ['olvidar', '-r', '62345284']
    args2 = ['olvidar', '--revision', '62345284']
    args3 = ['olvidar', '--revision=62345284']
    
    expected = dedent('''
        olvidar
        - to forget; to elude, escape (be forgotten by)
        - (reflexive) to forget
        - (reflexive) to leave behind
    ''').lstrip()
    
    for args in args1, args2, args3:
        exitcode = palabras.cli.main(args)
        captured = capsys.readouterr()
        assert captured.out == expected
        assert exitcode == 0
    

def test_cli_ser(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['ser']
    exitcode = palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = dedent('''
        ser
        - to be (essentially or identified as)
        - to be (in the passive voice sense)
        - to exist; to occur
        - a being, organism
        - nature, essence
        - value, worth
    ''').lstrip()
    assert captured.out == expected
    assert exitcode == 0
    

def test_cli_nonexistent_page(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['asdasdasd']
    exitcode = palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = 'No Wiktionary page found\n'
    assert captured.out == expected
    assert exitcode == 1
    

def test_cli_non_spanish_section(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['moikka']
    exitcode = palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = 'No Spanish entry found from Wiktionary page\n'
    assert captured.out == expected
    assert exitcode == 1


def test_get_next_siblings_until():
    markup = (
        '<h1>hello</h1>'
        '<p>foo</p>'
        '<h2>hello again</h2>'
        '<p>bar</p>'
        '<h1>hello 2</h1>'
        '<p>foo 2</p>'
        '<h2>hello again 2</h2>'
        '<p>bar 2</p>'
        '<h1>hello 3</h1>'
    )
    soup = BeautifulSoup(markup, features='html.parser')
    tag = soup.find('h1')
    assert len(get_siblings_until(tag, 'p')) == 1  # hello
    assert len(get_siblings_until(tag, 'h2')) == 2  # hello ... hello again
    assert len(get_siblings_until(tag, 'h1')) == 4  # hello ... hello 2
    assert len(get_siblings_until(tag, 'nope')) == 9  # all tags
    
    tag2 = soup.find_all('h1')[1]
    assert len(get_siblings_until(tag2, 'h1')) == 4  # hello 2 ... bar 2
    assert len(get_siblings_until(tag2, 'nope')) == 5  # hello 2 ... hello 3
    
    
def test_page_object():
    word = 'ser'
    page = WiktionaryPage(word)
    assert isinstance(page, WiktionaryPage)
    
    
def test_page_object_from_word_and_revision():
    word = 'empleado'
    revision = 62175311
    page = WiktionaryPage(word, revision)
    assert isinstance(page, WiktionaryPage)
    
    
def test_page_object_attributes():
    word = 'empleado'
    revision = 62175311
    page = WiktionaryPage(word, revision)
    assert page.word == word
    assert page.revision == revision
    