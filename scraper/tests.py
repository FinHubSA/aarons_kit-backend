import json
import bibtexparser
import pandas as pd

from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

from scraper.scraper import (
    scrape_journal,
    save_issue_articles,
    remote_driver_setup,
    update_journal_data,
    get_journals_to_scrape,
)

from api.models import (
    Journal,
    Issue,
    Article,
    Author,
)

client = Client()
# Create your tests here.
class TestScraper(TestCase):
    def test_update_journal_data(self):

        update_journal_data()

        journal = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )

        self.assertEqual(journal.journalName, "14th Century English Mystics Newsletter")
        self.assertEqual(str(journal.lastIssueDate), "1983-12-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "0001-01-01")

        # update to different values
        journal.lastVolume = "1"
        journal.lastVolumeIssue = "1"

        journal.save()

        journal = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )

        self.assertEqual(journal.journalName, "14th Century English Mystics Newsletter")
        self.assertEqual(str(journal.lastIssueDate), "1983-12-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "0001-01-01")

        # update again from the jstor file
        update_journal_data()

        journal = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )

        self.assertEqual(journal.journalName, "14th Century English Mystics Newsletter")
        self.assertEqual(str(journal.lastIssueDate), "1983-12-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "0001-01-01")

    def test_citation_save(self):

        with open("fixtures/citations.txt") as bibtex_file:
            citations_data = bibtexparser.load(bibtex_file)

        update_journal_data()

        journal = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        save_issue_articles(
            pd.DataFrame(citations_data.entries),
            journal,
            "https://www.jstor.org/stable/i26400176",
            58,
        )

        # Test journal
        journal = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        self.assertEqual(journal.issn, "1537260X")
        self.assertEqual(journal.altISSN, "19449585")
        self.assertEqual(str(journal.lastIssueDate), "2016-12-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "2016-01-01")
        self.assertEqual(journal.numberOfIssues, 58)
        self.assertEqual(journal.numberOfIssuesScraped, 1)

        # Test issue
        issue = Issue.objects.get(url="https://www.jstor.org/stable/i26400176")
        self.assertEqual(issue.year, 2016)

        # Test articles
        article = Article.objects.get(articleJstorID="10.2307/26400179")
        self.assertEqual(article.articleJstorID, "10.2307/26400179")
        self.assertEqual(
            article.title,
            "Publish and Politics: An Examination of Business School Faculty Salaries in Ontario",
        )
        authors = article.authors.all()
        self.assertEqual(len(authors), 2)
        self.assertEqual(authors[0].authorName, "YING HONG")

    def test_metadata_scrapper(self):

        driver = remote_driver_setup()

        update_journal_data()

        journal = Journal.objects.get(journalName="Technical Writing Review")

        self.assertEqual(journal.issn, "26377772")
        self.assertEqual(str(journal.lastIssueDate), "1957-06-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "0001-01-01")
        self.assertEqual(journal.numberOfIssues, 0)
        self.assertEqual(journal.numberOfIssuesScraped, 0)

        scrape_journal(driver, journal)

        driver.quit()

        # Test journal
        journal = Journal.objects.get(journalName="Technical Writing Review")

        self.assertEqual(journal.issn, "26377772")
        self.assertEqual(str(journal.lastIssueDate), "1957-06-01")
        self.assertEqual(str(journal.lastIssueDateScraped), "1957-06-01")
        self.assertEqual(journal.numberOfIssues, 2)
        self.assertEqual(journal.numberOfIssuesScraped, 2)
    
    def test_scraper_validation(self):
        extra={"HTTP_Authorization":"Bearer z7ku30VAX6Y6rajq2VMC4dHhG7HlBnb0zFd9A"}

        response = client.post(reverse("scrape_metadata_task"))

        self.assertEqual(response.data["message"], "Not Authorized")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = client.post(reverse("scrape_metadata_task"), {}, **extra)

        self.assertEqual(response.data["message"], "Authorization Failed")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)



