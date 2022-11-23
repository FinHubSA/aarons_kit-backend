# Generated by Django 4.0.4 on 2022-11-22 19:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0007_article_article_title_gin_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('accountID', models.AutoField(primary_key=True, serialize=False)),
                ('algorandAddress', models.CharField(max_length=100, unique=True)),
                ('donationsReceived', models.IntegerField(default=0)),
                ('donationsPaid', models.IntegerField(default=0)),
            ],
        ),
        migrations.AlterModelOptions(
            name='article',
            options={'ordering': ['articleID']},
        ),
        migrations.AlterModelOptions(
            name='issue',
            options={'ordering': ['-year', 'number', 'volume']},
        ),
        migrations.AddField(
            model_name='article',
            name='account',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articles', to='api.account'),
        ),
    ]
