# Generated by Django 4.0.4 on 2022-08-29 15:00

from django.db import migrations
from django.contrib.postgres.operations import TrigramExtension


class Migration(migrations.Migration):

    dependencies = [
        ("aarons_kit", "0001_createsuperuser"),
    ]

    operations = [TrigramExtension()]