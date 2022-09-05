import json
import bibtexparser
import pandas as pd

from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

from scraper.scraper import scrape_journal, save_issue_articles, remote_driver_setup, update_journal_data, get_journals_to_scrape

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
        self.assertEqual(journal.lastVolume, "9")
        self.assertEqual(journal.lastVolumeIssue, "4")
        self.assertEqual(journal.lastVolumeScrapped, "")
        self.assertEqual(journal.lastVolumeIssueScrapped, "")

        # update to different values
        journal.lastVolume='1'
        journal.lastVolumeIssue='1'
        
        journal.save()
        
        journal = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )

        self.assertEqual(journal.journalName, "14th Century English Mystics Newsletter")
        self.assertEqual(journal.lastVolume, "1")
        self.assertEqual(journal.lastVolumeIssue, "1")
        self.assertEqual(journal.lastVolumeScrapped, "")
        self.assertEqual(journal.lastVolumeIssueScrapped, "")

        # update again from the jstor file
        update_journal_data()

        journal = Journal.objects.get(
            journalName="14th Century English Mystics Newsletter"
        )

        self.assertEqual(journal.journalName, "14th Century English Mystics Newsletter")
        self.assertEqual(journal.lastVolume, "9")
        self.assertEqual(journal.lastVolumeIssue, "4")
        self.assertEqual(journal.lastVolumeScrapped, "")
        self.assertEqual(journal.lastVolumeIssueScrapped, "")

    def test_citation_save(self):

        with open("fixtures/citations.txt") as bibtex_file:
            citations_data = bibtexparser.load(bibtex_file)

        update_journal_data()

        journal = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        save_issue_articles(pd.DataFrame(citations_data.entries), journal, "https://www.jstor.org/stable/i26400176", 58)

        # Test journal
        journal = Journal.objects.get(
            journalName="Academy of Management Learning & Education"
        )

        self.assertEqual(journal.issn, "1537260X")
        self.assertEqual(journal.altISSN, "19449585")
        self.assertEqual(journal.lastVolumeScrapped, "15")
        self.assertEqual(journal.lastVolumeIssueScrapped, "4")
        self.assertEqual(journal.numberOfIssues, 58)
        self.assertEqual(journal.numberOfIssuesScrapped, 1)

        # Test issue
        issue = Issue.objects.get(url="https://www.jstor.org/stable/i26400176")
        self.assertEqual(issue.year, 2016)

        # Test articles
        article = Article.objects.get(url="http://www.jstor.org/stable/26400179")
        self.assertEqual(article.title, "Publish and Politics: An Examination of Business School Faculty Salaries in Ontario")
        authors = article.authors.all()
        self.assertEqual(len(authors), 2)
        self.assertEqual(authors[0].authorName, "YING HONG")

    def test_metadata_scrapper(self):

        driver = remote_driver_setup()

        update_journal_data()
        
        journal = Journal.objects.get(
            journalName="Technical Writing Review"
        )

        self.assertEqual(journal.issn, "26377772")
        self.assertEqual(journal.lastVolumeScrapped, "")
        self.assertEqual(journal.lastVolumeIssueScrapped, "")
        self.assertEqual(journal.numberOfIssues, 0)
        self.assertEqual(journal.numberOfIssuesScrapped, 0)

        scrape_journal(driver, journal)

        driver.quit()

        # Test journal
        journal = Journal.objects.get(
            journalName="Technical Writing Review"
        )

        self.assertEqual(journal.issn, "26377772")
        self.assertEqual(journal.lastVolumeScrapped, "4")
        self.assertEqual(journal.lastVolumeIssueScrapped, "2")
        self.assertEqual(journal.numberOfIssues, 2)
        self.assertEqual(journal.numberOfIssuesScrapped, 2)