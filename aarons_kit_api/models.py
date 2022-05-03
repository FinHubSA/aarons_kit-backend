from django.db import models

class Categories(models.Model):
    CategoryID = models.IntegerField(blank=False, primary_key=True)
    Category = models.CharField(max_length=100)

class SubCategories(models.Model):
    SubCategoryID = models.IntegerField(blank=False, primary_key=True)
    SubCategory = models.CharField(max_length=100)

class Journals(models.Model):
    JournalID = models.IntegerField(blank=False, primary_key=True)
    JournalName = models.CharField(max_length=100)
    
class JournalCategories(models.Model):
    JournalID = models.ForeignKey(Journals, on_delete=models.CASCADE, related_name='categories')
    CategoryID = models.ForeignKey(Categories, on_delete=models.CASCADE, related_name='journals')
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['JournalID', 'CategoryID'], name='JournalCategory')
        ]

class JournalSubCategories(models.Model):
    JournalID = models.ForeignKey(Journals, on_delete=models.CASCADE, related_name='sub_categories')
    SubCategoryID = models.ForeignKey(SubCategories, on_delete=models.CASCADE, related_name='journals')
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['JournalID', 'SubCategoryID'], name='JournalSubCategory')
        ]

class Publishers(models.Model):
    PublisherID = models.IntegerField(blank=False, primary_key=True)
    PublisherName = models.CharField(max_length=100)

class Issues(models.Model):
    IssueID = models.IntegerField(blank=False, primary_key=True)
    IssueName = models.CharField(max_length=100)
    Year = models.DateField()
    Volume = models.IntegerField(default=0)
    Number = models.IntegerField(default=0)
    JournalID = models.ForeignKey(Journals, on_delete=models.CASCADE)
    PublisherID = models.ForeignKey(Publishers, on_delete=models.CASCADE)

class Articles(models.Model):
    ArticleID = models.IntegerField(blank=False, primary_key=True)
    Title = models.CharField(max_length=500)
    DOI = models.CharField(max_length=200)
    IssueID = models.ForeignKey(Issues, on_delete=models.CASCADE, related_name='articles')
    Abstract = models.CharField(max_length=10000)
    References = models.CharField(max_length=10000)
    Url = models.CharField(max_length=1000)
    Scraped = models.BooleanField(default=False)

class Authors(models.Model):
    AuthorID = models.IntegerField(blank=False, primary_key=True)
    Name = models.CharField(max_length=500)
    Surname = models.CharField(max_length=500)
    
class ArticleAuthors(models.Model):
    AuthorID = models.ForeignKey(Authors, on_delete=models.CASCADE, related_name='articles')
    ArticleID = models.ForeignKey(Articles, on_delete=models.CASCADE, related_name='authors')

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['AuthorID', 'ArticleID'], name='ArticleAuthor')
        ]
