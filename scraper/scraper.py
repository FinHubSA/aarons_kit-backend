import json
import os
import random
import time
import codecs
import bibtexparser
import pandas as pd
import base64
import numpy as np

from django.db import transaction
from django.db.models import Q, F

from datetime import datetime
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.remote import remote_connection

from api.models import (
    Journal,
    Issue,
    Article,
    Author,
)

# This is the main method for scrapping all journals
def scrape_all_journals():

    driver = remote_driver_setup()

    update_journal_data()

    journals = get_journals_to_scrape(True)

    if journals is not None:
        # we'll iterate all journals and only skip scraped issues
        for journal in journals:
            scrape_journal(driver, journal, -1)

    driver.quit()


def get_masterlist_state():
    journals_count = Journal.objects.all().count()

    unscraped_journals_count = Journal.objects.filter(numberOfIssuesScraped=0).count()

    scraping_journals_count = Journal.objects.filter(
        Q(numberOfIssuesScraped__gt=0)
        & Q(numberOfIssues__gt=F("numberOfIssuesScraped"))
    ).count()

    scraped_journals_count = Journal.objects.filter(
        Q(numberOfIssuesScraped__gt=0) & Q(numberOfIssuesScraped=F("numberOfIssues"))
    ).count()

    return (
        journals_count,
        unscraped_journals_count,
        scraping_journals_count,
        scraped_journals_count,
    )


def print_masterlist_state():

    (
        journals_count,
        unscraped_journals_count,
        scraping_journals_count,
        scraped_journals_count,
    ) = get_masterlist_state()

    print("***  Masterlist State  ***")
    print("Total Journals       : ", journals_count)
    print(
        "Unscraped Journals : ",
        "{0:.0f}%".format(unscraped_journals_count / float(journals_count) * 100),
    )
    print(
        "Scraping Journals  : ",
        "{0:.0f}%".format(scraping_journals_count / float(journals_count) * 100),
    )
    print(
        "Scraped Journals   : ",
        "{0:.0f}%".format(scraped_journals_count / float(journals_count) * 100),
    )
    print("*** -Masterlist State- ***")


# count is the amount of new issues to scrape
# For unlimited count of scraping put a negative number
# This is useful when the scraping task service has a time limit
def scrape_journal(driver, journal, issue_scrape_count=-1):
    journal_url = journal.url

    print("scrapping journal " + journal.url)

    directory = os.path.dirname(__file__)

    scrape_start = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    scraper_log_path = os.path.join(directory, "data/logs/scraper_log.txt")

    load_page(driver, journal_url, issue_scrape_count)

    accept_cookies(driver, journal_url)

    issue_url_list, original_issue_url_list = scrape_issue_urls(driver, journal_url)
    number_of_issues = len(original_issue_url_list)

    if len(issue_url_list) == 0:
        journal.numberOfIssuesScraped = len(original_issue_url_list)
        save_journal(journal, number_of_issues, {})
        return

    count = 0
    # loops through a dataframe of issue urls and captures metadata per issue
    for issue_url in issue_url_list:

        if count == issue_scrape_count:
            break

        downloaded = download_citations(driver, issue_url)

        if not downloaded:
            continue

        old_name = os.path.join(directory, "data/logs/citations.txt")
        new_name = os.path.join(
            directory, "data/logs/" + issue_url.split("/")[-1] + ".txt"
        )

        files = WebDriverWait(driver, 20, 1).until(get_downloaded_files)
        print("number of downloads: " + str(len(files)))
        print(files[0])

        # get the content of the first file remotely
        content = get_file_content(driver, files[0])

        # save the content in a local file in the working directory
        with open(old_name, "wb") as f:
            f.write(content)

        os.rename(old_name, new_name)

        time.sleep(2)

        with open(new_name) as bibtex_file:
            citations_data = bibtexparser.load(bibtex_file)

        save_issue_articles(
            pd.DataFrame(citations_data.entries), journal, issue_url, number_of_issues
        )

        os.remove(new_name)

        count = count + 1

    scrape_end = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

    # Append log file
    with open(scraper_log_path, "a+") as log:
        log.write("\n")
        log.write("\nJournal: " + journal_url)
        log.write("\nNumber of Issues scraped: " + str(len(issue_url_list)))
        log.write("\nStart time: " + scrape_start)
        log.write("\nEnd time: " + scrape_end)

    return {"message": "Scraped {}".format(journal.journalName)}


# Sets up the webdriver on the selenium grid machine.
# The grid ochestrates the tests on the various machines that are setup.
# We only setup the chrome instaled machine for the scraper.
def remote_driver_setup(timeout=None):
    # Set directory to be current file
    directory = os.path.dirname(__file__)

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_extension(
        os.path.join(directory, "data/tools/extension_1_38_6_0.crx")
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option(
        "prefs",
        {
            # Set default directory for downloads.
            # It doesn't matter here because the download happens in the remote machines file system
            # "download.default_directory": os.path.join(directory, 'data'),
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

    selenium_connection = remote_connection.RemoteConnection(
        "https://selenium-browser-mrz6aygprq-oa.a.run.app/wd/hub"
    )
    # timeout is in seconds
    if not (timeout is None):
        selenium_connection.set_timeout(timeout)

    driver = webdriver.Remote(
        selenium_connection,
        # command_executor = "https://selenium-browser-mrz6aygprq-oa.a.run.app/wd/hub",
        options=chrome_options,
    )

    return driver


# Downloads the list of journals as a txt from the jstor and returns it as a pandas dataframe
def fetch_journal_data():
    directory = os.path.dirname(__file__)
    url = "https://www.jstor.org/kbart/collections/all-archive-titles?contentType=journals"

    if not os.path.exists(os.path.join(directory, "data/logs")):
        os.makedirs(os.path.join(directory, "data/logs"))

    journal_data_path = os.path.join(directory, "data/logs/journal_data.txt")

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
def update_journal_data():

    journal_data = fetch_journal_data()

    # remove the dash print_identifier
    journal_data["print_identifier"] = journal_data["print_identifier"].str.replace(
        "-", ""
    )

    journal_data["online_identifier"] = journal_data["online_identifier"].str.replace(
        "-", ""
    )

    journal_data.rename(
        columns={
            "publication_title": "journalName",
            "print_identifier": "issn",
            "online_identifier": "altISSN",
            "title_url": "url",
            "date_last_issue_online": "lastIssueDate",
        },
        inplace=True,
    )

    journal_data["issn"].fillna(journal_data["altISSN"], inplace=True)

    sm_journal_data = journal_data[
        ["issn", "altISSN", "journalName", "url", "lastIssueDate"]
    ]

    save_db_journals(sm_journal_data)


def save_db_journals(db_journal_data):

    # get all the records first
    journal_objects = Journal.objects.all()

    print("** starting journals update")

    # convert to dict so as to iterate
    # journal_records = db_journal_data.to_dict('records')
    journal_groups = db_journal_data.groupby("issn")

    for record in journal_objects:

        if record.issn in journal_groups.groups.keys():
            journal_update = journal_groups.get_group(record.issn)

            record.lastIssueDate = journal_update.iloc[0]["lastIssueDate"]

    # update the records
    if journal_objects.exists():
        print("** doing bulk update **", journal_objects.count())

        Journal.objects.bulk_update(journal_objects, ["lastIssueDate"])

        print("** after bulk update **")

    print("** doing bulk create")
    journal_records = db_journal_data.to_dict("records")

    # create those that aren't there
    model_instances = [
        Journal(
            altISSN=record["altISSN"],
            issn=record["issn"],
            journalName=record["journalName"],
            url=record["url"],
            lastIssueDate=record["lastIssueDate"],
        )
        for record in journal_records
    ]

    Journal.objects.bulk_create(model_instances, ignore_conflicts=True)

    print("** done journals create ", len(journal_records))


# Gets a journal that hasn't been scraped at all or with a new issue to be scraped
def get_journals_to_scrape(get_all):
    result = Journal.objects.filter(
        Q(numberOfIssues__gt=F("numberOfIssuesScraped"))
        | ~Q(lastIssueDate=F("lastIssueDateScraped"))
    )

    if result:
        if get_all:
            return result
        else:
            return result[0]

    return None


def filter_issues_urls(issue_url_list):

    remove_urls = Issue.objects.filter(url__in=issue_url_list).values_list(
        "url", flat=True
    )
    filtered_list = list(set(issue_url_list) - set(remove_urls))
    return filtered_list


def load_page(driver, journal_url, issue_scrape_count):

    try:
        driver.get(journal_url)
        time.sleep(5)
        driver.maximize_window()

        WebDriverWait(driver, 5).until(
            expected_conditions.presence_of_element_located(
                (By.ID, "onetrust-consent-sdk")
            )
        )
        print("passed")

    except:
        print("Failed to access journal page")

        driver = remote_driver_setup()
        journal = get_journals_to_scrape(False)
        scrape_journal(driver, journal, issue_scrape_count)


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

    # click = driver.find_elements(
    #     By.XPATH, r".//div[@class='accordion-container']//details"
    # )

    # print("details number: " + str(len(click)))

    # expand the decade drawers one by one
    # for element in click:
    #     time.sleep(2)
    #     try:
    #         element.click()
    #     except:
    #         print("not clickable", element.get_attribute("class"))

    time.sleep(2)

    # captures the year elements within the decade
    decade_List = driver.find_elements(By.XPATH, r".//div//ol//li")

    # print("decades number: " + str(len(decade_List)))

    # captures the issues of the year element and records the issue url
    for element in decade_List:
        year_list = element.find_elements(
            By.XPATH, r".//ol//li//collection-view-pharos-link"
        )
        temp = element.get_attribute("data-year")
        if temp == None:
            continue
        for item in year_list:
            issue_url = item.get_attribute("href")
            if not issue_url.startswith("http") and not issue_url.startswith("https"):
                issue_url = "https://www.jstor.org" + issue_url
            issue_url_list.append(issue_url)

    # print("issue number before filter: " + str(len(issue_url_list)))
    original_issue_url_list = issue_url_list

    issue_url_list = filter_issues_urls(issue_url_list)

    # print("issue number after filter: " + str(len(issue_url_list)))

    # filter out scraped issues by url
    return issue_url_list, original_issue_url_list


def download_citations(driver, issue_url):
    time.sleep(5 * random.random())
    driver.get(issue_url)

    print("download citations ", issue_url)

    try:
        # Download Citations
        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable(
                (
                    By.XPATH,
                    r".//*[@id='select_all_citations']/span[@slot='label']",
                )
            )
        ).click()

        # print("citations 1")

        WebDriverWait(driver, 10).until(
            expected_conditions.element_to_be_clickable((By.ID, "bulk-cite-button"))
        ).click()

        # print("citations 2")

        time.sleep(5)

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

        return True
    except Exception as e:
        print("failed to download citations for ", issue_url)
        return False


# This must run atomically
@transaction.atomic
def save_issue_articles(citations_data, journal, issue_url, number_of_issues):

    # print("** columns: ", citations_data.head())

    if "volume" in citations_data:
        citations_data["volume"] = pd.to_numeric(
            citations_data["volume"], errors="coerce"
        ).fillna(0)

    if "number" in citations_data:
        citations_data["number"] = pd.to_numeric(
            citations_data["number"], errors="coerce"
        ).fillna(0)

    journal_data = citations_data.iloc[0].to_dict()

    print(
        "saving citations: "
        + issue_url
        + " number: "
        + str(journal_data.get("volume", ""))
        + " issue: "
        + str(journal_data.get("number", ""))
    )

    # save the issue
    issue, issue_created = save_issue(issue_url, journal, journal_data)

    # if issue was created update the journal
    if issue_created:
        save_journal(journal, number_of_issues, journal_data)

    articles_ids, authors_names, article_author_names = save_articles_and_authors(
        citations_data, issue
    )

    save_article_author_relations(articles_ids, authors_names, article_author_names)


def save_issue(issue_url, journal, journal_data):
    issue_id = issue_url.rsplit("/", 1)[-1]

    issue, issue_created = Issue.objects.get_or_create(
        url=issue_url,
        defaults={
            "journal": journal,
            "issueJstorID": issue_id,
            "url": issue_url,
            "volume": journal_data.get("volume", "0"),
            "number": journal_data.get("number", "0"),
            "year": journal_data["year"],
        },
    )

    return issue, issue_created


def save_journal(journal, number_of_issues, journal_data):
    number_of_issues_scraped = journal.numberOfIssuesScraped + 1

    print(
        "number of issues: "
        + str(number_of_issues)
        + " number of issues scraped: "
        + str(number_of_issues_scraped)
    )

    journal.numberOfIssues = number_of_issues

    if number_of_issues <= number_of_issues_scraped:
        journal.numberOfIssuesScraped = number_of_issues
        journal.lastIssueDateScraped = journal.lastIssueDate
    else:
        journal.numberOfIssuesScraped = number_of_issues_scraped
        journal.lastIssueDateScraped = journal_data["year"] + "-01-01"

    journal.save()


def save_articles_and_authors(citations_data, issue):

    article_records = citations_data.to_dict("records")

    article_author_names = {}

    articles = []
    authors = []

    articles_ids = []
    authors_names = []

    for record in article_records:

        if record["title"] == "Front Matter" or record["title"] == "Back Matter":
            continue

        articles.append(
            Article(
                issue=issue,
                articleJstorID=record["ID"],
                title=record["title"],
                abstract=record.get("abstract", ""),
                articleURL=record.get("url", ""),
            )
        )

        articles_ids.append(record.get("ID", ""))

        try:
            if record.get("author"):

                names = [x.strip() for x in record.get("author").split("and")]
                article_author_names[record.get("ID", "")] = names

                for name in names:
                    authors.append(Author(authorName=name))

                    authors_names.append(name)
        except:
            # print(
            #     "failed to store authors: "
            #     + str(record.get("author", ""))
            #     + " url: "
            #     + record["url"]
            # )
            pass

    # save articles and authors
    Article.objects.bulk_create(articles, ignore_conflicts=True)
    Author.objects.bulk_create(authors, ignore_conflicts=True)

    print("completed bulk author and article save")

    return articles_ids, authors_names, article_author_names


def save_article_author_relations(articles_ids, authors_names, article_author_names):

    print("saving article author relations")

    saved_articles = Article.objects.filter(articleJstorID__in=articles_ids)
    saved_authors = Author.objects.filter(authorName__in=authors_names)

    authors_dict = {}
    for author in saved_authors:
        authors_dict[author.authorName] = author

    ArticleAuthorModel = Article.authors.through
    article_authors = []

    # link articles and authors
    for article in saved_articles:
        if article.articleJstorID in article_author_names:
            author_names = article_author_names[article.articleJstorID]

            for name in author_names:
                # print("article id: "+str(article.articleID)+" author id: "+str(author.authorID))
                author = authors_dict[name]
                article_authors.append(
                    ArticleAuthorModel(
                        article_id=article.articleID, author_id=author.authorID
                    )
                )

    ArticleAuthorModel.objects.bulk_create(article_authors, ignore_conflicts=True)

    print("completed article author relations")


def get_downloaded_files(driver):
    if not driver.current_url.startswith("chrome://downloads"):
        driver.get("chrome://downloads/")

    return driver.execute_script(
        "return  document.querySelector('downloads-manager')  "
        " .shadowRoot.querySelector('#downloadsList')         "
        " .items.filter(e => e.state === 'COMPLETE')          "
        " .map(e => e.filePath || e.file_path || e.fileUrl || e.file_url); "
    )


def get_file_content(driver, path):
    elem = driver.execute_script(
        "var input = window.document.createElement('INPUT'); "
        "input.setAttribute('type', 'file'); "
        "input.hidden = true; "
        "input.onchange = function (e) { e.stopPropagation() }; "
        "return window.document.documentElement.appendChild(input); "
    )

    elem._execute("sendKeysToElement", {"value": [path], "text": path})

    result = driver.execute_async_script(
        "var input = arguments[0], callback = arguments[1]; "
        "var reader = new FileReader(); "
        "reader.onload = function (ev) { callback(reader.result) }; "
        "reader.onerror = function (ex) { callback(ex.message) }; "
        "reader.readAsDataURL(input.files[0]); "
        "input.remove(); ",
        elem,
    )

    if not result.startswith("data:"):
        raise Exception("Failed to get file content: %s" % result)

    return base64.b64decode(result[result.find("base64,") + 7 :])


def save_current_page(path, driver):
    # open file in write mode with encoding
    f = codecs.open(path, "w", "utf−8")
    # obtain page source
    h = driver.page_source
    # write page source content to file
    f.write(h)
