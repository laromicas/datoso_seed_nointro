"""Tests for picking Datomatic's Download button."""

from types import SimpleNamespace

import pytest
from datoso.configuration import config

from datoso_seed_nointro import fetch
from datoso_seed_nointro.fetch import FetchSteps, button_label, downloaded_size, pick_download_button, pick_visible


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


def test_pick_visible_skips_hidden_copies():
    real = Button('Daily')
    assert pick_visible([Button('Daily', hidden='display:none'), real], reason, 'Daily link') is real


@pytest.mark.parametrize('elements', [[], [Button('Daily', hidden='off-screen')], [Button('Daily'), Button('Daily')]])
def test_pick_visible_needs_exactly_one(elements):
    with pytest.raises(LookupError, match='Expected one visible Daily link'):
        pick_visible(elements, reason, 'Daily link')


def test_steps_advance_and_label(monkeypatch):
    monkeypatch.setitem(config['COMMAND'], 'Quiet', 'true')
    with FetchSteps(3) as steps:
        steps.step('Opening Datomatic')
        task = steps.progress.tasks[0]
        assert (task.completed, task.description) == (0, 'Opening Datomatic')  # the first step only starts
        steps.step('Downloading')
        steps.label('Downloading (1.0 MB)')
        assert (task.completed, task.description) == (1, 'Downloading (1.0 MB)')
        steps.finish('Fetched')
        assert (task.completed, task.total, task.description) == (3, 3, 'Fetched')
        assert steps.progress.disable


def test_total_steps_counts_categories(monkeypatch):
    monkeypatch.setattr(fetch, 'get_categories', lambda: iter([('a', {}), ('b', {})]))
    assert fetch.total_steps() == fetch.FIXED_STEPS + 2 + 1


def test_downloaded_size(tmp_path):
    folders = SimpleNamespace(download=tmp_path)
    assert downloaded_size(folders) == ''
    (tmp_path / 'pack.zip.part').write_bytes(b'0' * 2_500_000)
    assert downloaded_size(folders) == '2.5 MB'
