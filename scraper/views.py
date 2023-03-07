# Create your views here.
import json
from django.conf import settings

from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
from django.db import connection
import requests
import time

from .scraper import (
    scrape_journal,
    remote_driver_setup,
    get_journals_to_scrape,
    update_journal_data,
    print_masterlist_state,
)

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
    parent = client.queue_path(
        settings.PROJECT_NAME, settings.QUEUE_REGION, queue=settings.QUEUE_ID
    )

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


def authorize(headers):
    print("** headers ** ", headers)

    if not "Authorization" in headers:
        print("Not Authorized")
        return False, Response(
            {"message": "Not Authorized"}, status=status.HTTP_401_UNAUTHORIZED
        )

    if not headers["Authorization"].startswith("Bearer "):
        print("Wrong Authorization")
        return False, Response(
            {"message": "Wrong Authorization"}, status=status.HTTP_401_UNAUTHORIZED
        )

    # get the bearer token
    token = headers["Authorization"][7:]
    print("** token " + token)

    response = requests.get(
        "https://oauth2.googleapis.com/tokeninfo?id_token=" + token
    ).json()

    print("** response **", response)

    # {
    #     "aud": "https://api-service-mrz6aygprq-oa.a.run.app/scraper/run",
    #     "azp": "100386201458136714087",
    #     "email": "scraper-service@aarons-kit-360209.iam.gserviceaccount.com",
    #     "email_verified": "true",
    #     "exp": "1663914000",
    #     "iat": "1663910400",
    #     "iss": "https://accounts.google.com",
    #     "sub": "100386201458136714087",
    #     "alg": "RS256",
    #     "kid": "209c057d3bdd8c08f2d5739788632673f7c6240f",
    #     "typ": "JWT"
    # }

    if not "exp" in response:
        print("Authorization Failed ")
        return False, Response(
            {"message": "Authorization Failed"}, status=status.HTTP_401_UNAUTHORIZED
        )

    expiry = int(response["exp"])
    current_time = int(time.time())

    print("** times ** ", str(expiry) + " - " + str(current_time))

    if expiry < current_time:
        print("Authorization Expired")
        return False, Response(
            {"message": "Authorization Expired"}, status=status.HTTP_401_UNAUTHORIZED
        )

    return True, Response({"message": "Authorized"}, status=status.HTTP_200_OK)


@api_view(["POST"])
def scrape_metadata_task(request):

    headers = request.headers

    authorized, response = authorize(headers)

    if not authorized:
        return response

    db_name = connection.settings_dict["NAME"]
    print("starting scrapping for db: " + db_name)

    driver = remote_driver_setup(600)

    update_journal_data()

    print_masterlist_state()

    journal = get_journals_to_scrape(False)

    if journal is None:
        return Response(
            {"message": "Found no journals to scrape"}, status=status.HTTP_200_OK
        )

    # number of scraped issues currently
    scraped_issues = journal.numberOfIssuesScraped

    scrape_journal(driver, journal, 25)

    # quit driver
    driver.quit()

    journal = Journal.objects.get(journalID=journal.journalID)

    # number of scraped newly scraped issues
    new_scraped_issues = journal.numberOfIssuesScraped - scraped_issues

    print(
        "scraped "
        + str(new_scraped_issues)
        + " issues for the journal '"
        + journal.journalName
        + "'"
    )

    return Response(
        {
            "message": "scraped "
            + str(new_scraped_issues)
            + " issues for the journal '"
            + journal.journalName
            + "'"
        },
        status=status.HTTP_200_OK,
    )
