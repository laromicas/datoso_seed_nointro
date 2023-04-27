from pathlib import Path
import shutil
import sys
import time
import random
import zipfile

from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By

from datoso_seed_nointro import __preffix__
from datoso.configuration.folder_helper import Folders


def execute_with_retry(method, max_attempts):
    """Executes a method with several times until it fails all or is executed fine."""
    exc = None
    for _ in range(0, max_attempts):
        try:
            return method()
        except Exception as exc:
            print(exc)
            time.sleep(1)
    if exc is not None:
        raise exc
    return None


def sleep_time():
    """Sleeps for a random time."""
    time.sleep(random.random() * 3 + 4)


def is_download_finished(folder_helper) -> bool:
    """Checks if the download is finished."""
    firefox_temp_file = sorted(Path(folder_helper.download).glob('*.part'))
    chrome_temp_file = sorted(Path(folder_helper.download).glob('*.crdownload'))
    downloaded_files = sorted(Path(folder_helper.download).glob('*.*'))
    return (len(firefox_temp_file) == 0) and \
       (len(chrome_temp_file) == 0) and \
       (len(downloaded_files) >= 1)


def downloads_disabled(driver) -> bool:
    """Checks if the downloads in Datomatic are disabled."""
    words = ['temporary suspended', 'temporary disabled']
    return any(word in driver.page_source for word in words)


def download_daily(folder_helper):
    """Downloads the Datomatic Love Pack."""
    options = FirefoxOptions()
    # options.add_argument("--headless")
    options.set_capability("marionette", True)
    options.set_preference("browser.download.folderList", 2)
    options.set_preference("browser.download.manager.showWhenStarting", False)
    options.set_preference("browser.download.dir", folder_helper.download)
    options.set_preference("browser.download.folderList", 2)

    driver = webdriver.Firefox(options=options)

    driver.implicitly_wait(10)
    driver.get("https://www.google.com")

    driver.get("https://datomatic.no-intro.org")

    sleep_time()

    try:

        if downloads_disabled(driver):
            print("Downloads suspended")
            driver.close()
            sys.exit(1)

        print("Getting to file download page")

        # driver.manage().timeouts().implicitlyWait(5, TimeUnit.SECONDS)
        download_button = driver.find_element(By.XPATH, "//a[contains(text(), 'Download')]")
        download_button.click()

        sleep_time()
        daily_link = driver.find_element(By.XPATH, "//a[contains(text(), 'Daily')]")
        daily_link.click()

        print("Including aftermarket")
        sleep_time()
        aftermarket = driver.find_element(By.CSS_SELECTOR, "input[name='include_additional']")
        if not aftermarket.is_selected():
            aftermarket.click()

        sleep_time()
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        prepare_button = driver.find_element(By.CSS_SELECTOR, "form[name='daily'] input[type='submit']")

        sleep_time()
        prepare_button.click()

        print("Downloading")
        sleep_time()
        download_button = driver.find_element(By.CSS_SELECTOR, "form[name='opt_form'] input[name='lazy_mode']")
        download_button.click()

        while not is_download_finished(folder_helper):
            print("Waiting for download to finish")
            time.sleep(10)

    except Exception as exc:
        print(exc)

    driver.close()


def get_downloaded_file(folder_helper) -> str:
    """Gets the downloaded file."""
    downloaded_files = sorted(Path(folder_helper.download).glob('*.zip'))
    if len(downloaded_files) == 0:
        raise Exception("No downloaded file")
    return downloaded_files[-1]


def extract_dats(downloaded_file, folder_helper: Folders):
    with zipfile.ZipFile(downloaded_file, 'r') as zip_ref:
        filelist = zip_ref.filelist
        for file in filelist:
            if file.filename.endswith('txt'):
                continue
            file_name = file.filename
            file.filename = Path(file_name).name
            zip_ref.extract(file, folder_helper.dats)
            file.filename = file_name


def download_dats(folder_helper: Folders):
    download_daily(folder_helper)
    downloaded_file = get_downloaded_file(folder_helper)
    print('Extracting dats')
    extract_dats(downloaded_file, folder_helper)
    shutil.move(downloaded_file, folder_helper.backup)


def fetch():
    folder_helper = Folders(seed=__preffix__)
    folder_helper.clean_dats()
    folder_helper.create_all()
    download_dats(folder_helper)
