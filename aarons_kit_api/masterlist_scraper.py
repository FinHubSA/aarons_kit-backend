import json
import os
import random
import time
import codecs
import bibtexparser
import pandas as pd
import os, time, base64

from datetime import datetime
from pyvirtualdisplay import Display
from urllib.request import urlopen

from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

def start_scraping():
    # Set directory and import journal list
    directory = os.path.dirname(__file__)
    journal_list = clean_data()["title_url"]

    # Start VPN Service (choose high performance service for initial scrape)
    # expressvpn(directory, "UK - London")

    # display = Display(visible=False, size=(800, 600))
    # display.start()

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Safari/537.36"
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f"user-agent={USER_AGENT}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    # chrome_options.add_argument("--headless")
    chrome_options.add_extension(
        os.path.join(directory, 'scraper_data/extension_1_38_6_0.crx')
    )
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    chrome_options.add_experimental_option(
        "prefs",
        {
            # "download.default_directory": os.path.join(directory, 'scraper_data'),  # Change default directory for downloads
            "download.prompt_for_download": False,  # To auto download the file
            # "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,  # It will not show PDF directly in chrome
            "credentials_enable_service": False,  # gets rid of password saver popup
            "profile.password_manager_enabled": False,  # gets rid of password saver popup
        },
    )

    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

    driver = webdriver.Remote(
        command_executor="http://host.docker.internal:4444/wd/hub",
        # command_executor="http://127.0.0.1:4444/wd/hub",
        options=chrome_options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    start_json_path = os.path.join(directory, "scraper_data/start.json")
    metadata_json_path = os.path.join(directory, "scraper_data/metadata.json")
    scraper_log_path = os.path.join(directory, "scraper_data/scraper_log.txt")
    html_page_path = os.path.join(directory, "scraper_data/Page.html")
    # load input file to specify where the loop should start
    with open(start_json_path, "r") as input_file:
        data = json.load(input_file)

    journal_start = data["journal_start"]
    issue_start = data["issue_start"]

    for journal in journal_list[journal_start : len(journal_list)]:

        scrape_start = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
        page_loaded = False

        while not page_loaded:
            # Retrieving journal data
            driver.get(journal)
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

        random.seed(time.time())
        issue_url_list = []
        # issue_url_df=pd.DataFrame()

        # save_current_page(html_page_path, driver)

        click = driver.find_elements(
            By.XPATH, r".//div[@class='accordion-container']//details"
        )

        print("details number: "+str(len(click)))

        # expand the decade drawers one by one
        for element in click:
            time.sleep(5)
            element.click()

        time.sleep(2)

        # captures the year elements within the decade
        decade_List = driver.find_elements(By.XPATH, r".//dd//ul//li")

        print("decades number: "+str(len(decade_List)))

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

                # Creating a tracker file
                # url_item=pd.DataFrame({'url':[issue_url],'scraped':[0],'Journal':[journal]})
                # issue_url_df=issue_url_df.concat(issue_url_df,url_item)

        # issue_url_df.to_csv("issue_url_df.csv")

        # loops through a dataframe of issue urls and captures metadata per issue
        for issue_url in issue_url_list[issue_start : len(issue_url_list)]:
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
                
                print("citations 1")

                WebDriverWait(driver, 10).until(
                    expected_conditions.element_to_be_clickable((By.ID, "bulk-cite-button"))
                ).click()

                print("citations 2")

                time.sleep(10)

                # download_metadata=driver.find_element(By.XPATH,r".//toc-view-pharos-dropdown-menu-item[@class='bibtex_bulk_export export_citations']")
                # download_metadata = driver.find_element(
                WebDriverWait(driver, 10).until(
                    expected_conditions.element_to_be_clickable(
                        (
                            By.XPATH,
                            r"//*[@id='bulk-citation-dropdown']/mfe-bulk-cite-pharos-dropdown-menu-item[5]",
                        )
                    )
                ).click()

                print("citations 3")

                # print("metadata size:" + str(download_metadata.size))

                # driver.implicitly_wait(5)

                # ActionChains(driver).move_to_element(download_metadata).perform()

                # driver.implicitly_wait(10)
                # # WebDriverWait(driver,30).until(expected_conditions.element_to_be_clickable((By.XPATH,r"//*[@id='bulk-citation-dropdown']/toc-view-pharos-dropdown-menu-item[5]"))).click()
                # driver.execute_script("arguments[0].click();", download_metadata)
                print("citations 4")
            except Exception as e:
                print(e)
                input()

            old_name = os.path.join(directory, "scraper_data/citations.txt")
            new_name = os.path.join(directory, "scraper_data/" + issue_url.split("/")[-1] + ".txt")

            # Wait for download to complete
            count = 0
            while not os.path.isfile(old_name) and count <= 10:
                time.sleep(2)
                count += 1

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
                convert = bibtexparser.load(bibtex_file)

            with open(metadata_json_path, "r") as input_json_file:
                metadata = json.load(input_json_file)

            for entry in convert.entries:
                metadata.append(entry)

            with open(metadata_json_path, "w") as output_json_file:
                json.dump(metadata, output_json_file, indent=4, sort_keys=True)

            os.remove(new_name)

            # Update tracker file to pin new start location
            if len(issue_url_list) == issue_start + 1:
                issue_start = 0
            else:
                issue_start = issue_start + 1
            data["issue_start"] = issue_start
            with open(start_json_path, "w") as input_file:
                json.dump(data, input_file)

        scrape_end = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")

        # Append log file
        with open(scraper_log_path, "a+") as log:
            log.write("\n")
            log.write("\nJournal: " + journal)
            log.write("\nNumber of Issues scraped: " + str(len(issue_url_list)))
            log.write("\nRotated IP: " + rotated)
            log.write("\nStart time: " + scrape_start)
            log.write("\nEnd time: " + scrape_end)

        # Update tracker file to pin new start location
        journal_start = journal_start + 1
        data["journal_start"] = journal_start
        with open(start_json_path, "w") as input_file:
            json.dump(data, input_file)

    # display.stop()

# def get_downloaded_files(driver):
#     if not driver.current_url.startswith("chrome://downloads"):
#         driver.get("chrome://downloads/")

#     return driver.execute_script( \
#         "return downloads.Manager.get().items_   "
#         "  .filter(e => e.state === 'COMPLETE')  "
#         "  .map(e => e.filePath || e.file_path); " )

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

def fetch_new_titles():
    url = "https://www.jstor.org/kbart/collections/all-archive-titles?contentType=journals"

    with urlopen(url) as response:
        body = response.read()

    character_set = response.headers.get_content_charset()
    new_data = body.decode(character_set)
    with open("data.txt", encoding="utf-8", mode="w") as file:
        file.write(new_data)

    df = pd.read_csv("data.txt", sep="\t")
    os.remove("data.txt")
    return df


def clean_data():

    full_title_list_history = fetch_new_titles()

    title_url = full_title_list_history[["publication_title", "title_url"]]

    return title_url

