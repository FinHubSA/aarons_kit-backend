from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
import requests
import json
from django.conf import settings

from api.models import (
    Journal,
    Article,
    Issue,
)
from api.views import ONLY_JSTOR_ID, SCRAPED, update_article_account

client = Client()


class TestArticle(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_articles(self):
        response = client.get(reverse("get_articles"))

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # title
    def test_get_articles_by_title(self):
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get(
            "%s?title=%s" % (reverse("get_articles"), title)
        ).data[0]

        self.assertEqual(response["title"], title)

    def test_get_article_jstor_ids_by_title(self):
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get(
            "%s?title=%s&%s=1"
            % (reverse("get_articles"), title, ONLY_JSTOR_ID),
        ).data[0]

        article = Article.objects.select_related("issue").get(title=title)

        self.assertEqual(response["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.get("articleID"), None)

    # author
    def test_get_articles_by_author(self):
        author_name = "B. R. Laurence"

        response = client.get(
            "%s?authorName=%s" % (reverse("get_articles"), author_name)
        ).data[0]

        article = Article.objects.get(title="The Larval Inhabitants of Cow Pats")

        self.assertEqual(response["articleID"], article.articleID)

    def test_get_article_jstor_ids_by_author(self):

        author_name = "B. R. Laurence"

        response = client.get(
            "%s?authorName=%s&%s=1"
            % (reverse("get_articles"), author_name, ONLY_JSTOR_ID)
        ).data[0]

        article = Article.objects.get(title="The Larval Inhabitants of Cow Pats")

        self.assertEqual(response["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.get("articleID"), None)

    def test_get_articles_by_author_to_scrape(self):
        author_name = "J. B. S. Haldane"

        response = client.get(
            "%s?authorName=%s&%s=0"
            % (reverse("get_articles"), author_name, SCRAPED)
        ).data

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].get("articleID"), 2)

    # journal
    def test_get_articles_from_journal(self):
        journal_name = "Journal of Animal Ecology"
        journal_id = 2

        response = client.get(
            "%s?journalName=%s" % (reverse("get_articles"), journal_name)
        ).data

        articles = Article.objects.filter(
            issue__journal__journalName=journal_name
        )

        self.assertGreaterEqual(len(response), len(articles))

        # test get by ID
        response = client.get(
            "%s?journalID=%s" % (reverse("get_articles"), journal_id)
        ).data

        articles = Article.objects.filter(
            issue__journal__journalID = journal_id
        )

        self.assertEqual(len(response), len(articles))

    # issue
    def test_get_articles_by_issue(self):
        issue_id = 2

        response = client.get(
            "%s?issueID=%s" % (reverse("get_articles"), issue_id)
        ).data

        articles = Article.objects.filter(issue__issueID = 2)

        self.assertEqual(len(response), len(articles))


    def test_get_articles_page_size(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&page=1&page_size=1" % (reverse("get_articles"), journal_name)
        ).data

        self.assertEqual(len(response), 1)


    def test_pdf_upload(self):
        
        algorand_address = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ'

        files = {
            'file': open('fixtures/test_article.pdf', 'rb')
        }

        data = {
            'articleJstorID' : '1', #"10.2307/41985663"
            'algorandAddress': algorand_address
        }

        # response = requests.post("https://api-service-mrz6aygprq-oa.a.run.app/api/articles/pdf", files=files, data=data, verify=False)
        response = client.post(reverse("store_pdf"), files=files, data=data, verify=False)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        update_article_account(1, algorand_address)

        account = Article.objects.get(articleJstorID=1).account
        
        self.assertEqual(account.algorandAddress, algorand_address)

    def test_update_article_bucket_url(self):
        
        data = {
            'articleJstorID' : '1',
            'filename': 'test_article.pdf',
            'bucket': settings.GS_CLEAN_BUCKET_NAME
        }

        # response = requests.post("https://api-service-mrz6aygprq-oa.a.run.app/api/articles/pdf", files=files, data=data, verify=False)
        response = client.post(reverse("update_article_bucket_url"), data=data, verify=False)

        print(response.content)

        article = Article.objects.get(articleJstorID="1")
        self.assertEqual(
            article.bucketURL,
            "https://storage.googleapis.com/clean-aarons-kit-360209/test_article.pdf",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_article_jstor_ids_from_journal(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&%s=1"
            % (reverse("get_articles"), journal_name, ONLY_JSTOR_ID)
        ).data

        articles = Article.objects.filter(
            issue__journal__journalName=journal_name
        )

        self.assertGreaterEqual(len(response), len(articles))
        self.assertEqual(response[0].get("articleID"), None)

    def test_get_articles_by_journal_to_scrape(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&%s=0"
            % (reverse("get_articles"), journal_name, SCRAPED)
        ).data

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].get("articleID"), 2)


class TestAuthor(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_authors_by_name(self):
        incorrect_author_name = "B. R."

        response = client.get(
            "%s?authorName=%s" % (reverse("get_authors"), incorrect_author_name)
        ).data

        self.assertEqual(response[0]["authorName"], "B. R. Laurence")
        self.assertEqual(response[1]["authorName"], "R. Capildeo")
        self.assertEqual(response[2]["authorName"], "J. B. S. Haldane")


class TestJournal(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_journals(self):
        response = client.get(reverse("get_journals"))

        journals = Journal.objects.all()

        self.assertEqual(len(response.data), len(journals))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    

    def test_get_journals_by_name(self):

        incorrect_journal_name = "Animimal Ecology"
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s" % (reverse("get_journals"), incorrect_journal_name)
        ).data

        journal = Journal.objects.get(journalName=journal_name)

        self.assertEqual(response[0]["journalID"], journal.journalID)

class TestIssue(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_issues(self):
        response = client.get(reverse("get_issues"))

        issues = Issue.objects.all()

        self.assertEqual(len(response.data), len(issues))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_issues_by_journal(self):
        journal_name = "Journal of Animal Ecology"
        journal = Journal.objects.get(journalName=journal_name)

        response = client.get(
            "%s?journalID=%s" % (reverse("get_issues"), journal.journalID)
        ).data

        print("response size",len(response))
        issues = Issue.objects.filter(
            journal__journalID=journal.journalID
        )

        self.assertEqual(len(response), len(issues))


