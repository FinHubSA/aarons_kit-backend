# Create your views here.
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import Journal, Article, Author
from api.serializers import AuthorSerializer, JournalSerializer, ArticleSerializer

ONLY_JSTOR_ID = "onlyJstorID"
SCRAPING = "scraping"

##### articles #####
@api_view(["GET"])
def get_articles(request):
    try:
        title = request.query_params.get("title")
        author_name = request.query_params.get("authorName")
        journal_name = request.query_params.get("journalName")
        only_jstor_id = request.query_params.get(ONLY_JSTOR_ID) == "1"
        scraping = request.query_params.get(SCRAPING) == "1"

        if request.method == "GET":
            if title:
                return get_articles_by_title(title, only_jstor_id)
            elif author_name:
                return get_articles_by_author(author_name, only_jstor_id, scraping)
            elif journal_name:
                return get_articles_from_journal(journal_name, only_jstor_id, scraping)

            articles = Article.objects.all()[:50]

            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_articles_by_title(title, only_jstor_id):
    articles = (
        Article.objects.annotate(
            similarity=TrigramSimilarity("title", title),
        )
        .filter(similarity__gt=0.1)
        .order_by("-similarity")[:10]
    )

    if only_jstor_id:
        return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
    else:
        article_serializer = ArticleSerializer(articles, many=True)
        return Response(article_serializer.data, status.HTTP_200_OK)


def get_articles_by_author(author_name, only_jstor_id, scraping):
    try:
        author = Author.objects.get(authorName=author_name)
    except Author.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if author:
        articles = author.article_set.all()

        if scraping:
            articles = articles.filter(bucketURL=None)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)


def get_articles_from_journal(journal_name, only_jstor_id, scraping):
    try:
        journal = Journal.objects.get(journalName=journal_name)
    except Journal.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if journal:
        articles = Article.objects.filter(
            issue__journal__journalName=journal.journalName
        )

        if scraping:
            articles = articles.filter(bucketURL=None)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)


##### authors #####
@api_view(["GET"])
def get_authors(request):
    try:
        author_name = request.query_params.get("authorName")

        if request.method == "GET":
            if author_name:
                return get_authors_by_name(author_name)

            authors = Author.objects.all()[:50]

            authors_serializer = AuthorSerializer(authors, many=True)
            return Response(authors_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_authors_by_name(author_name):
    authors = (
        Author.objects.annotate(
            similarity=TrigramSimilarity("authorName", author_name),
        )
        .filter(similarity__gt=0.1)
        .order_by("-similarity")[:10]
    )

    if authors:
        authors_serializer = AuthorSerializer(authors, many=True)
        return Response(authors_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### journals #####
@api_view(["GET"])
def get_journals(request):
    try:
        journal_name = request.query_params.get("journalName")

        if request.method == "GET":
            if journal_name:
                return get_journals_by_name(journal_name)

            journals = Journal.objects.all()[:50]

            journals_serializer = JournalSerializer(journals, many=True)
            return Response(journals_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_journals_by_name(journal_name):
    journals = (
        Journal.objects.annotate(
            similarity=TrigramSimilarity("journalName", journal_name),
        )
        .filter(similarity__gt=0.1)
        .order_by("-similarity")[:10]
    )

    if journals:
        journals_serializer = JournalSerializer(journals, many=True)
        return Response(journals_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)
