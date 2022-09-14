# Create your views here.
import json
import os

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import Journal, Issue, Article, Author
from api.serializers import JournalSerializer, ArticleSerializer

##### articles #####
@api_view(["POST"])
def store_metadata(request):
    api_key = request.query_params.get("apiKey")

    if not api_key or api_key != os.environ.get("METADATA_API_KEY"):
        return Response(
            {"message": "Forbidden"}, status=status.HTTP_403_FORBIDDEN
        )

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
                "bucketURL": metadata.get("url", None),
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
def get_all_articles(request):
    articles = Article.objects.all()[:50]

    # Pagination?
    if request.method == "GET":
        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


@api_view(["GET"])
def get_article_by_title(request):
    title = request.query_params.get("title")

    article = Article.objects.filter(title__trigram_similar=title)[:10]

    if request.method == "GET":
        article_serializer = ArticleSerializer(article, many=True)
        return Response(article_serializer.data)


@api_view(["GET"])
def get_articles_by_author(request):
    author_name = request.query_params.get("authorName")

    author = Author.objects.filter(authorName__trigram_similar=author_name).first()

    if author:
        articles = author.article_set.all()

        if request.method == "GET":
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data)


@api_view(["GET"])
def get_articles_from_journal(request):
    journal_name = request.query_params.get("journalName")

    journal = Journal.objects.filter(journalName__trigram_similar=journal_name).first()

    if journal:
        articles = Article.objects.filter(
            issue__journal__journalName=journal.journalName
        )

        if request.method == "GET":
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data)


##### journals #####
@api_view(["GET"])
def get_all_journals(request):
    journals = Journal.objects.all()[:50]

    if request.method == "GET":
        journals_serializer = JournalSerializer(journals, many=True)
        return Response(journals_serializer.data)


@api_view(["GET"])
def get_journal_by_name(request):
    journal_name = request.query_params.get("journalName")

    journal = Journal.objects.filter(journalName__trigram_similar=journal_name)[:10]

    if request.method == "GET":
        journal_serializer = JournalSerializer(journal, many=True)
        return Response(journal_serializer.data)
