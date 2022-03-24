import requests
import bs4
from bs4 import BeautifulSoup


WiktionaryPage = str
WiktionaryPageSection = str

def lookup(word: str):
    return word


def get_wiktionary_spanish_section(word: str) -> WiktionaryPageSection:
    return extract_spanish_section(get_wiktionary_page(word))


def get_wiktionary_page(word: str) -> WiktionaryPage:
    r = requests.get(f'https://en.wiktionary.org/wiki/{word}')
    return r.text


def extract_spanish_section(page: WiktionaryPage) -> WiktionaryPageSection:
    
    soup = BeautifulSoup(page)
    start_tag = soup.find(id='Spanish').parent
    section_tags = [start_tag]
    for sibling in start_tag.next_siblings:
        if sibling.name == start_tag.name:
            break
        else:
            section_tags.append(sibling)
    
    raise NotImplementedError