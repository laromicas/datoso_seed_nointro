"""Common functions for the No-Intro seed."""
from collections.abc import Generator

from datoso.configuration import config

categories = {
    'aftermarket': {
        'folder': 'Aftermarket',
        'link': 'set8',
    },
    'non_game': {
        'folder': 'Non-Game',
        'link': 'set5',
    },
    'non_redump': {
        'folder': 'Non-Redump',
        'link': 'set3',
    },
    'redump_custom': {
        'folder': 'Redump Custom',
        'link': 'set6',
    },
    'redump_bios': {
        'folder': 'Redump BIOS',
        'link': 'set7',
    },
    'source_code': {
        'folder': 'Source Code',
        'link': 'set2',
    },
    'unofficial': {
        'folder': 'Unofficial',
        'link': 'set4',
    },
}

def get_categories() -> Generator[str, dict]:
    """Get the categories."""
    include = config.get('NOINTRO', 'include_categories', fallback='')
    exclude = config.get('NOINTRO', 'exclude_categories', fallback='')

    include_list = include.split(',') if include else categories.keys()
    exclude_list = exclude.split(',') if exclude else []

    for category, metadata in categories.items():
        if category not in exclude_list and category in include_list:
            yield category, metadata

def get_categories_folders() -> Generator[str]:
    """Get the categories folders."""
    for _, metadata in get_categories():
        yield metadata['folder']
