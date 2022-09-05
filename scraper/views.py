# Create your views here.
import json
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2

from .scraper import scrape_journal, remote_driver_setup, get_journals_to_scrape, update_journal_data

from api.models import (
    Journal,
    Issue,
    Article,
    Author,
)

from api.serializers import (
    JournalSerializer,
    IssueSerializer,
    ArticleSerializer,
    AuthorSerializer,
)

client = tasks_v2.CloudTasksClient()

@api_view(["GET"])
def enqueue_scraper_task(request):
    print("enquieing task")

    # construct the queue
    parent = client.queue_path(settings.PROJECT_NAME, settings.QUEUE_REGION, queue=settings.QUEUE_ID)

    # construct the request body
    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": "https://api-service-mrz6aygprq-oa.a.run.app/scraper/run",
            "oidc_token": {
                "service_account_email": "scraper-service@aarons-kit-360209.iam.gserviceaccount.com",
                "audience": "https://api-service-mrz6aygprq-oa.a.run.app/scraper/run",
            },
        }
    }

    # use the client to build and send the task
    response = client.create_task(parent=parent, task=task)
    
    print("Created task {}".format(response.name))

    return Response(
        {"message": "Created task {}".format(response.name)}, status=status.HTTP_200_OK
    )

@api_view(["POST"])
def scrape_metadata_task(request):

    print("starting scrapping")
    driver = remote_driver_setup()

    update_journal_data()

    journal = get_journals_to_scrape(False)
    
    if journal is None:
        return Response(
            {"message": "Found no journals to scrape"}, status=status.HTTP_200_OK
        )
    
    # number of scrapped issues currently
    scrapped_issues = journal.numberOfIssuesScrapped

    scrape_journal(driver, journal)

    journal = Journal.objects.get(journalID=journal.journalID)

    # number of scrapped newly scrapped issues
    new_scrapped_issues = journal.numberOfIssuesScrapped - scrapped_issues

    print("scrapped "+str(new_scrapped_issues)+" issues for the journal '"+journal.journalName+"'")

    return Response(
        {"message": "scrapped "+str(new_scrapped_issues)+" issues for the journal '"+journal.journalName+"'"}, status=status.HTTP_200_OK
    )
