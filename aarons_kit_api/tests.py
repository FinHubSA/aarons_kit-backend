import json
import bibtexparser
import pandas as pd

from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

from aarons_kit_api.masterlist_scraper import scrape_journal
from aarons_kit_api.masterlist_scraper import save_citations_data
from aarons_kit_api.masterlist_scraper import remote_driver_setup

from aarons_kit_api.models import (
    Journal,
    Issue,
    Article,
    Author,
)

client = Client()

class TestArticle(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_available_articles(self):
        response = client.get(reverse("get_available_articles"))

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_article_by_title(self):
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get("%s?title=%s" % (reverse("get_article_by_title"), title))

        article = Article.objects.select_related("issue").get(title=title)

        self.assertEqual(response.data["articleID"], article.articleID)
        self.assertEqual(response.data["issue"], article.issue.issueID)
        self.assertEqual(response.data["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.data["title"], article.title)
        self.assertEqual(response.data["abstract"], article.abstract)
        self.assertEqual(response.data["url"], article.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestMetadata(TestCase):
    def test_upload_metadata(self):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        with open("fixtures/test_metadata_small.json") as f:
            metadata = json.load(f)

        response = client.post(
            reverse("store_metadata"),
            data={"metadata": json.dumps(metadata)},
            headers=headers,
        )

        # Test journal
        journal_response = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )
        self.assertEqual(journal_response.issn, "07375840")
        self.assertEqual(journal_response.altISSN, "")

        # Test issue
        issue_response = Issue.objects.get(issueJstorID="1")
        self.assertEqual(issue_response.journal, journal_response)
        self.assertEqual(issue_response.volume, 9)
        self.assertEqual(issue_response.number, 4)
        self.assertEqual(issue_response.year, 1983)

        # Test articles
        article_response_1 = Article.objects.get(articleJstorID="1")
        self.assertEqual(article_response_1.issue, issue_response)
        self.assertEqual(article_response_1.title, "Front Matter")
        self.assertEqual(article_response_1.abstract, "")
        self.assertEqual(article_response_1.url, "")
        article_response_2 = Article.objects.get(articleJstorID="2")
        self.assertEqual(article_response_2.issue, issue_response)
        self.assertEqual(article_response_2.title, "TO OUR READERS")
        self.assertEqual(article_response_2.abstract, "")
        self.assertEqual(article_response_2.url, "")

        # Test authors
        author_1 = Author.objects.get(authorName="blah")
        author_2 = Author.objects.get(authorName="blah 2")

        self.assertEqual(len(author_1.article_set.all()), 2)
        self.assertEqual(len(author_2.article_set.all()), 1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

class TestScraper(TestCase):
    def test_citation_save(self):

        with open("fixtures/citations.txt") as bibtex_file:
            citations_data = bibtexparser.load(bibtex_file)

        save_citations_data(pd.DataFrame(citations_data.entries), "https://www.jstor.org/journal/acadmanaleareduc", "https://www.jstor.org/stable/i26400176")

        # Test journal
        journal_response = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        self.assertEqual(journal_response.issn, "1537260X")
        self.assertEqual(journal_response.altISSN, "")

        # Test issue
        issue_response = Issue.objects.get(url="https://www.jstor.org/stable/i26400176")
        self.assertEqual(issue_response.year, 2016)

        # Repeat the test and check that it doesn't duplicate or give errors
        save_citations_data(pd.DataFrame(citations_data.entries), "https://www.jstor.org/journal/acadmanaleareduc", "https://www.jstor.org/stable/i26400176")

        # Test journal
        journal_response = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        self.assertEqual(journal_response.issn, "1537260X")

    def test_metadata_scrapper(self):

        driver = remote_driver_setup()

        # https://www.jstor.org/journal/techwritrevi - 2
        # 
        scrape_journal(driver, "https://www.jstor.org/journal/techwritrevi")

        driver.quit()

        # Test journal
        journal_response = Journal.objects.get(
            journalName="Technical Writing Review"
        )

        self.assertEqual(journal_response.issn, "26377772")

