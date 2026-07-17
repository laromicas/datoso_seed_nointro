"""Fetch and download DAT files."""
import random
import shutil
import time
import zipfile
from collections.abc import Callable
from pathlib import Path

from datoso.configuration import config, logger
from datoso.configuration.folder_helper import Folders
from datoso.helpers.file_utils import move_path
from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service

from datoso_seed_nointro import __prefix__
from datoso_seed_nointro.common import get_categories


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

def download_daily(folder_helper: Folders) -> None:
    """Download the Datomatic Love Pack."""
    # ruff: noqa: FBT003, PLR0915
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
    driver.get('https://www.google.com')

    driver.get('https://datomatic.no-intro.org')

    sleep_time()

    try:
        if downloads_disabled(driver):
            print('Downloads suspended')
            logger.error(driver.page_source)
            driver.close()
            return

        delete_temp_files_if_exists(folder_helper)

        print('Getting to file download page')

        download_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Download')]")
        download_button.click()

        sleep_time()
        daily_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Daily')]")
        daily_link.click()

        print('Including categories')
        sleep_time()

        for category, metadata in get_categories():
            category_link = driver.find_element(By.CSS_SELECTOR, "input[name='" + metadata['link'] + "']")
            if not category_link.is_selected():
                print(f'Including {category}')
                category_link.click()
                sleep_time()

        driver.execute_script('window.scrollTo(0, document.body.scrollHeight);')
        # now the name is daily_dl_2026-05-30 (with the date of the day)
            # <input type="submit" name="daily_dl_2026-05-30" value="Request">
        request_button = driver.find_element(By.CSS_SELECTOR, "form input[type='submit'][value^='Request']")
        request_button.click()
        sleep_time()

        print('Downloading')
        sleep_time()
        input_valid_values = [
            'Download....','Download!!!!',
            'Download...','Download!!!',
            'Download..','Download!!',
            'Download.','Download!',
            'Download',
            ]
        download_button = None
        for value in input_valid_values:
            try:
                download_button = driver.find_element(By.CSS_SELECTOR, "form input[type='submit'][value^='" + value + "']")
                break
            except Exception: # noqa: S110, BLE001
                pass
        if download_button is None:
            msg = 'Download button not found'
            raise LookupError(msg) # noqa: TRY301

        driver.execute_script('arguments[0].scrollIntoView(true);', download_button)
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', download_button)
        driver.execute_script("arguments[0].style.display = 'block';", download_button)
        driver.execute_script("arguments[0].style.visibility = 'visible';", download_button)
        driver.execute_script("arguments[0].style.opacity = '1';", download_button)

        driver.execute_script('arguments[0].click();', download_button)
        download_button.click() #noqa: ERA001 RUF100

        while not is_download_finished(folder_helper):
            print('Waiting for download to finish')
            time.sleep(10)

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
    """Download DAT files."""
    download_daily(folder_helper)
    try:
        downloaded_file = get_downloaded_file(folder_helper)
    except Exception:
        logger.exception('Error downloading dats')
        return
    print('Extracting dats')
    extract_dats(downloaded_file, folder_helper)
    move_path(downloaded_file, folder_helper.backup)


def fetch() -> None:
    """Fetch and download DAT files."""
    folder_helper = Folders(seed=__prefix__)
    folder_helper.clean_dats()
    folder_helper.create_all()
    download_dats(folder_helper)
