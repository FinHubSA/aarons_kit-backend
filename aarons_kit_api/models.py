from django.db import models


class Categories(models.Model):
    CategoryID = models.IntegerField(blank=False, primary_key=True)
    Category = models.CharField(max_length=100)


class SubCategories(models.Model):
    SubCategoryID = models.IntegerField(blank=False, primary_key=True)
    CategoryID = models.ForeignKey(
        Categories, default=1, on_delete=models.CASCADE, related_name="sub_categories"
    )
    SubCategory = models.CharField(max_length=100)


class Journals(models.Model):
    JournalID = models.IntegerField(blank=False, primary_key=True)
    JournalName = models.CharField(max_length=100)


class JournalSubCategories(models.Model):
    JournalID = models.ForeignKey(
        Journals, on_delete=models.CASCADE, related_name="sub_categories"
    )
    SubCategoryID = models.ForeignKey(
        SubCategories, on_delete=models.CASCADE, related_name="journals"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["JournalID", "SubCategoryID"], name="JournalSubCategory"
            )
        ]


class Publishers(models.Model):
    PublisherID = models.IntegerField(blank=False, primary_key=True)
    PublisherName = models.CharField(max_length=100)


class Issues(models.Model):
    IssueID = models.IntegerField(blank=False, primary_key=True)
    IssueName = models.CharField(max_length=100)
    Year = models.IntegerField(default=0)
    Volume = models.IntegerField(default=0)
    Number = models.IntegerField(default=0)
    JournalID = models.ForeignKey(Journals, on_delete=models.CASCADE)
    PublisherID = models.ForeignKey(Publishers, on_delete=models.CASCADE)

    # Related Data
    PublisherName = None
    JournalName = None

    def get_related_data(self):
        self.PublisherName = self.PublisherID.PublisherName
        self.JournalName = self.JournalID.JournalName


class Articles(models.Model):
    ArticleID = models.IntegerField(blank=False, primary_key=True)
    Title = models.CharField(max_length=500)
    DOI = models.CharField(max_length=200)
    IssueID = models.ForeignKey(
        Issues, on_delete=models.CASCADE, related_name="articles"
    )
    Abstract = models.CharField(max_length=10000)
    References = models.CharField(max_length=10000)
    URL = models.CharField(max_length=1000)
    Scraped = models.BooleanField(default=False)

    # Related Data
    IssueName = None
    IssueYear = None
    IssueVolume = None
    IssueNumber = None

    JournalID = None
    JournalName = None

    PublisherID = None
    PublisherName = None

    Authors = []

    def get_related_data(self):
        self.IssueID.get_related_data()

        self.IssueName = self.IssueID.IssueName
        self.IssueYear = self.IssueID.Year
        self.IssueVolume = self.IssueID.Volume
        self.IssueNumber = self.IssueID.Number

        self.JournalID = self.IssueID.JournalID.JournalID
        self.JournalName = self.IssueID.JournalName

        self.PublisherID = self.IssueID.PublisherID.PublisherID
        self.PublisherName = self.IssueID.PublisherName

        authors = self.authors.all()

        for author in authors:
            self.Authors.append(
                {
                    "id": author.AuthorID.AuthorID,
                    "name": author.AuthorID.Name,
                    "surname": author.AuthorID.Surname,
                }
            )


class Authors(models.Model):
    AuthorID = models.IntegerField(blank=False, primary_key=True)
    Name = models.CharField(max_length=500)
    Surname = models.CharField(max_length=500)


class ArticleAuthors(models.Model):
    AuthorID = models.ForeignKey(
        Authors, on_delete=models.CASCADE, related_name="articles"
    )
    ArticleID = models.ForeignKey(
        Articles, on_delete=models.CASCADE, related_name="authors"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["AuthorID", "ArticleID"], name="ArticleAuthor"
            )
        ]
