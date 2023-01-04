from time import sleep
import environ

from algosdk.error import IndexerHTTPError
from algosdk.v2client.algod import AlgodClient
from algosdk.v2client.indexer import IndexerClient
from django.core.management import call_command
from django.test import TestCase, Client
from django.urls import reverse

from rest_framework import status
import json
from django.conf import settings

from api.models import Journal, Article, Issue, Account
from api.views import (
    decode_state,
    get_accounts_scraped,
    ONLY_JSTOR_ID,
    SCRAPED,
    update_article_account,
)

client = Client()
env = environ.Env(DEBUG=(bool, True))


class TestArticle(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_articles(self):
        response = client.get(reverse("get_articles"))

        articles = Article.objects.all()

        self.assertEqual(len(response.data), len(articles))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # title
    def test_get_articles_by_title(self):
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get("%s?title=%s" % (reverse("get_articles"), title)).data[0]

        self.assertEqual(response["title"], title)

    def test_get_article_jstor_ids_by_title(self):
        title = "The Larval Inhabitants of Cow Pats"

        response = client.get(
            "%s?title=%s&%s=1" % (reverse("get_articles"), title, ONLY_JSTOR_ID),
        ).data[0]

        article = Article.objects.select_related("issue").get(title=title)

        self.assertEqual(response["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.get("articleID"), None)

    # author
    def test_get_articles_by_author(self):
        author_name = "B. R. Laurence"

        response = client.get(
            "%s?authorName=%s" % (reverse("get_articles"), author_name)
        ).data[0]

        article = Article.objects.get(title="The Larval Inhabitants of Cow Pats")

        self.assertEqual(response["articleID"], article.articleID)

    def test_get_article_jstor_ids_by_author(self):

        exact_author_name = "B. R. Laurence"
        author_name = "Laurence"

        response = client.get(
            "%s?authorName=%s&%s=1&exact=0.9"
            % (reverse("get_articles"), author_name, ONLY_JSTOR_ID)
        ).data

        self.assertEqual(response["message"], "no articles found")

        response = client.get(
            "%s?exact=1&authorName=%s&%s=1"
            % (reverse("get_articles"), exact_author_name, ONLY_JSTOR_ID)
        ).data[0]

        article = Article.objects.get(title="The Larval Inhabitants of Cow Pats")

        self.assertEqual(response["articleJstorID"], article.articleJstorID)
        self.assertEqual(response.get("articleID"), None)

    def test_get_articles_by_author_to_scrape(self):
        author_name = "J. B. S. Haldane"

        response = client.get(
            "%s?authorName=%s&%s=0" % (reverse("get_articles"), author_name, SCRAPED)
        ).data

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].get("articleID"), 2)

    # journal
    def test_get_articles_from_journal(self):
        journal_name = "Journal of Animal Ecology"
        journal_id = 2

        response = client.get(
            "%s?journalName=%s" % (reverse("get_articles"), journal_name)
        ).data

        articles = Article.objects.filter(issue__journal__journalName=journal_name)

        self.assertGreaterEqual(len(response), len(articles))

        # test get by ID
        response = client.get(
            "%s?journalID=%s" % (reverse("get_articles"), journal_id)
        ).data

        articles = Article.objects.filter(issue__journal__journalID=journal_id)

        self.assertEqual(len(response), len(articles))

    # issue
    def test_get_articles_by_issue(self):
        issue_id = 2

        response = client.get(
            "%s?issueID=%s" % (reverse("get_articles"), issue_id)
        ).data

        articles = Article.objects.filter(issue__issueID=2)

        self.assertEqual(len(response), len(articles))

    def test_get_articles_page_size(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&page=1&page_size=1"
            % (reverse("get_articles"), journal_name)
        ).data

        self.assertEqual(len(response), 1)

    def test_pdf_upload(self):

        algorand_address = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAY5HFKQ"

        files = {"file": open("fixtures/test_article.pdf", "rb")}

        data = {
            "articleJstorID": "1",  # "10.2307/41985663"
            "algorandAddress": algorand_address,
        }

        # response = requests.post("https://api-service-mrz6aygprq-oa.a.run.app/api/articles/pdf", files=files, data=data, verify=False)
        response = client.post(
            reverse("store_pdf"), files=files, data=data, verify=False
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        update_article_account(1, algorand_address)

        account = Article.objects.get(articleJstorID=1).account

        self.assertEqual(account.algorandAddress, algorand_address)

    def test_update_article_bucket_url(self):

        data = {
            "articleJstorID": "1",
            "filename": "test_article.pdf",
            "bucket": settings.GS_CLEAN_BUCKET_NAME,
        }

        # response = requests.post("https://api-service-mrz6aygprq-oa.a.run.app/api/articles/pdf", files=files, data=data, verify=False)
        response = client.post(
            reverse("update_article_bucket_url"), data=data, verify=False
        )

        print(response.content)

        article = Article.objects.get(articleJstorID="1")
        self.assertEqual(
            article.bucketURL,
            "https://storage.googleapis.com/clean-aarons-kit-360209/test_article.pdf",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_article_jstor_ids_from_journal(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&%s=1"
            % (reverse("get_articles"), journal_name, ONLY_JSTOR_ID)
        ).data

        articles = Article.objects.filter(issue__journal__journalName=journal_name)

        self.assertGreaterEqual(len(response), len(articles))
        self.assertEqual(response[0].get("articleID"), None)

    def test_get_articles_by_journal_to_scrape(self):
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s&%s=0" % (reverse("get_articles"), journal_name, SCRAPED)
        ).data

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0].get("articleID"), 2)


class TestAuthor(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_authors_by_name(self):
        incorrect_author_name = "B. R."

        response = client.get(
            "%s?authorName=%s" % (reverse("get_authors"), incorrect_author_name)
        ).data

        self.assertEqual(response[0]["authorName"], "B. R. Laurence")
        self.assertEqual(response[1]["authorName"], "R. Capildeo")
        self.assertEqual(response[2]["authorName"], "J. B. S. Haldane")


class TestJournal(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_journals(self):
        response = client.get(reverse("get_journals"))

        journals = Journal.objects.all()

        self.assertEqual(len(response.data), len(journals))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_journals_by_name(self):

        incorrect_journal_name = "Animimal Ecology"
        journal_name = "Journal of Animal Ecology"

        response = client.get(
            "%s?journalName=%s" % (reverse("get_journals"), incorrect_journal_name)
        ).data

        journal = Journal.objects.get(journalName=journal_name)

        self.assertEqual(response[0]["journalID"], journal.journalID)


class TestIssue(TestCase):
    def setUp(self):
        call_command("loaddata", "fixtures/test_fixtures", verbosity=0)

    def test_get_issues(self):
        response = client.get(reverse("get_issues"))

        issues = Issue.objects.all()

        self.assertEqual(len(response.data), len(issues))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_issues_by_journal(self):
        journal_name = "Journal of Animal Ecology"
        journal = Journal.objects.get(journalName=journal_name)

        response = client.get(
            "%s?journalID=%s" % (reverse("get_issues"), journal.journalID)
        ).data

        print("response size", len(response))
        issues = Issue.objects.filter(journal__journalID=journal.journalID)

        self.assertEqual(len(response), len(issues))


class TestAccount(TestCase):
    def setUp(self):
        Journal.objects.create(journalID=1, issn="1")

        Issue.objects.create(
            issueID=1, issueJstorID=1, year="2022", volume=1, number=1, journal_id=1
        )

        Account.objects.create(
            accountID=1, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_1")
        )
        Account.objects.create(
            accountID=2, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_2")
        )
        Account.objects.create(
            accountID=3, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_3")
        )
        Account.objects.create(
            accountID=4, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_4")
        )
        Account.objects.create(
            accountID=5, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_5")
        )
        Account.objects.create(
            accountID=6, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_6")
        )
        Account.objects.create(
            accountID=7, algorandAddress=env.get_value("TEST_SCRAPER_ADDRESS_7")
        )

        Article.objects.create(
            articleID=1,
            title="1",
            abstract="1",
            issue_id=1,
            account_id=1,
            articleJstorID=1,
        )
        Article.objects.create(
            articleID=2,
            title="2",
            abstract="2",
            issue_id=1,
            account_id=2,
            articleJstorID=2,
            bucketURL="www.ex2.com",
        )
        Article.objects.create(
            articleID=3,
            title="3",
            abstract="3",
            issue_id=1,
            account_id=1,
            articleJstorID=3,
            bucketURL="www.ex3.com",
        )
        Article.objects.create(
            articleID=4,
            title="4",
            abstract="4",
            issue_id=1,
            account_id=4,
            articleJstorID=4,
            bucketURL="www.ex4.com",
        )
        Article.objects.create(
            articleID=5,
            title="5",
            abstract="5",
            issue_id=1,
            account_id=5,
            articleJstorID=5,
            bucketURL="www.ex5.com",
        )
        Article.objects.create(
            articleID=6,
            title="6",
            abstract="6",
            issue_id=1,
            account_id=6,
            articleJstorID=6,
            bucketURL="www.ex6.com",
        )
        Article.objects.create(
            articleID=7,
            title="7",
            abstract="7",
            issue_id=1,
            account_id=7,
            articleJstorID=7,
            bucketURL="www.ex7.com",
        )
        Article.objects.create(
            articleID=8,
            title="8",
            abstract="8",
            issue_id=1,
            account_id=1,
            articleJstorID=8,
            bucketURL="www.ex8.com",
        )
        Article.objects.create(
            articleID=9,
            title="9",
            abstract="9",
            issue_id=1,
            account_id=1,
            articleJstorID=9,
            bucketURL="www.ex9.com",
        )
        Article.objects.create(
            articleID=10,
            title="10",
            abstract="10",
            issue_id=1,
            account_id=2,
            articleJstorID=10,
            bucketURL="www.ex10.com",
        )

    def test_get_total_scraped(self):
        response = client.get(reverse("get_accounts")).data

        json_result = json.dumps(response)
        expected_json_result = json.dumps(
            [
                {
                    "accountID": 1,
                    "algorandAddress": "X5JACF3ZUIJCNQCNNKW7CVTQFQ3E5OAUTNL3ZS3ZR2IDL742EUWI46BEBI",
                    "scraped": 3,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
                {
                    "accountID": 2,
                    "algorandAddress": "PBUUOUHW5CATIWKUJP253JAORLERFUMIAM6MNDRDSJ4PP5IGJRZK23WQCE",
                    "scraped": 2,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
                {
                    "accountID": 4,
                    "algorandAddress": "H4AW6AP2K2JCIDOBYSWI7YVCALKVT4FSAXJOQOWVOJ6ASSH67OVPDXOOZA",
                    "scraped": 1,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
                {
                    "accountID": 5,
                    "algorandAddress": "KDNAXEHU5MCWOD5JA52TZJVO5DSGVQ72YWKAH6T6PMAD75TNVRZ6GQHIFM",
                    "scraped": 1,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
                {
                    "accountID": 6,
                    "algorandAddress": "B62EFYHSTG62DCCUMDJAZHI2N5UHL5TZH5YXS2RMMORRDHA7S7WPX4Z65A",
                    "scraped": 1,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
                {
                    "accountID": 7,
                    "algorandAddress": "5Z5BKKP2C6ECMCLRCC5VRUEGOYHKYEAPVEC2TAHKNFDWNC6CTS6XPE3SGQ",
                    "scraped": 1,
                    "donationsReceived": 0,
                    "donationsPaid": 0,
                },
            ]
        )
        self.assertEqual(sorted(json_result), sorted(expected_json_result))

    def test_get_smartcontract_info(self):

        response = client.get(reverse("get_smart_contract_info")).data

        self.assertEqual(
            response["amount_for_distribution"],
            response["amount"] - response["min-balance"],
        )

    def test_get_smartcontract_state(self):

        response = client.get(reverse("get_smart_contract_state")).data

        self.assertGreaterEqual(response["total_distributed"], 0)
        self.assertGreaterEqual(response["donations_snapshot"], 0)
        self.assertGreaterEqual(response["papers_scraped_snapshot"], 0)

    def test_distribute_donations(self):
        MAX_TRIES = 5
        SLEEP = 5

        algod_client: AlgodClient = settings.ALGOD_CLIENT
        indexer_client: IndexerClient = settings.INDEXER_CLIENT
        app_addr = settings.SMART_CONTRACT_ADDRESS

        app_acc_info_before = algod_client.account_info(app_addr)
        app_amount_before = app_acc_info_before["amount"]
        app_min_balance = app_acc_info_before["min-balance"]

        app_distributable_amount = app_amount_before - app_min_balance

        accounts = get_accounts_scraped()

        expected_payments = []

        for account in accounts:
            expected_payments.append(
                (
                    account["algorandAddress"],
                    (app_distributable_amount * account["scraped"]) // 9,
                )
            )

        response = client.get(
            "%s?distributeToken=%s"
            % (
                reverse("distribute_donations"),
                env.get_value("DISTRIBUTE_DONATIONS_TOKEN"),
            ),
        ).data

        if response is None:
            assert True
            return

        assert len(response) == 2  # 2 txns

        sleep(SLEEP)  # give indexer time to catch up

        tries = 0
        payments_verified = 0

        for txn_id in response:
            while tries < MAX_TRIES:
                tries += 1
                try:
                    txn = indexer_client.transaction(txn_id)["transaction"]
                    for inner_txn in txn["inner-txns"]:
                        assert inner_txn["sender"] == app_addr
                        assert inner_txn["tx-type"] == "pay"
                        payment_txn = inner_txn["payment-transaction"]
                        assert (
                            payment_txn["receiver"],
                            payment_txn["amount"],
                        ) in expected_payments
                        payments_verified += 1
                    break
                except IndexerHTTPError as e:
                    print(e)
                    print(
                        "Error while getting txn {} from indexer. Indexer probably has not caught up yet. Let's wait.".format(
                            txn_id
                        )
                    )
                    if tries == MAX_TRIES:
                        print("Could not retrieve txn info to run assertions with")
                        assert False
            tries = 0

        assert payments_verified == 6
