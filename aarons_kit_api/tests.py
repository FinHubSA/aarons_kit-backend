import json
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from aarons_kit_api.models import Categories, SubCategories, Journals, JournalSubCategories,Publishers,Issues,Articles,Authors,ArticleAuthors
from .serializers import CategoriesSerializer, SubCategoriesSerializer, JournalsSerializer, JournalSubCategoriesSerializer,PublishersSerializer,IssuesSerializer,ArticlesSerializer,AuthorsSerializer,ArticleAuthorsSerializer

client = Client()

class CategoriesTestCase(TestCase):

    def setUp(self):
        call_command('loaddata', 'fixtures/model_fixtures', verbosity=0)
        call_command('loaddata', 'fixtures/test_fixtures', verbosity=0)

    def test_get_available_categories(self):
        response = client.get(reverse('get_available_categories'))

        categories = Categories.objects.all()

        self.assertEqual(len(response.data), len(categories))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_available_articles(self):
        response = client.get(reverse('get_available_articles'))

        articles = Articles.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_article_by_title(self):
        response = client.get('%s?title=%s' % (reverse('get_article_by_title'), 'The Larval Inhabitants of Cow Pats'))

        article = Articles.objects.get(Title='The Larval Inhabitants of Cow Pats')
        article.get_related_data()

        self.assertEqual(response.data['ArticleID'], article.ArticleID)
        self.assertEqual(response.data['IssueName'], article.IssueName)
        self.assertEqual(response.data['JournalName'], article.JournalName)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    