import json
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from aarons_kit_api.models import Categories, SubCategories, Journals, JournalCategories, JournalSubCategories,Publishers,Issues,Articles,Authors,ArticleAuthors
from .serializers import CategoriesSerializer, SubCategoriesSerializer, JournalsSerializer, JournalCategoriesSerializer, JournalSubCategoriesSerializer,PublishersSerializer,IssuesSerializer,ArticlesSerializer,AuthorsSerializer,ArticleAuthorsSerializer

client = Client()

class CategoriesTestCase(TestCase):

    def setUp(self):
        call_command('loaddata', 'fixtures/model_fixtures', verbosity=0)
        #call_command('loaddata', 'fixtures/test_fixtures', verbosity=0)

    def test_get_available_categories(self):
        response = client.get(reverse('get_available_categories'))

        categories = Categories.objects.all()

        self.assertEqual(len(response.data), len(categories))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

