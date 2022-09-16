# Create your views here.
from rest_framework.response import Response
from rest_framework.decorators import api_view

from api.models import Journal, Issue, Article, Author
from api.serializers import JournalSerializer, ArticleSerializer

ONLY_JSTOR_ID = "onlyJstorID"

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

        # Pagination?
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
    author = Author.objects.filter(authorName__trigram_similar=author_name).first()

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
