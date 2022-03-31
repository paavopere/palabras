
from bs4 import BeautifulSoup
from textwrap import dedent
import pytest
import palabras.core
import palabras.cli
from palabras.core import WordInfo


def test_get_word_info_return_type():
    word = 'despacito'
    wi = palabras.core.get_word_info(word)
    assert isinstance(wi, palabras.core.WordInfo)


def test_get_word_info_from_search_return_type():
    word = 'despacito'
    wi = WordInfo.from_search(word)
    assert isinstance(wi, palabras.core.WordInfo)


def test_get_word_info_equals_but_is_not_word_info_from_search():
    word = 'despacito'
    wi1 = palabras.core.get_word_info(word)
    wi2 = WordInfo.from_search(word)
    assert wi1 == wi2
    assert wi1 is not wi2


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
    ''', features='html.parser').li
    str_definition = palabras.core.WiktionaryPageSection.definition_list_item_to_str(li)
    assert str_definition == 'parse this'


def test_lookup_definition():
    word = 'culpar'
    word_info = palabras.core.get_word_info(word)
    assert word_info.definition_strings[0] == 'to blame'


def test_lookup_definition_complicated():
    word = 'empleado'  # this word has definitions for adjective, noun, and verb
    revision = 62175311
    word_info = palabras.core.get_word_info(word, revision=revision)
    assert word_info.definition_strings == [
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

    assert palabras.core.get_word_info(word, revision=revision_1).definition_strings == expected_definitions_1
    assert palabras.core.get_word_info(word, revision=revision_2).definition_strings == expected_definitions_2

    
def test_cli(capsys: pytest.CaptureFixture):
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
    

def test_cli_revision(capsys: pytest.CaptureFixture):
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
    

def test_cli_ser(capsys: pytest.CaptureFixture):
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
    

def test_cli_nonexistent_page(capsys: pytest.CaptureFixture):
    args = ['asdasdasd']
    exitcode = palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = 'No Wiktionary page found\n'
    assert captured.out == expected
    assert exitcode == 1
    

def test_cli_non_spanish_section(capsys: pytest.CaptureFixture):
    args = ['moikka']
    exitcode = palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = 'No Spanish entry found from Wiktionary page\n'
    assert captured.out == expected
    assert exitcode == 1
