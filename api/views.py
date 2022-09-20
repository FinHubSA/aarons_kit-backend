# Create your views here.
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import Journal, Issue, Article, Author
from api.serializers import AuthorSerializer, JournalSerializer, ArticleSerializer
from storages.backends.gcloud import GoogleCloudStorage
storage = GoogleCloudStorage()

ONLY_JSTOR_ID = "onlyJstorID"

@api_view(["POST"])
def store_pdf(request):
    article_id = request.data["articleJstorID"]

    file = request.data["file"]
    filename = file.name
    
    try:
        target_path = '/articles/' + filename
        path = storage.save(target_path, file)
        bucket_url = storage.url(path)
    except Exception as e:
        print("Failed to upload!", e)
        return Response(
            {"message": "Failed to upload "+filename}, status=status.HTTP_401_UNAUTHORIZED
        )

    if Article.objects.filter(articleJstorID=article_id).exists():
        
        article = Article.objects.get(
            articleJstorID=article_id
        )

        article.bucketURL = bucket_url
        article.save()

    return Response(
        {"message": "Article PDF successfully stored at: "+bucket_url}, status=status.HTTP_200_OK
    )

##### articles #####
@api_view(["GET"])
def get_articles(request):
    title = request.query_params.get("title")
    author_name = request.query_params.get("authorName")
    journal_name = request.query_params.get("journalName")
    only_jstor_id = request.query_params.get(ONLY_JSTOR_ID) == "1"

    if request.method == "GET":
        if title:
            return get_articles_by_title(title, only_jstor_id)
        elif author_name:
            return get_articles_by_author(author_name, only_jstor_id)
        elif journal_name:
            return get_articles_from_journal(journal_name, only_jstor_id)

        articles = Article.objects.all()[:50]

        articles_serializer = ArticleSerializer(articles, many=True)
        return Response(articles_serializer.data)


def get_articles_by_title(title, only_jstor_id):
    articles = Article.objects.filter(title__trigram_similar=title)[:10]

    if only_jstor_id:
        return Response(articles.values("articleJstorID"))
    else:
        articles = Article.objects.filter(title__trigram_similar=title)[:10]
        article_serializer = ArticleSerializer(articles, many=True)
        return Response(article_serializer.data)


def get_articles_by_author(author_name, only_jstor_id):
    author = Author.objects.get(authorName=author_name)

    if author:
        articles = author.article_set.all()

        if only_jstor_id:
            return Response(articles.values("articleJstorID"))
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data)


def get_articles_from_journal(journal_name, only_jstor_id):
    journal = Journal.objects.filter(journalName__trigram_similar=journal_name).first()

    if journal:
        articles = Article.objects.filter(
            issue__journal__journalName=journal.journalName
        )

        if only_jstor_id:
            return Response(articles.values("articleJstorID"))
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data)


##### authors #####
@api_view(["GET"])
def get_authors_by_name(request):
    author_name = request.query_params.get("authorName")

    authors = (
        Author.objects.annotate(
            similarity=TrigramSimilarity("authorName", author_name),
        )
        .filter(similarity__gt=0.1)
        .order_by("-similarity")[:10]
    )

    if authors:
        authors_serializer = AuthorSerializer(authors, many=True)
        return Response(authors_serializer.data)


##### journals #####
@api_view(["GET"])
def get_journals(request):
    journal_name = request.query_params.get("journalName")

    if request.method == "GET":
        if journal_name:
            return get_journals_by_name(journal_name)

        journals = Journal.objects.all()[:50]

        journals_serializer = JournalSerializer(journals, many=True)
        return Response(journals_serializer.data)


def get_journals_by_name(journal_name):
    journal = Journal.objects.filter(journalName__trigram_similar=journal_name)[:10]

    journal_serializer = JournalSerializer(journal, many=True)
    return Response(journal_serializer.data)
