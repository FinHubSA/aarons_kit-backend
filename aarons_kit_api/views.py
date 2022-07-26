# Create your views here.
from django.shortcuts import render
from django.db.models import Avg, Count, Min, Sum
from django.http.response import JsonResponse
from django.core import serializers
from django.db.models import F, Func, Value, CharField
from django.core import serializers

from rest_framework import status
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.decorators import api_view
import json

from aarons_kit_api.models import Categories, SubCategories, Journals, JournalSubCategories,Publishers,Issues,Articles,Authors,ArticleAuthors
from aarons_kit_api.serializers import CategoriesSerializer, SubCategoriesSerializer, JournalsSerializer, JournalSubCategoriesSerializer,PublishersSerializer,IssuesSerializer,ArticlesSerializer,AuthorsSerializer,ArticleAuthorsSerializer

##### articles #####

@api_view(['POST'])
def store_articles_metadata(request):
    articles_metadata = json.loads(request.data["metadata"])
    
    for metadata in articles_metadata:
        print(metadata)

    return Response({'message':'Metadata successfully stored'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def get_available_articles(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

@api_view(['GET'])
def get_article_by_title(request):
    title = request.GET.get('title')

    article = Articles.objects.get(Title=title)
    article.get_related_data()

    if request.method == 'GET':
        article_serializer = ArticlesSerializer(article, many=False)
        return Response(article_serializer.data)

@api_view(['GET'])
def get_articles_by_year_range(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

@api_view(['GET'])
def check_article_by_title(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

@api_view(['GET'])
def get_articles_by_author(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

@api_view(['GET'])
def get_articles_from_journal(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

@api_view(['GET'])
def check_article_by_author(request):
    articles = Articles.objects.all()

    if request.method == 'GET':
        articles_serializer = ArticlesSerializer(articles, many=True)
        return Response(articles_serializer.data)

##### categories #####

@api_view(['GET'])
def get_available_categories(request):
    categories = Categories.objects.all()

    if request.method == 'GET':
        categories_serializer = CategoriesSerializer(categories, many=True)
        return Response(categories_serializer.data)

@api_view(['GET'])
def get_category(request):
    categories = Categories.objects.all()

    if request.method == 'GET':
        categories_serializer = CategoriesSerializer(categories, many=True)
        return Response(categories_serializer.data)

##### journals #####

@api_view(['GET'])
def get_available_journals(request):
    journals = Journals.objects.all()

    if request.method == 'GET':
        journals_serializer = ArticlesSerializer(journals, many=True)
        return Response(journals_serializer.data)

@api_view(['GET'])
def check_article_by_journal_name(request):
    journals = Journals.objects.all()

    if request.method == 'GET':
        journals_serializer = ArticlesSerializer(journals, many=True)
        return Response(journals_serializer.data)