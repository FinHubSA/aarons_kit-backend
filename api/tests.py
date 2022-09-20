from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status

from api.models import (
    Journal,
    Article,
)
from api.views import ONLY_JSTOR_ID

client = Client()


class TestArticle(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_articles(self):
        response = client.get(reverse("get_articles"))

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_articles_by_title(self):
        incorrect_title = "The Inhabitanst of Cat Pats"
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get(
            "%s?title=%s" % (reverse("get_articles"), incorrect_title)
        ).data[0]

        article = Article.objects.select_related("issue").get(title=title)

        self.assertEqual(response["articleID"], article.articleID)

    def test_get_article_jstor_ids_by_title(self):
        incorrect_title = "The Inhabitanst of Cat Pats"
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get(
            "%s?title=%s&%s=1"
            % (reverse("get_articles"), incorrect_title, ONLY_JSTOR_ID),
        ).data[0]

        article = Article.objects.select_related("issue").get(title=title)

        self.assertEqual(response["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.get("articleID"), None)

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

    def test_get_articles_from_journal(self):
        incorrect_journal_name = "Amimal Ecology"

        response = client.get(
            "%s?journalName=%s" % (reverse("get_articles"), incorrect_journal_name)
        )

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))

    def test_get_article_jstor_ids_from_journal(self):
        incorrect_journal_name = "Amimal Ecology"

        response = client.get(
            "%s?journalName=%s&%s=1"
            % (reverse("get_articles"), incorrect_journal_name, ONLY_JSTOR_ID)
        )

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.data[0].get("articleID"), None)


class TestAuthor(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_authors_by_name(self):
        incorrect_author_name = "B. R."

        response = client.get(
            "%s?authorName=%s" % (reverse("get_authors_by_name"), incorrect_author_name)
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
        ).data[0]

        journal = Journal.objects.get(journalName=journal_name)

        self.assertEqual(response["journalID"], journal.journalID)
