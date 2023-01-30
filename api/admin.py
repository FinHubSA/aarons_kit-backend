from django.contrib import admin

from .models import Journal, Issue, Author, Article

admin.site.register([Journal, Issue, Author, Article])
