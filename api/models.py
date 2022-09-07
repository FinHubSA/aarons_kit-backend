from django.db import models
from datetime import datetime

class Journal(models.Model):
    journalID = models.AutoField(primary_key=True)
    issn = models.CharField(max_length=50, unique=True)
    altISSN = models.CharField(max_length=50, unique=True, null=True)
    url = models.CharField(max_length=1000, unique=True, null=True)
    journalName = models.CharField(max_length=500, unique=True)
    numberOfIssues = models.IntegerField(default=0)
    numberOfIssuesScraped = models.IntegerField(default=0)
    lastIssueDate = models.DateField(default=datetime.min)
    lastIssueDateScraped = models.DateField(default=datetime.min)


class Issue(models.Model):
    issueID = models.AutoField(primary_key=True)
    issueJstorID = models.CharField(max_length=50, unique=True, null=True)
    url = models.CharField(max_length=1000, unique=True, null=True)
    year = models.IntegerField()
    volume = models.IntegerField()
    number = models.IntegerField()
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name="issues"
    )


class Author(models.Model):
    authorID = models.AutoField(primary_key=True)
    authorName = models.CharField(max_length=200, unique=True)


class Article(models.Model):
    articleID = models.AutoField(primary_key=True)
    title = models.CharField(max_length=500)
    abstract = models.TextField()
    bucketURL = models.CharField(max_length=1000, unique=True, null=True)
    articleURL = models.CharField(max_length=500, unique=True, null=True)
    articleJstorID = models.CharField(max_length=50, unique=True)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="articles")
    authors = models.ManyToManyField(Author)
