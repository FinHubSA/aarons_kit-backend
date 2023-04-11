from rest_framework import serializers
from django.db import models

from api.models import Journal, Issue, Article, Author, Account


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
            "url",
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
    journalName = serializers.CharField(source="issue.journal.journalName")
    journalUrl = serializers.CharField(source="issue.journal.url")
    issue = IssueSerializer(read_only=True, many=False)

    class Meta:
        model = Article
        fields = (
            "articleID",
            "journalName",
            "journalUrl",
            "issue",
            "articleJstorID",
            "title",
            "abstract",
            "bucketURL",
            "authors",
            "account",
            "issue",
        )


class AccountSerializer(serializers.ModelSerializer):
    scraped = serializers.IntegerField()

    class Meta:
        model = Account
        fields = (
            "accountID",
            "algorandAddress",
            "scraped",
            "donationsReceived",
            "donationsPaid",
        )
