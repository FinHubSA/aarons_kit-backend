# Create your views here.
import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import (
    Journal,
    Issue,
    Article,
    Author,
)
from api.serializers import (
    JournalSerializer,
    IssueSerializer,
    ArticleSerializer,
    AuthorSerializer,
)

##### articles #####


@api_view(["POST"])
def store_metadata(request):
    articles_metadata = json.loads(request.data["metadata"])

    for metadata in articles_metadata:
        # store journal
        journal_result = Journal.objects.get_or_create(
            issn=metadata["issn"],
            defaults={
                "journalName": metadata["journal"],
                "altISSN": metadata.get("altISSN", ""),
            },
        )
        # store issue
        issue_result = Issue.objects.get_or_create(
            issueJstorID=metadata["issueJstorID"],
            defaults={
                "journal": journal_result[0],
                "issueJstorID": metadata["issueJstorID"],
                "volume": metadata["volume"],
                "number": metadata["number"],
                "year": metadata["year"],
            },
        )
        # store article
        article_result = Article.objects.get_or_create(
            articleJstorID=metadata["articleJstorID"],
            defaults={
                "issue": issue_result[0],
                "articleJstorID": metadata["articleJstorID"],
                "title": metadata["title"],
                "abstract": metadata.get("abstract", ""),
                "url": metadata.get("url", ""),
            },
        )
        # store author
        if metadata.get("authors"):
            names = metadata.get("authors").split("and")
            for name in names:
                author_result = Author.objects.get_or_create(authorName=name.strip())
                article_result[0].authors.add(author_result[0])

    return Response(
        {"message": "Metadata successfully stored"}, status=status.HTTP_200_OK
    )


@api_view(["GET"])
def get_available_articles(request):
    articles = Article.objects.all()

    # Pagination?
    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def get_article_by_title(request):
    title = request.GET.get("title")

    article = Article.objects.get(title=title)
    # article.get_related_data()

    if request.method == "GET":
        article_serializer = ArticleSerializer(article, many=False)
        return Response(article_serializer.data)


@api_view(["GET"])
def get_articles_by_year_range(request):
    articles = Article.objects.all()

    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def check_article_by_title(request):
    articles = Article.objects.all()

    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def get_articles_by_author(request):
    articles = Article.objects.all()

    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def get_articles_from_journal(request):
    articles = Article.objects.all()

    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def check_article_by_author(request):
    articles = Article.objects.all()

    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


##### journals #####


@api_view(["GET"])
def get_available_journals(request):
    journals = Journal.objects.all()

    if request.method == "GET":
        journals_serializer = ArticleSerializer(journals, many=True)
        return Response(journals_serializer.data)


@api_view(["GET"])
def check_article_by_journal_name(request):
    journals = Journal.objects.all()

    if request.method == "GET":
        journals_serializer = ArticleSerializer(journals, many=True)
        return Response(journals_serializer.data)
