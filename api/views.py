# Create your views here.
from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings

from api.models import Journal, Article, Author
from api.serializers import AuthorSerializer, JournalSerializer, ArticleSerializer
# from storages.backends.gcloud import GoogleCloudStorage
# storage = GoogleCloudStorage()
from google.cloud import storage

ONLY_JSTOR_ID = "onlyJstorID"
SCRAPING = "scraping"

@api_view(["POST"])
def store_pdf(request):
    article_id = request.data["articleJstorID"]

    print("** pdf upload article id "+article_id)

    if not Article.objects.filter(articleJstorID=article_id).exists():
        return Response(
            {"message": "Article not found "}, status=status.HTTP_404_NOT_FOUND
        )

    file = request.FILES["file"]
    filename = file.name

    if not filename.lower().endswith(('.pdf')):
        return Response(
            {"message": "Article file is not a PDF "}, status=status.HTTP_403_FORBIDDEN
        )

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(settings.GS_UNSCANNED_BUCKET_NAME)
        blob = bucket.blob(filename)

        blob.upload_from_file(file)
        unscanned_bucket_url = "https://storage.googleapis.com/"+settings.GS_UNSCANNED_BUCKET_NAME+"/"+filename
        clean_bucket_url = "https://storage.googleapis.com/"+settings.GS_CLEAN_BUCKET_NAME+"/"+filename
    except Exception as e:
        print("Failed to upload!", e)
        return Response(
            {"message": "Failed to upload "+filename}, status=status.HTTP_401_UNAUTHORIZED
        )
        
    article = Article.objects.get(
        articleJstorID=article_id
    )

    article.bucketURL = unscanned_bucket_url
    article.save()

    return Response(
        {"message": "Article PDF successfully stored", "bucket_url": clean_bucket_url}, status=status.HTTP_200_OK
    )

@api_view(["POST"])
def update_article_bucket_url(request):
    article_id = request.data["articleJstorID"]
    filename = request.data["filename"]
    bucket = request.data["bucket"]

    bucket_url = "https://storage.googleapis.com/"+bucket+"/"+filename

    if not Article.objects.filter(articleJstorID=article_id).exists():
        return Response(
            {"message": "Article not found "}, status=status.HTTP_404_NOT_FOUND
        )

    article = Article.objects.get(
        articleJstorID=article_id
    )

    article.bucketURL = bucket_url
    article.save()

    return Response(
        {"message": "Article bucket url successfully updated", "bucket_url": bucket_url}, status=status.HTTP_200_OK
    )

##### articles #####
@api_view(["GET"])
def get_articles(request):
    try:
        title = request.query_params.get("title")
        author_name = request.query_params.get("authorName")
        journal_name = request.query_params.get("journalName")
        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")

        only_jstor_id = request.query_params.get(ONLY_JSTOR_ID) == "1"
        scraping = request.query_params.get(SCRAPING) == "1"
        
        if not page:
            page = 1

        if not page_size:
            page_size = 50

        if request.method == "GET":
            if title:
                return get_articles_by_title(title, only_jstor_id, page, page_size)
            elif author_name:
                return get_articles_by_author(author_name, only_jstor_id, scraping, page, page_size)
            elif journal_name:
                return get_articles_from_journal(journal_name, only_jstor_id, scraping, page, page_size)

            articles = Article.objects.all()

            paginator = Paginator(articles, page_size)
            articles = paginator.get_page(page)

            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_articles_by_title(title, only_jstor_id, page, page_size):
    articles = (
        Article.objects.annotate(
            similarity=TrigramSimilarity("title", title),
        )
        .filter(similarity__gt=0.1)
        .order_by("-similarity")
    )

    paginator = Paginator(articles, page_size) 
    articles = paginator.get_page(page)

    if only_jstor_id:
        return Response(articles.object_list.values("articleJstorID"), status.HTTP_200_OK)
    else:
        article_serializer = ArticleSerializer(articles, many=True)
        return Response(article_serializer.data, status.HTTP_200_OK)


def get_articles_by_author(author_name, only_jstor_id, scraping, page, page_size):
    try:
        author = Author.objects.get(authorName=author_name)
    except Author.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if author:
        articles = author.article_set.all()

        if scraping:
            articles = articles.filter(bucketURL=None)

        paginator = Paginator(articles, page_size)
        articles = paginator.get_page(page)

        if only_jstor_id:
            return Response(articles.object_list.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)


def get_articles_from_journal(journal_name, only_jstor_id, scraping, page, page_size):
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

        paginator = Paginator(articles, page_size)
        articles = paginator.get_page(page)

        if only_jstor_id:
            return Response(articles.object_list.values("articleJstorID"), status.HTTP_200_OK)
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
