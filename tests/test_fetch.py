"""Tests for picking Datomatic's Download button."""

import pytest

from datoso_seed_nointro.fetch import button_label, pick_download_button


class Button:
    def __init__(self, value: str, name: str = '', *, tag: str = 'input', hidden: str = '') -> None:
        self.value, self.name, self.tag_name, self.hidden = value, name, tag, hidden

    def get_attribute(self, attribute: str) -> str:
        return {'value': self.value, 'name': self.name, 'textContent': self.value}[attribute]


def reason(button: Button) -> str:
    return button.hidden


def pick(buttons, form=()):
    return pick_download_button(list(buttons), list(form), reason)


REQUEST = Button('Request', 'download_request')


@pytest.mark.parametrize('label', ['Download!!', 'Download...', 'DOWNLOAD', 'D-o-w-n-l-o-a-d', 'Dwnld?'])
def test_by_stable_name_whatever_the_label(label):
    real = Button(label, 'download_file')
    assert pick([REQUEST, real, Button('Go', 'search')]) is real


@pytest.mark.parametrize('label', ['Download!!', 'DOWNLOAD...', 'download'])
def test_by_label_when_the_name_changes(label):
    real = Button(label, 'x123')
    assert pick([Button('Go'), real]) is real


def test_button_element_label():
    assert button_label(Button(' Download!! ', tag='button')) == 'download'


def test_hidden_decoys_are_never_chosen():
    real = Button('Download!!', 'download_file')
    decoys = [Button('Download!!', 'download_file', hidden=why) for why in ('display:none', 'off-screen', 'opacity 0')]
    assert pick([*decoys, real, *decoys]) is real


def test_only_hidden_candidates_is_not_found():
    with pytest.raises(LookupError, match='not found'):
        pick([REQUEST, Button('Download!!', 'download_file', hidden='display:none')], [REQUEST])


def test_two_visible_candidates_refuses_to_guess():
    with pytest.raises(LookupError, match='refusing to guess'):
        pick([Button('Download!!', 'download_file'), Button('Download!!!', 'other')])


def test_form_fallback_only_without_any_download_like_button():
    real = Button('Get pack', 'zz')
    assert pick([REQUEST, real, Button('Go')], [REQUEST, real]) is real


def test_form_fallback_ignores_hidden_buttons():
    with pytest.raises(LookupError):
        pick([REQUEST], [REQUEST, Button('Get pack', 'zz'), Button('Get', 'yy')])
    real = Button('Get pack', 'zz')
    assert pick([REQUEST], [REQUEST, real, Button('Get', 'yy', hidden='clip')]) is real
