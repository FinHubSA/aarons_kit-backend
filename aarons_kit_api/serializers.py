from rest_framework import serializers
from aarons_kit_api.models import Categories, SubCategories, Journals, JournalCategories, JournalSubCategories,Publishers,Issues,Articles,Authors,ArticleAuthors


class CategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Categories
        fields = ('CategoryID',
                  'Category',
                  )


class SubCategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = SubCategories
        fields = ('SubCategoryID',
                  'SubCategory',
                  )


class JournalsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Journals
        fields = ('JournalID',
                  'JournalName',
                  )

class JournalCategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = JournalCategories
        fields = ('TransactionID',
                  'Timestamp',
                  'InstrumentTypeID',
                  'Receiver',
                  'Sender'
                  )

class JournalSubCategoriesSerializer(serializers.ModelSerializer):

    class Meta:
        model = JournalSubCategories
        fields = ('JournalID',
                  'SubCategoryID',
                  )

class PublishersSerializer(serializers.ModelSerializer):

    class Meta:
        model = Publishers
        fields = ('PublisherID',
                  'PublisherName',
                  )

class IssuesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Issues
        fields = ('IssueID',
                  'IssueName',
                  'Year',
                  'Volume',
                  'Number',
                  'JournalID',
                  'PublisherID',
                  )

class ArticlesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Articles
        fields = ('ArticleID',
                  'Title',
                  'DOI',
                  'IssueID',
                  'Abstract',
                  'References',
                  'Url',
                  'Scraped',
                  )

class AuthorsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Authors
        fields = ('AuthorID',
                  'Name',
                  'Surname',
                  )

class ArticleAuthorsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ArticleAuthors
        fields = ('AuthorID',
                  'ArticleID',
                  )
