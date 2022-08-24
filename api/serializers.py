from rest_framework import serializers

from api.models import (
    Journal,
    Issue,
    Article,
    Author,
)


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = (
            "journalID",
            "issn",
            "altISSN",
            "journalName",
        )


class IssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Issue
        fields = (
            "issueID",
            "journal",
            "issueJstorID",
            "year",
            "volume",
            "number",
        )


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = (
            "authorID",
            "authorName",
        )


class ArticleSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(read_only=True, many=True)

    class Meta:
        model = Article
        fields = (
            "articleID",
            "issue",
            "articleJstorID",
            "title",
            "abstract",
            "url",
            "authors",
        )
