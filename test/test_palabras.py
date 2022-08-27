
import json
from pathlib import Path
from textwrap import dedent

import pytest
from bs4 import BeautifulSoup
from pytest_mock import MockerFixture

import palabras.core
import palabras.cli
from palabras.core import Subsection, WiktionaryPage, WordInfo
from palabras.utils import get_siblings_until, get_heading_siblings_on_level


MOCK_CACHE_FILE_PATH = Path(__file__).parent / '../data/mock_cache.json'


@pytest.fixture()
def mocked_request_url_text(mocker: MockerFixture):
    """
    Mock palabras.core.request_url_text to read URL -> content (HTML) mappings from a pre-populated
    file instead of over the internet.
    """
    with open(MOCK_CACHE_FILE_PATH) as fp:
        mock_cache: dict = json.load(fp)['url_contents']
    mocker.patch('palabras.core.request_url_text', side_effect=lambda url: mock_cache[url])


def test_word_info_from_search_return_type(mocked_request_url_text):
    word = 'despacito'
    wi = WordInfo.from_search(word)
    assert isinstance(wi, palabras.core.WordInfo)


def test_word_info_equals_but_not_is(mocked_request_url_text):
    word = 'despacito'
    wi1 = WordInfo.from_search(word)
    wi2 = WordInfo.from_search(word)
    assert wi1 == wi2
    assert wi1 is not wi2


def test_page_equalities(mocked_request_url_text):
    word = 'olvidar'
    wp_1 = WiktionaryPage(word=word)
    wp_2 = WiktionaryPage(word=word)

    assert wp_1 == wp_2
    assert wp_1 is not wp_2

    revision_a = 62345284
    revision_b = 66217360
    wp_with_revision = WiktionaryPage(word=word, revision=revision_a)
    wp_with_revision_same = WiktionaryPage(word=word, revision=revision_a)
    wp_with_revision_other = WiktionaryPage(word=word, revision=revision_b)

    assert wp_1 != wp_with_revision
    assert wp_with_revision == wp_with_revision_same
    assert wp_with_revision != wp_with_revision_other


def test_eqs_with_other_types(mocked_request_url_text):
    word = 'olvidar'
    page = WiktionaryPage(word)
    section = page.get_section('Spanish')
    wi = WordInfo(section)
    assert page != 'foo'
    assert section != 'foo'
    assert wi != 'foo'


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
    str_definition = palabras.core.Subsection.definition_list_item_to_str(li)
    assert str_definition == 'parse this'


def test_lookup_definition(mocked_request_url_text):
    word = 'culpar'
    wi = WordInfo.from_search(word)
    assert wi.definition_strings[0] == 'to blame'


def test_lookup_definition_complicated(mocked_request_url_text):
    word = 'empleado'  # this word has definitions for adjective, noun, and verb
    revision = 62175311
    wi = WordInfo.from_search(word, revision=revision)
    assert wi.definition_strings == [
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

    assert WordInfo.from_search(word, revision=revision_1).definition_strings \
        == expected_definitions_1
    assert WordInfo.from_search(word, revision=revision_2).definition_strings \
        == expected_definitions_2


def test_cli(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['olvidar']
    palabras.cli.main(args)
    captured = capsys.readouterr()
    expected = dedent('''
        Verb: olvidar (first-person singular present olvido, first-person singular preterite olvidé, past participle olvidado)
        - (transitive) to forget (be forgotten by)
        - (reflexive, intransitive) to forget, elude, escape
        - (with de, reflexive, intransitive) to forget, to leave behind
    ''').lstrip()  # noqa: E501
    assert captured.out == expected


def test_cli_compact(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['olvidar', '--compact']
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
        Verb: olvidar (first-person singular present olvido, first-person singular preterite olvidé, past participle olvidado)
        - to forget; to elude, escape (be forgotten by)
        - (reflexive) to forget
        - (reflexive) to leave behind
    ''').lstrip()  # noqa: E501

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
        Verb: ser (first-person singular present soy, first-person singular preterite fui, past participle sido)
        - to be (essentially or identified as)
        - to be (in the passive voice sense)
        - to exist; to occur

        Noun: ser m (plural seres)
        - a being, organism
        - nature, essence
        - value, worth
    ''').lstrip()  # noqa: E501
    assert captured.out == expected
    assert exitcode == 0


def test_cli_ser_compact(capsys: pytest.CaptureFixture, mocked_request_url_text):
    args = ['ser', '--compact']
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


def test_page_object(mocked_request_url_text):
    word = 'ser'
    page = WiktionaryPage(word)
    assert isinstance(page, WiktionaryPage)


def test_page_object_from_word_and_revision(mocked_request_url_text):
    word = 'empleado'
    revision = 62175311
    page = WiktionaryPage(word, revision)
    assert isinstance(page, WiktionaryPage)


def test_page_object_attributes(mocked_request_url_text):
    word = 'empleado'
    revision = 62175311
    page = WiktionaryPage(word, revision)
    assert page.word == word
    assert page.revision == revision


def test_get_subsections_len_and_type(mocked_request_url_text):
    page = WiktionaryPage('empleado')
    section = page.get_spanish_section()
    subsections = section.get_subsections()
    assert len(subsections) > 0  # this page has sections
    for subsection in subsections:
        assert isinstance(subsection, Subsection)


def test_get_subsections_titles(mocked_request_url_text):
    page = WiktionaryPage('empleado', revision=68396093)
    section = page.get_spanish_section()
    subsections = section.get_subsections()
    titles = [ss.title for ss in subsections]
    assert titles == [
        'Etymology',
        'Pronunciation',
        'Adjective',
        'Noun',
        'Participle',
        'Further reading'
    ]


def test_get_specific_subsection(mocked_request_url_text):
    page = WiktionaryPage('empleado')
    section = page.get_spanish_section()
    subsection_adjective = section.get_subsection('Adjective')
    assert isinstance(subsection_adjective, Subsection)
    assert subsection_adjective.title == 'Adjective'


def test_get_nonexistent_subsection(mocked_request_url_text):
    page = WiktionaryPage('empleado')
    section = page.get_spanish_section()
    with pytest.raises(KeyError, match='No section with title:'):
        section.get_subsection('Nonexistent section')


def test_get_heading_siblings_on_level():
    soup = BeautifulSoup(
        '<h1>tag 1</h1>'
        '<h2>tag 2</h2>'
        '<h3>tag 3</h3>'
        '<p>tag 4</p>'
        '<h3>tag 5</h3>'
        '<h2>tag 6</h2>',
        features='html.parser'
    )
    element = soup.h2  # find the first h2
    # should find 2,3,4,5
    assert len(get_heading_siblings_on_level(element)) == 4

    element = soup.h3  # find the first h3
    # should find 3,4
    assert len(get_heading_siblings_on_level(element)) == 2


def test_get_siblings_on_level_error_on_unexpected_element():
    soup = BeautifulSoup(
        '<h1>one</h1>'
        '<li>get_siblings_on_level</li>'
        '<li>only works for headings</li>',
        features='html.parser'
    )
    element = soup.li
    with pytest.raises(ValueError):
        get_heading_siblings_on_level(element)


def test_page_repr(mocked_request_url_text):
    assert repr(WiktionaryPage('empleado')) \
        == "WiktionaryPage('empleado')"
    assert repr(WiktionaryPage('empleado', revision=62175311)) \
        == "WiktionaryPage('empleado', revision=62175311)"


def test_section_repr(mocked_request_url_text):
    page = WiktionaryPage('empleado')
    section = page.get_section('Spanish')
    assert repr(section) == "<WiktionaryPage('empleado') → 'Spanish'>"


def test_subsection_repr(mocked_request_url_text):
    page = WiktionaryPage('ser')
    section = page.get_section('Spanish')
    subsection = section.get_subsection('Verb')
    assert repr(subsection) == "<WiktionaryPage('ser') → 'Spanish' → 'Verb'>"


def test_subsection_raises_on_invalid_parent():
    placeholder_soup = BeautifulSoup('<a>foo</a>', features='html.parser')
    page = WiktionaryPage('ser')

    # get a valid subsection from the page
    ok_subsection = page.get_section('Spanish').get_subsections()[0]

    # parent cannot be a Subsection object
    with pytest.raises(TypeError):
        Subsection(parent=ok_subsection, soup=placeholder_soup)

    # parent cannot be None
    with pytest.raises(TypeError):
        Subsection(parent=None, soup=placeholder_soup)


def test_minimal_subsection_lead(mocker):
    mock_html = '''
    <h2><span id="SectionTitle"></span></h2>
    <h3><span class="mw-headline">SubsectionTitle</span></h3>
    <p>
        <span class="headword">headword</span>
        (<i>an attribute</i><b>a value</b>)
    </p>
    '''
    mocker.patch('palabras.core.WiktionaryPage.get_page_html', return_value=mock_html)

    page = WiktionaryPage('foo')
    section = page.get_section('SectionTitle')
    subsection = section.get_subsection('SubsectionTitle')
    assert subsection.word == 'headword'
    assert subsection.lead_extras == [{'attribute': 'an attribute', 'value': 'a value'}]


def test_minimal_subsection_empty_lead(mocker):
    # mock to create page with a minimal HTML that doesn't have <p> under subsection
    mock_html = '''
    <h2><span id="SectionTitle"></span></h2>
        <h3><span class="mw-headline">SubsectionTitle</span></h3>
    '''
    mocker.patch('palabras.core.WiktionaryPage.get_page_html', return_value=mock_html)

    # create a subsection through a page object
    subsection = (
        WiktionaryPage('foo')
        .get_section('SectionTitle')
        .get_subsection('SubsectionTitle')
    )

    assert subsection.word == ''
    assert subsection.lead_extras == []
    assert subsection.to_dict() == {}


def test_word_info_to_dict(mocked_request_url_text):
    wi = WordInfo.from_search('olvidar')

    expected = dict(
        word='olvidar',
        language='Spanish',
        definition_subsections=[
            dict(
                part_of_speech='Verb',
                word='olvidar',
                extras=[
                    dict(attribute='first-person singular present', value='olvido'),
                    dict(attribute='first-person singular preterite', value='olvidé'),
                    dict(attribute='past participle', value='olvidado'),
                ],
                definitions=[
                    dict(text='(transitive) to forget (be forgotten by)'),
                    dict(text='(reflexive, intransitive) to forget, elude, escape'),
                    dict(text='(with de, reflexive, intransitive) to forget, to leave behind')
                ]
            )
        ]
    )

    assert wi.to_dict() == expected
