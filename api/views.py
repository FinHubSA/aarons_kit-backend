# Create your views here.
from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator
from django.db.models import Q, Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings
from urllib.request import urlopen

import traceback
import base64

from api.models import Journal, Article, Author, Issue, Account
from api.serializers import AuthorSerializer, JournalSerializer, ArticleSerializer, IssueSerializer, AccountSerializer
# from storages.backends.gcloud import GoogleCloudStorage
# storage = GoogleCloudStorage()
from google.cloud import storage

ONLY_JSTOR_ID = "onlyJstorID"
SCRAPED = "scraped"

@api_view(["POST"])
def store_pdf(request):
    article_id = request.data.get("articleJstorID","")
    algorand_address = request.data.get("algorandAddress", "")

    print("** article ID ", article_id)
    print("** algo address ", algorand_address)

    if not Article.objects.filter(articleJstorID=article_id).exists():
        print("article not found")
        return Response(
            {"message": "Article not found "}, status=status.HTTP_404_NOT_FOUND
        )

    article = Article.objects.get(
        articleJstorID=article_id
    )

    if article.bucketURL:
        return Response(
            {"message": "Article already scraped "}, status=status.HTTP_403_FORBIDDEN
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
        # unscanned_bucket_url = "https://storage.googleapis.com/"+settings.GS_UNSCANNED_BUCKET_NAME+"/"+filename
        clean_bucket_url = "https://storage.googleapis.com/"+settings.GS_CLEAN_BUCKET_NAME+"/"+filename
    except Exception as e:
        print("Failed to upload!", e)
        return Response(
            {"message": "Failed to upload "+filename}, status=status.HTTP_401_UNAUTHORIZED
        )
    
    update_article_account(article_id, algorand_address)

    return Response(
        {"message": "Article PDF successfully stored", "bucket_url": clean_bucket_url}, status=status.HTTP_200_OK
    )

def update_article_account(article_id, algorand_address):
    if algorand_address:
        article = Article.objects.get(
            articleJstorID=article_id
        )

        account, account_created = Account.objects.get_or_create(
            algorandAddress=algorand_address,
            defaults={
                "algorandAddress": algorand_address
            },
        )

        # article.bucketURL = unscanned_bucket_url
        article.account = account
        article.save()


@api_view(["POST"])
def update_article_bucket_url(request):
    article_id = request.data["articleJstorID"]
    filename = request.data["filename"]
    bucket = request.data["bucket"]

    bucket_url = "https://storage.googleapis.com/"+bucket+"/"+filename

    code = urlopen(bucket_url).code

    if code != 200:
        return Response(
            {"message": "Article pdf not found "}, status=status.HTTP_404_NOT_FOUND
        )

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
def get_articles_from_page(articles, page, page_size):

    paginator = Paginator(articles, page_size)
    
    if (page > paginator.num_pages):
        return Article.objects.none()

    articles = paginator.get_page(page)

    return articles.object_list

@api_view(["GET"])
def get_articles(request):
    try:
        title = request.query_params.get("title")
        author_name = request.query_params.get("authorName")
        journal_name = request.query_params.get("journalName")
        journal_id = request.query_params.get("journalID")
        issue_id = request.query_params.get("issueID")
        exact = request.query_params.get("exact")

        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")

        only_jstor_id = request.query_params.get(ONLY_JSTOR_ID) == "1"
        scraped = request.query_params.get('scraped')

        if not page:
            page = 1
        else:
            page = int(page)

        if scraped:
            scraped = int(scraped)
        else:
            scraped = -1

        if not page_size:
            page_size = 50
        else:
            page_size = int(page_size)

        if not exact:
            exact = 0.1
        else:
            exact = float(exact)
        
        if request.method == "GET":
            if title:
                return get_articles_by_title(title, only_jstor_id, page, page_size, exact)
            elif author_name:
                return get_articles_by_author(author_name, only_jstor_id, scraped, page, page_size, exact)
            elif journal_name or journal_id:
                return get_articles_by_journal(journal_name, journal_id, only_jstor_id, scraped, page, page_size, exact)
            elif issue_id:
                return get_articles_by_issue(issue_id, only_jstor_id, scraped, page, page_size)
            else: 
                return get_all_articles(scraped)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_all_articles(scraped):

    if scraped == 1:
        articles = Article.objects.filter(bucketURL__isnull=False)
    elif scraped == 0:
        articles = Article.objects.filter(bucketURL__isnull=True)
    else:
        articles = Article.objects.all()
    
    articles_serializer = ArticleSerializer(articles, many=True)
    return Response(articles_serializer.data, status.HTTP_200_OK)

def get_articles_by_title(title, only_jstor_id, page, page_size, exact):
    articles = (
        Article.objects.annotate(
            similarity=TrigramSimilarity("title", title),
        )
        .filter(similarity__gte=exact)
        .order_by("-similarity")
    )

    articles = get_articles_from_page(articles, page, page_size)

    if only_jstor_id:
        return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
    else:
        article_serializer = ArticleSerializer(articles, many=True)
        return Response(article_serializer.data, status.HTTP_200_OK)

def get_articles_by_author(author_name, only_jstor_id, scraped, page, page_size, exact):
    try:
        authors = (
            Author.objects.annotate(
                similarity=TrigramSimilarity("authorName", author_name),
            )
            .filter(similarity__gte=exact)
            .order_by("-similarity")
        )
    except Author.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    print("** get by authors")

    if authors:
        articles = Article.objects.filter(authors__in=authors) 

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)


def get_articles_by_journal(journal_name, journal_id, only_jstor_id, scraped, page, page_size, exact):
    try:
        if (journal_name):
            journals = (
                Journal.objects.annotate(
                    similarity=TrigramSimilarity("journalName", journal_name),
                )
                .filter(similarity__gte=exact)
                .order_by("-similarity")
            )
        else:
            journals = Journal.objects.filter(journalID=journal_id)
    except Journal.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if journals:
        articles = Article.objects.filter(
            issue__journal__in=journals
        )

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)

def get_articles_by_issue(issue_id, only_jstor_id, scraped, page, page_size):
    try:
        issue = Issue.objects.get(issueID=issue_id)
    except Journal.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if issue:
        articles = Article.objects.filter(
            issue__issueID=issue.issueID
        )

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)

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
        .filter(similarity__gte=0.1)
        .order_by("-similarity")[:10]
    )

    if authors:
        authors_serializer = AuthorSerializer(authors, many=True)
        return Response(authors_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)

##### issues #####
@api_view(["GET"])
def get_issues(request):
    try:
        journal_id = request.query_params.get("journalID")

        print("getting issues ", journal_id)
        if request.method == "GET":
            if journal_id:
                return get_issues_by_journal(journal_id)

            issues = Issue.objects.all()[:50]

            issues_serializer = IssueSerializer(issues, many=True)
            return Response(issues_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

def get_issues_by_journal(journal_id):
    
    issues = Issue.objects.filter(
        journal__journalID=journal_id
    )

    if issues:
        issues_serializer = IssueSerializer(issues, many=True)
        return Response(issues_serializer.data, status.HTTP_200_OK)

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
        .filter(similarity__gte=0.1)
        .order_by("-similarity")[:10]
    )

    if journals:
        journals_serializer = JournalSerializer(journals, many=True)
        return Response(journals_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### accounts #####
@api_view(["GET"])
def get_accounts(request):

    accounts = Account.objects.annotate(scraped=Count('articles', filter=Q(articles__bucketURL__isnull=False))).filter(scraped__gte=0)

    try:
        account_serializer = AccountSerializer(accounts, many=True)
        return Response(account_serializer.data, status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["GET"])
def get_amount_for_distribution(request):
    algod_client = settings.ALGOD_CLIENT
    app_address = settings.SMART_CONTRACT_ADDRESS

    smart_contract_info = algod_client.account_info(app_address)

    print(smart_contract_info)

    smart_contract_info['amount_for_distribution'] = smart_contract_info['amount'] - smart_contract_info['min-balance']
    
    return Response(smart_contract_info, status.HTTP_200_OK)

@api_view(["GET"])
def get_amount_distributed_todate(request):
    algod_client = settings.ALGOD_CLIENT
    app_id = settings.SMART_CONTRACT_ID

    app = algod_client.application_info(app_id)
    global_state = app['params']['global-state'] if "global-state" in app["params"] else []

    app_info = decode_state(global_state)

    print(f"global_state for app_id {app_id}: ", app_info)

    return Response(app_info, status.HTTP_200_OK)

def str_or_hex(v):
    decoded: str = ""
    try:
        decoded = v.decode("utf-8")
    except Exception:
        decoded = v.hex()

    return decoded


def decode_state(state, raw=False):

    decoded_state = {}

    for sv in state:

        raw_key = base64.b64decode(sv["key"])

        key = raw_key if raw else str_or_hex(raw_key)
        val = None

        action = (
            sv["value"]["action"] if "action" in sv["value"] else sv["value"]["type"]
        )

        if action == 1:
            raw_val = base64.b64decode(sv["value"]["bytes"])
            val = raw_val if raw else str_or_hex(raw_val)
        elif action == 2:
            val = sv["value"]["uint"]
        elif action == 3:
            val = None

        decoded_state[key] = val

    return decoded_state

