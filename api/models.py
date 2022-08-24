from django.db import models


class Journal(models.Model):
    journalID = models.AutoField(primary_key=True)
    issn = models.CharField(max_length=50)
    altISSN = models.CharField(max_length=50)
    journalName = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Issue(models.Model):
    issueID = models.AutoField(primary_key=True)
    issueJstorID = models.CharField(max_length=50)
    year = models.IntegerField()
    volume = models.IntegerField()
    number = models.IntegerField()
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name="issues"
    )

    def __str__(self):
        return self.name


class Author(models.Model):
    authorID = models.AutoField(primary_key=True)
    authorName = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Article(models.Model):
    articleID = models.AutoField(primary_key=True)
    title = models.CharField(max_length=500)
    abstract = models.TextField()  # nullable
    url = models.CharField(max_length=1000)
    articleJstorID = models.CharField(max_length=50)
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="articles")
    authors = models.ManyToManyField(Author)

    def __str__(self):
        return self.name
