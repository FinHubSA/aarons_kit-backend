from django.urls import include, path, re_path
from aarons_kit_api import views

urlpatterns = [
    re_path(
        r"^api/articles/metadata$",
        views.store_articles_metadata,
        name="store_articles_metadata",
    ),
    re_path(
        r"^api/articles$", views.get_available_articles, name="get_available_articles"
    ),
    re_path(
        r"^api/articles/title$", views.get_article_by_title, name="get_article_by_title"
    ),
    re_path(
        r"^api/articles/year$",
        views.get_articles_by_year_range,
        name="get_articles_by_year_range",
    ),
    re_path(
        r"^api/articles/check$",
        views.check_article_by_title,
        name="check_article_by_title",
    ),
    re_path(
        r"^api/articles/author$",
        views.get_articles_by_author,
        name="get_articles_by_author",
    ),
    re_path(
        r"^api/articles/journal$",
        views.get_articles_from_journal,
        name="get_articles_from_journal",
    ),
    re_path(
        r"^api/author/check$",
        views.check_article_by_author,
        name="check_article_by_author",
    ),
    re_path(
        r"^api/categories$",
        views.get_available_categories,
        name="get_available_categories",
    ),
    re_path(r"^api/category$", views.get_category, name="get_category"),
    re_path(
        r"^api/journals/titles$",
        views.get_available_journals,
        name="get_available_journals",
    ),
    re_path(
        r"^api/journals/check$",
        views.check_article_by_journal_name,
        name="check_article_by_journal_name",
    ),
]
