
import palabras.core


def test_lookup_returns_str():
    word = 'despacito'
    result = palabras.core.lookup(word)
    assert isinstance(result, str)


def test_get_wiktionary_page_returns_str():
    word = 'despacito'
    result = palabras.core.get_wiktionary_page(word)
    assert isinstance(result, str)


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


def test_get_wiktionary_spanish_section():
    word = 'culpar'
    result = palabras.core.get_wiktionary_spanish_section(word)
    assert isinstance(result, str)


def test_get_wiktionary_spanish_section_does_not_contain_portuguese():
    word = 'culpar'
    portuguese_conjugation = 'culpou'  # Portuguese 3rd person preterite
    section = palabras.core.get_wiktionary_spanish_section(word)
    assert portuguese_conjugation not in section
    