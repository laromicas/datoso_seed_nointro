"""Fetch and download DAT files."""
import random
import re
import shutil
import time
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import Self

from datoso.configuration import config, logger
from datoso.configuration.folder_helper import Folders
from datoso.helpers.file_utils import move_path
from rich.progress import BarColumn, MofNCompleteColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.remote.webelement import WebElement

from datoso_seed_nointro import __prefix__
from datoso_seed_nointro.common import get_categories

FIXED_STEPS = 7  # open site, terms, download page, categories, request, download, wait (+ extract and categories)


class FetchSteps:
    """One progress bar for the fetch: each Selenium step advances it and becomes its label."""

    def __init__(self, total: int) -> None:
        """Bar of ``total`` steps, hidden with --quiet."""
        self.progress = Progress(
            SpinnerColumn(), TextColumn('{task.description}'), BarColumn(), MofNCompleteColumn(), TimeElapsedColumn(),
            disable=config.getboolean('COMMAND', 'Quiet', fallback=False),
        )  # fmt: skip
        self.task = self.progress.add_task('Starting', total=total)
        self.started = False

    def __enter__(self) -> Self:  # noqa: D105
        self.progress.start()
        return self

    def __exit__(self, *exc: object) -> None:  # noqa: D105
        self.progress.stop()

    def step(self, description: str) -> None:
        """Finish the current step and start ``description``."""
        self.progress.update(self.task, advance=1 if self.started else 0, description=description)
        self.started = True

    def label(self, description: str) -> None:
        """Change the current step's label without advancing."""
        self.progress.update(self.task, description=description)

    def finish(self, description: str = 'Done') -> None:
        """Finish the last step."""
        task = self.progress.tasks[0]
        self.progress.update(self.task, completed=task.total, description=description)


def total_steps() -> int:
    """Count the steps of a full fetch: the fixed ones, one per category, and extracting."""
    return FIXED_STEPS + len(list(get_categories())) + 1


def downloaded_size(folder_helper: Folders) -> str:
    """Size of the file Firefox is writing (``*.part``), e.g. ``12.3 MB``, or empty."""
    parts = sorted(Path(folder_helper.download).glob('*.part'))
    size = sum(part.stat().st_size for part in parts if part.exists())
    return f'{size / 1_000_000:.1f} MB' if size else ''


def execute_with_retry(method: Callable, max_attempts: int) -> None:
    """Execute a method with several times until it fails all or is executed fine."""
    exc = None
    for _ in range(max_attempts):
        try:
            return method()
        except Exception as exc:  # noqa: BLE001
            print(exc)
            time.sleep(1)
    if exc is not None:
        raise exc
    return None


def sleep_time() -> None:
    """Sleeps for a random time."""
    time.sleep(random.random() * 3 + 4)  # noqa: S311


def is_download_finished(folder_helper: Folders) -> bool:
    """Check if the download is finished."""
    firefox_temp_file = sorted(Path(folder_helper.download).glob('*.part'))
    chrome_temp_file = sorted(Path(folder_helper.download).glob('*.crdownload'))
    downloaded_files = sorted(Path(folder_helper.download).glob('*.zip'))
    return (len(firefox_temp_file) == 0) and \
       (len(chrome_temp_file) == 0) and \
       (len(downloaded_files) >= 1)


def delete_temp_files_if_exists(folder_helper: Folders) -> None:
    """Check if the files are in the folder."""
    firefox_temp_file = sorted(Path(folder_helper.download).glob('*.part'))
    chrome_temp_file = sorted(Path(folder_helper.download).glob('*.crdownload'))
    downloaded_files = sorted(Path(folder_helper.download).glob('*.zip'))
    for file in firefox_temp_file:
        file.unlink()
    for file in chrome_temp_file:
        file.unlink()
    for file in downloaded_files:
        file.unlink()


def downloads_disabled(driver: webdriver.Firefox) -> bool:
    """Check if the downloads in Datomatic are disabled."""
    words = ['temporary suspended', 'temporary disabled', 'services may be down', 'temporarily throttled']
    return any(word in driver.page_source for word in words)

def accept_terms(driver: webdriver.Firefox, steps: FetchSteps | None = None) -> None:
    """Accept the Terms and Conditions page if shown."""
    found = driver.find_elements(By.CSS_SELECTOR, "form input[type='submit'][name='terms_accept']")
    if any(not hidden_reason(driver, element) for element in found):
        if steps:
            steps.label('Accepting Terms and Conditions')
        else:
            print('Accepting Terms and Conditions')
        click_once(pick_visible(found, lambda element: hidden_reason(driver, element), 'I accept'))
        sleep_time()


DOWNLOAD_NAME = 'download_file'
BUTTONS = "input[type='submit'], input[type='button'], button"


def button_label(element: WebElement) -> str:
    """Button label as lowercase letters only ('Download!!' -> 'download')."""
    label = element.get_attribute('value') if element.tag_name == 'input' else element.get_attribute('textContent')
    return re.sub(r'[^a-z]', '', (label or '').lower())


# Returns why a button is hidden, or '' if visible. Hidden buttons may be bot traps.
HIDDEN_REASON_JS = """
const el = arguments[0];
if (el.disabled) return 'disabled';
if (el.type === 'hidden') return 'type=hidden';
if (el.closest('[hidden], [aria-hidden="true"], [inert]')) return 'hidden/aria-hidden/inert';
const style = getComputedStyle(el);
if (style.visibility !== 'visible') return 'visibility:' + style.visibility;
if (style.pointerEvents === 'none') return 'pointer-events:none';
let opacity = 1;
for (let node = el; node && node.nodeType === 1; node = node.parentElement) {
  const s = getComputedStyle(node);
  if (s.display === 'none') return 'display:none';
  if (s.clipPath && s.clipPath !== 'none') return 'clip-path';
  if (s.clip && s.clip !== 'auto') return 'clip';
  opacity *= parseFloat(s.opacity);
}
if (opacity < 0.5) return 'opacity ' + opacity.toFixed(2);
el.scrollIntoView({block: 'center', inline: 'center'});
const r = el.getBoundingClientRect();
if (r.width < 8 || r.height < 8) return 'too small ' + Math.round(r.width) + 'x' + Math.round(r.height);
if (r.right <= 0 || r.bottom <= 0 || r.left >= innerWidth || r.top >= innerHeight) return 'off-screen';
const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
if (!top || !(top === el || el.contains(top))) return 'covered by another element';
return '';
"""


def is_download_candidate(button: WebElement) -> bool:
    """Whether the button looks like the Download button."""
    return button.get_attribute('name') == DOWNLOAD_NAME or button_label(button).startswith('download')


def pick_download_button(
    buttons: list[WebElement], daily_form_buttons: list[WebElement], reason: Callable[[WebElement], str],
) -> WebElement:
    """Return the only visible Download button; raise if there is none or more than one."""
    candidates = [button for button in buttons if is_download_candidate(button)]
    usable, hidden = [], []
    for button in candidates:
        why = reason(button)
        (hidden if why else usable).append((button, why))
    if hidden:
        print(f'Ignoring {len(hidden)} hidden download-like button(s): {[why for _, why in hidden]}')
    if len(usable) == 1:
        return usable[0][0]
    if len(usable) > 1:
        msg = f'{len(usable)} visible download-like buttons, refusing to guess: {[button_label(b) for b, _ in usable]}'
        raise LookupError(msg)
    if not candidates:
        others = [b for b in daily_form_buttons if button_label(b) != 'request' and not reason(b)]
        if len(others) == 1:
            return others[0]
    msg = f'Download button not found (buttons: {[button_label(button) for button in buttons]})'
    raise LookupError(msg)


def hidden_reason(driver: webdriver.Firefox, element: WebElement) -> str:
    """Why the element is hidden from a person, or '' if visible."""
    return driver.execute_script(HIDDEN_REASON_JS, element)


def pick_visible(elements: list[WebElement], reason: Callable[[WebElement], str], what: str) -> WebElement:
    """Return the only visible element; raise if there is none or more than one."""
    reasons = [reason(element) for element in elements]
    hidden = [why for why in reasons if why]
    visible = [element for element, why in zip(elements, reasons, strict=True) if not why]
    if hidden:
        print(f'Ignoring {len(hidden)} hidden {what}: {hidden}')
    if len(visible) != 1:
        msg = f'Expected one visible {what}, found {len(visible)}'
        raise LookupError(msg)
    return visible[0]


def find_visible(driver: webdriver.Firefox, by: str, selector: str, what: str) -> WebElement:
    """Find the only visible element matching the selector."""
    return pick_visible(driver.find_elements(by, selector), lambda element: hidden_reason(driver, element), what)


def find_download_button(driver: webdriver.Firefox) -> WebElement:
    """Find the Download button shown after 'Request'."""
    driver.implicitly_wait(0)
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, BUTTONS)
        daily_form = ', '.join(f"form[name='daily'] {button}" for button in BUTTONS.split(', '))
        in_form = driver.find_elements(By.CSS_SELECTOR, daily_form)
        return pick_download_button(buttons, in_form, lambda button: hidden_reason(driver, button))
    finally:
        driver.implicitly_wait(10)


def click_once(element: WebElement) -> None:
    """Click once, natively (no script click)."""
    element.click()


def get_geckodriver_path() -> str:
    """Get the geckodriver path from configuration or default."""
    geckodriver_path = config.get('NOINTRO', 'geckodriver_path', fallback=None)
    if geckodriver_path is None:
        # Try to find geckodriver in PATH
        geckodriver_executable = shutil.which('geckodriver')
        if geckodriver_executable:
            return geckodriver_executable
        # Fallback to 'geckodriver' and let Selenium handle it
        return None
    return geckodriver_path

def download_daily(folder_helper: Folders, steps: FetchSteps) -> None:  # noqa: PLR0915
    """Download the Datomatic Love Pack."""
    # ruff: noqa: FBT003
    options = FirefoxOptions()
    # change user agent
    options.set_preference('general.useragent.override', config.get('NOINTRO', 'user_agent', fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0"))
    #change navigator platform
    options.set_preference('general.platform.override', config.get('NOINTRO', 'platform', fallback='Win32'))

    if config.getboolean('NOINTRO', 'headless', fallback=True):
        options.add_argument('--headless')
    # Marionette is enabled by default in modern Firefox
    options.set_preference('browser.download.folderList', 2)
    options.set_preference('browser.download.manager.showWhenStarting', False)
    # Use WSL path for download directory since we're using Linux Firefox
    options.set_preference('browser.download.dir', str(folder_helper.download))

    # Use Linux geckodriver
    geckodriver_path = get_geckodriver_path()
    service = Service(executable_path=geckodriver_path) if geckodriver_path is not None else None
    driver = webdriver.Firefox(service=service, options=options)
    # print([x for x in get_categories()])
    # exit()
    driver.implicitly_wait(10)
    steps.step('Opening Datomatic')
    driver.get('https://www.google.com')

    driver.get('https://datomatic.no-intro.org')

    sleep_time()

    try:
        steps.step('Checking Terms and Conditions')
        accept_terms(driver, steps)
        if downloads_disabled(driver):
            steps.label('Downloads suspended')
            steps.progress.stop()
            print('Downloads suspended')
            logger.error(driver.page_source)
            driver.close()
            return

        delete_temp_files_if_exists(folder_helper)

        steps.step('Getting to file download page')

        click_once(find_visible(driver, By.XPATH, "//a[contains(text(), 'Download')]", 'Download link'))

        sleep_time()
        click_once(find_visible(driver, By.XPATH, "//a[contains(text(), 'Daily')]", 'Daily link'))

        steps.step('Including categories')
        sleep_time()

        for category, metadata in get_categories():
            steps.step(f'Including {category}')
            selector = f"input[name='{metadata['link']}']"
            checkbox = find_visible(driver, By.CSS_SELECTOR, selector, f'{category} checkbox')
            if not checkbox.is_selected():
                click_once(checkbox)
                sleep_time()

        driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        # now the name is daily_dl_2026-05-30 (with the date of the day)
            # <input type="submit" name="daily_dl_2026-05-30" value="Request">
        steps.step('Requesting the pack')
        request = "form input[type='submit'][value^='Request']"
        click_once(find_visible(driver, By.CSS_SELECTOR, request, 'Request button'))
        sleep_time()

        steps.step('Downloading')
        sleep_time()
        download_button = find_download_button(driver)
        click_once(download_button)

        steps.step('Waiting for download to finish')
        while not is_download_finished(folder_helper):
            size = downloaded_size(folder_helper)
            steps.label(f'Waiting for download to finish ({size})' if size else 'Waiting for download to finish')
            time.sleep(2)

    except Exception as exc:  # noqa: BLE001
        print(exc)

    driver.close()


def get_downloaded_file(folder_helper: Folders) -> str:
    """Get the downloaded file."""
    downloaded_files = sorted(Path(folder_helper.download).glob('*.zip'))
    if len(downloaded_files) == 0:
        msg = 'No downloaded files found'
        raise Exception(msg) # noqa: TRY002
    return downloaded_files[-1]


def extract_dats(downloaded_file: str, folder_helper: Folders) -> None:
    """Extract the DAT files."""
    with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
        zip_ref.extractall(folder_helper.dats)


def download_dats(folder_helper: Folders) -> None:
    """Download DAT files, with one progress bar over all the steps."""
    with FetchSteps(total_steps()) as steps:
        download_daily(folder_helper, steps)
        try:
            downloaded_file = get_downloaded_file(folder_helper)
        except Exception:  # noqa: BLE001
            steps.progress.stop()
            logger.exception('Error downloading dats')
            return
        steps.step('Extracting dats')
        extract_dats(downloaded_file, folder_helper)
        move_path(downloaded_file, folder_helper.backup)
        steps.finish('Fetched')


def fetch() -> None:
    """Fetch and download DAT files."""
    folder_helper = Folders(seed=__prefix__)
    folder_helper.clean_dats()
    folder_helper.create_all()
    download_dats(folder_helper)
