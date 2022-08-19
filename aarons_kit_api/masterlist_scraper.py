import json
import os
import random
import time
import codecs
import bibtexparser
import pandas as pd
import base64
import numpy as np

from datetime import datetime
from pyvirtualdisplay import Display
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from aarons_kit_api.models import (
    Journal,
    Issue,
    Article,
    Author,
)

# Sets up the webdriver on the selenium grid machine.
# The grid ochestrates the tests on the various machines that are setup.
# We only setup the chrome instaled machine for the scraper.
def remote_driver_setup():
    # Set directory to be current file
    directory = os.path.dirname(__file__)

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_extension(
        os.path.join(directory, 'scraper_data/extension_1_38_6_0.crx')
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option(
        "prefs",
        {
            # Set default directory for downloads. 
            # It doesn't matter here because the download happens in the remote machines file system
            # "download.default_directory": os.path.join(directory, 'scraper_data'),
            
            # Auto download files
            "download.prompt_for_download": False,  
            
            # "download.directory_upgrade": True,

            # It will not show PDF directly in chrome
            "plugins.always_open_pdf_externally": True,  

            # gets rid of password saver popup
            "credentials_enable_service": False,  

            # gets rid of password saver popup
            "profile.password_manager_enabled": False,  
        },
    )

    driver = webdriver.Remote(
        command_executor="http://host.docker.internal:4444/wd/hub",
        options=chrome_options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver

# Downloads the list of journals as a txt from the jstor and returns it as a pandas dataframe
def fetch_journal_data():
    directory = os.path.dirname(__file__)
    url = "https://www.jstor.org/kbart/collections/all-archive-titles?contentType=journals"

    journal_data_path = os.path.join(directory, "scraper_data/journal_data.txt")

    with urlopen(url) as response:
        body = response.read()

    character_set = response.headers.get_content_charset()
    new_data = body.decode(character_set)
    with open(journal_data_path, encoding="utf-8", mode="w") as file:
        file.write(new_data)

    df = pd.read_csv(journal_data_path, sep="\t")
    os.remove(journal_data_path)
    return df

# Renames the columns and saves into DB if they aren't in already
def get_journal_data():

    journal_data = fetch_journal_data()

    # remove the dash print_identifier
    journal_data["print_identifier"].str.replace("-","")

    journal_data.rename(columns=
        {
            "publication_title":"journalName",
            "print_identifier":"issn",
            "online_identifier":"altISSN",
            "title_url":"url"
        } ,inplace=True)

    sm_journal_data = journal_data[["issn", "altISSN", "journalName","url"]]
    
    save_db_journals(sm_journal_data)

    return sm_journal_data

def save_db_journals(db_journal_data):
    # convert to dict so as to iterate
    journal_records = db_journal_data.to_dict('records')

    model_instances = [Journal(
        altISSN=record['altISSN'],
        issn=record['issn'],
        journalName=record['journalName'],
        url=record['url']
    ) for record in journal_records]

    Journal.objects.bulk_create(model_instances, ignore_conflicts=True)

def filter_issues_urls(issue_url_list):
    remove_urls = Issue.objects.filter(url__in=issue_url_list).values_list('url', flat=True)
    filtered_list = list(set(issue_url_list) - set(remove_urls))
    return filtered_list

# This is the main method for scrapping all journals
def scrape_all_journals():
    
    driver = remote_driver_setup()

    journal_urls = get_journal_data()["url"]
    
    # we'll iterate all journals and only skip scrapped issues
    for journal_url in journal_urls:
        scrape_journal(driver, journal_url)

    driver.quit()

def load_page(driver, journal_url):
    page_loaded = False

    while not page_loaded:
        # Retrieving journal data
        driver.get(journal_url)
        time.sleep(5)
        driver.maximize_window()

        try:
            WebDriverWait(driver, 5).until(
                expected_conditions.presence_of_element_located(
                    (By.ID, "onetrust-consent-sdk")
                )
            )
            print("passed")
            rotated = "False"
            page_loaded = True
        except:
            print("Failed to access journal page")
            
            # Connect to new server
            # expressvpn(directory, vpn_list(directory))
            rotated = "True"

def accept_cookies(driver, journal_url):
    try:
        WebDriverWait(driver, 5).until(
            expected_conditions.element_to_be_clickable(
                (By.XPATH, r"//button[@id='onetrust-accept-btn-handler']")
            )
        )

        driver.find_element(
            By.XPATH, r".//button[@id='onetrust-accept-btn-handler']"
        ).click()
        print("cookies accepted")
    except:
        print("No cookies, continue")

    time.sleep(5)

def scrape_issue_urls(driver, journal_url):
    
    random.seed(time.time())
    issue_url_list = []

    click = driver.find_elements(
        By.XPATH, r".//div[@class='accordion-container']//details"
    )

    # print("details number: "+str(len(click)))

    # expand the decade drawers one by one
    for element in click:
        time.sleep(5)
        element.click()

    time.sleep(2)

    # captures the year elements within the decade
    decade_List = driver.find_elements(By.XPATH, r".//dd//ul//li")

    # print("decades number: "+str(len(decade_List)))

    # captures the issues of the year element and records the issue url
    for element in decade_List:
        year_list = element.find_elements(By.XPATH, r".//ul//li//collection-view-pharos-link")
        temp = element.get_attribute("data-year")
        if temp == None:
            continue
        for item in year_list:
            issue_url = item.get_attribute("href")
            if (not issue_url.startswith("http") and not issue_url.startswith("https")):
                issue_url = "https://www.jstor.org"+issue_url
            issue_url_list.append(issue_url)

    issue_url_list = filter_issues_urls(issue_url_list)

    # print("issue number: "+str(len(issue_url_list)))

    # filter out scraped issues by url
    return issue_url_list

def download_citations(driver, issue_url):
    time.sleep(5 * random.random())
    print("driver url: "+issue_url)
    driver.get(issue_url)

    try:
        # Download Citations
        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (
                    By.XPATH,
                    r".//toc-view-pharos-checkbox[@id='select_all_citations']/span[@slot='label']",
                )
            )
        ).click()
        
        # print("citations 1")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable((By.ID, "bulk-cite-button"))
        ).click()

        # print("citations 2")

        time.sleep(10)

        # click the link to download the bibtex
        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (
                    By.XPATH,
                    r"//*[@id='bulk-citation-dropdown']/mfe-bulk-cite-pharos-dropdown-menu-item[5]",
                )
            )
        ).click()

        # print("citations 3")
    except Exception as e:
        print(e)
        input()

def scrape_journal(driver, journal_url):
    directory = os.path.dirname(__file__)

    scrape_start = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    scraper_log_path = os.path.join(directory, "scraper_data/scraper_log.txt")

    load_page(driver, journal_url)

    accept_cookies(driver, journal_url)

    issue_url_list = scrape_issue_urls(driver, journal_url)
    
    # loops through a dataframe of issue urls and captures metadata per issue
    for issue_url in issue_url_list:
        
        download_citations(driver, issue_url)

        old_name = os.path.join(directory, "scraper_data/citations.txt")
        new_name = os.path.join(directory, "scraper_data/" + issue_url.split("/")[-1] + ".txt")

        files = WebDriverWait(driver, 20, 1).until(get_downloaded_files)
        print("number of downloads: "+str(len(files)))
        print(files[0])

        # get the content of the first file remotely
        content = get_file_content(driver, files[0])

        # save the content in a local file in the working directory
        with open(old_name, 'wb') as f:
            f.write(content)

        os.rename(old_name, new_name)

        time.sleep(2)

        with open(new_name) as bibtex_file:
            citations_data = bibtexparser.load(bibtex_file)
        
        save_citations_data(pd.DataFrame(citations_data.entries), journal_url, issue_url)
        
        os.remove(new_name)

    scrape_end = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    # Append log file
    with open(scraper_log_path, "a+") as log:
        log.write("\n")
        log.write("\nJournal: " + journal_url)
        log.write("\nNumber of Issues scraped: " + str(len(issue_url_list)))
        log.write("\nStart time: " + scrape_start)
        log.write("\nEnd time: " + scrape_end)

def save_citations_data(citations_data, journal_url, issue_url):
    print("saving citations: "+journal_url+" "+issue_url)

    # save the journal
    journal_data = citations_data.iloc[0].to_dict()

    journal_result = Journal.objects.get_or_create(
        issn=journal_data["issn"],
        defaults={
            "journalName": journal_data["journal"],
            "url": journal_url,
            "altISSN": journal_data.get("altissn",""),
        },
    )

    # save the issue
    issue_result = Issue.objects.get_or_create(
        defaults={
            "journal": journal_result[0],
            "url": issue_url,
            "volume": journal_data["volume"],
            "number": journal_data["number"],
            "year": journal_data["year"],
        },
    )

    # save articles
    citation_records = citations_data.to_dict('records')

    for record in citation_records:

        # store article
        article_result = Article.objects.get_or_create(
            defaults={
                "issue": issue_result[0],
                "title": record["title"],
                "abstract": record.get("abstract", ""),
                "url": record.get("url", ""),
            },
        )
        # store author
        if str(record.get("author")) != "nan":
            names = record.get("author").split("and")
            for name in names:
                author_result = Author.objects.get_or_create(authorName=name.strip())
                article_result[0].authors.add(author_result[0])


def get_downloaded_files(driver):
    if not driver.current_url.startswith("chrome://downloads"):
        driver.get("chrome://downloads/")

    return  driver.execute_script( \
        "return  document.querySelector('downloads-manager')  "
        " .shadowRoot.querySelector('#downloadsList')         "
        " .items.filter(e => e.state === 'COMPLETE')          "
        " .map(e => e.filePath || e.file_path || e.fileUrl || e.file_url); ")

def get_file_content(driver, path):
    elem = driver.execute_script( \
        "var input = window.document.createElement('INPUT'); "
        "input.setAttribute('type', 'file'); "
        "input.hidden = true; "
        "input.onchange = function (e) { e.stopPropagation() }; "
        "return window.document.documentElement.appendChild(input); " )

    elem._execute('sendKeysToElement', {'value': [ path ], 'text': path})

    result = driver.execute_async_script( \
        "var input = arguments[0], callback = arguments[1]; "
        "var reader = new FileReader(); "
        "reader.onload = function (ev) { callback(reader.result) }; "
        "reader.onerror = function (ex) { callback(ex.message) }; "
        "reader.readAsDataURL(input.files[0]); "
        "input.remove(); "
        , elem)

    if not result.startswith('data:') :
        raise Exception("Failed to get file content: %s" % result)

    return base64.b64decode(result[result.find('base64,') + 7:])


def save_current_page(path, driver):
    #open file in write mode with encoding
    f = codecs.open(path, "w", "utf−8")
    #obtain page source
    h = driver.page_source
    #write page source content to file
    f.write(h)

