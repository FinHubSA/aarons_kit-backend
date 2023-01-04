# Create your views here.
from base64 import b64decode
from math import ceil
from time import sleep
import environ

from algosdk.abi import Method
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AtomicTransactionResponse,
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.future.transaction import ApplicationNoOpTxn
from algosdk.v2client.algod import AlgodClient
from django.contrib.postgres.search import TrigramSimilarity
from django.core.paginator import Paginator
from django.db.models import Q, Count
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from django.conf import settings
from urllib.request import urlopen

from api.models import Journal, Article, Author, Issue, Account
from api.serializers import (
    AccountSerializer,
    AuthorSerializer,
    JournalSerializer,
    ArticleSerializer,
    IssueSerializer,
)

# from storages.backends.gcloud import GoogleCloudStorage
# storage = GoogleCloudStorage()
from google.cloud import storage

ONLY_JSTOR_ID = "onlyJstorID"
SCRAPED = "scraped"

env = environ.Env(DEBUG=(bool, True))


@api_view(["POST"])
def store_pdf(request):
    article_id = request.data.get("articleJstorID", "")
    algorand_address = request.data.get("algorandAddress", "")

    print("** article ID ", article_id)
    print("** algo address ", algorand_address)

    if not Article.objects.filter(articleJstorID=article_id).exists():
        print("article not found")
        return Response(
            {"message": "Article not found "}, status=status.HTTP_400_BAD_REQUEST
        )

    article = Article.objects.get(articleJstorID=article_id)

    if article.bucketURL:
        return Response(
            {"message": "Article already scraped "}, status=status.HTTP_400_BAD_REQUEST
        )

    file = request.FILES["file"]
    filename = file.name

    if not filename.lower().endswith((".pdf")):
        return Response(
            {"message": "Article file is not a PDF "},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(settings.GS_UNSCANNED_BUCKET_NAME)
        blob = bucket.blob(filename)

        blob.upload_from_file(file)
        # unscanned_bucket_url = "https://storage.googleapis.com/"+settings.GS_UNSCANNED_BUCKET_NAME+"/"+filename
        clean_bucket_url = (
            "https://storage.googleapis.com/"
            + settings.GS_CLEAN_BUCKET_NAME
            + "/"
            + filename
        )
    except Exception as e:
        print("Failed to upload!", e)
        return Response(
            {"message": "Failed to upload " + filename},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    update_article_account(article_id, algorand_address)

    return Response(
        {"message": "Article PDF successfully stored", "bucket_url": clean_bucket_url},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
def update_article_bucket_url(request):
    article_id = request.data["articleJstorID"]
    filename = request.data["filename"]
    bucket = request.data["bucket"]

    bucket_url = "https://storage.googleapis.com/" + bucket + "/" + filename

    code = urlopen(bucket_url).code

    if code != 200:
        return Response(
            {"message": "Article pdf not found "}, status=status.HTTP_400_BAD_REQUEST
        )

    if not Article.objects.filter(articleJstorID=article_id).exists():
        return Response(
            {"message": "Article not found "}, status=status.HTTP_400_BAD_REQUEST
        )

    article = Article.objects.get(articleJstorID=article_id)

    article.bucketURL = bucket_url
    article.save()

    return Response(
        {
            "message": "Article bucket url successfully updated",
            "bucket_url": bucket_url,
        },
        status=status.HTTP_200_OK,
    )


##### articles #####
def get_articles_from_page(articles, page, page_size):

    paginator = Paginator(articles, page_size)

    if page > paginator.num_pages:
        return Article.objects.none()

    articles = paginator.get_page(page)

    return articles.object_list


@api_view(["GET"])
def get_articles(request):
    try:
        title = request.query_params.get("title")
        author_name = request.query_params.get("authorName")
        journal_name = request.query_params.get("journalName")
        journal_id = request.query_params.get("journalID")
        issue_id = request.query_params.get("issueID")
        exact = request.query_params.get("exact")

        page = request.query_params.get("page")
        page_size = request.query_params.get("page_size")

        only_jstor_id = request.query_params.get(ONLY_JSTOR_ID) == "1"
        scraped = request.query_params.get("scraped")

        if not page:
            page = 1
        else:
            page = int(page)

        if scraped:
            scraped = int(scraped)
        else:
            scraped = -1

        if not page_size:
            page_size = 50
        else:
            page_size = int(page_size)

        if not exact:
            exact = 0.1
        else:
            exact = float(exact)

        if request.method == "GET":
            if title:
                return get_articles_by_title(
                    title, only_jstor_id, page, page_size, exact
                )
            elif author_name:
                return get_articles_by_author(
                    author_name, only_jstor_id, scraped, page, page_size, exact
                )
            elif journal_name or journal_id:
                return get_articles_by_journal(
                    journal_name,
                    journal_id,
                    only_jstor_id,
                    scraped,
                    page,
                    page_size,
                    exact,
                )
            elif issue_id:
                return get_articles_by_issue(
                    issue_id, only_jstor_id, scraped, page, page_size
                )
            else:
                return get_all_articles(scraped)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_all_articles(scraped):

    if scraped == 1:
        articles = Article.objects.filter(bucketURL__isnull=False)
    elif scraped == 0:
        articles = Article.objects.filter(bucketURL__isnull=True)
    else:
        articles = Article.objects.all()

    articles_serializer = ArticleSerializer(articles, many=True)
    return Response(articles_serializer.data, status.HTTP_200_OK)


def get_articles_by_title(title, only_jstor_id, page, page_size, exact):
    articles = (
        Article.objects.annotate(
            similarity=TrigramSimilarity("title", title),
        )
        .filter(similarity__gte=exact)
        .order_by("-similarity")
    )

    articles = get_articles_from_page(articles, page, page_size)

    if only_jstor_id:
        return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
    else:
        article_serializer = ArticleSerializer(articles, many=True)
        return Response(article_serializer.data, status.HTTP_200_OK)


def get_articles_by_author(author_name, only_jstor_id, scraped, page, page_size, exact):
    try:
        authors = (
            Author.objects.annotate(
                similarity=TrigramSimilarity("authorName", author_name),
            )
            .filter(similarity__gte=exact)
            .order_by("-similarity")
        )
    except Author.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    print("** get by authors")

    if authors:
        articles = Article.objects.filter(authors__in=authors)

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)


def get_articles_by_journal(
    journal_name, journal_id, only_jstor_id, scraped, page, page_size, exact
):
    try:
        if journal_name:
            journals = (
                Journal.objects.annotate(
                    similarity=TrigramSimilarity("journalName", journal_name),
                )
                .filter(similarity__gte=exact)
                .order_by("-similarity")
            )
        else:
            journals = Journal.objects.filter(journalID=journal_id)
    except Journal.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if journals:

        articles = Article.objects.filter(issue__journal__in=journals)

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)


def get_articles_by_issue(issue_id, only_jstor_id, scraped, page, page_size):
    try:
        issue = Issue.objects.get(issueID=issue_id)
    except Journal.DoesNotExist:
        return Response(None, status.HTTP_400_BAD_REQUEST)

    if issue:
        articles = Article.objects.filter(issue__issueID=issue.issueID)

        if scraped == 1:
            articles = articles.filter(bucketURL__isnull=False)
        elif scraped == 0:
            articles = articles.filter(bucketURL__isnull=True)

        articles = get_articles_from_page(articles, page, page_size)

        if only_jstor_id:
            return Response(articles.values("articleJstorID"), status.HTTP_200_OK)
        else:
            articles_serializer = ArticleSerializer(articles, many=True)
            return Response(articles_serializer.data, status.HTTP_200_OK)
    else:
        return Response({"message": "no articles found"}, status.HTTP_200_OK)


##### authors #####
@api_view(["GET"])
def get_authors(request):
    try:
        author_name = request.query_params.get("authorName")

        if request.method == "GET":
            if author_name:
                return get_authors_by_name(author_name)

            authors = Author.objects.all()[:50]

            authors_serializer = AuthorSerializer(authors, many=True)
            return Response(authors_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_authors_by_name(author_name):
    authors = (
        Author.objects.annotate(
            similarity=TrigramSimilarity("authorName", author_name),
        )
        .filter(similarity__gte=0.1)
        .order_by("-similarity")[:10]
    )

    if authors:
        authors_serializer = AuthorSerializer(authors, many=True)
        return Response(authors_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### issues #####
@api_view(["GET"])
def get_issues(request):
    try:
        journal_id = request.query_params.get("journalID")

        print("getting issues ", journal_id)
        if request.method == "GET":
            if journal_id:
                return get_issues_by_journal(journal_id)

            issues = Issue.objects.all()[:50]

            issues_serializer = IssueSerializer(issues, many=True)
            return Response(issues_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_issues_by_journal(journal_id):

    issues = Issue.objects.filter(journal__journalID=journal_id)

    if issues:
        issues_serializer = IssueSerializer(issues, many=True)
        return Response(issues_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### journals #####
@api_view(["GET"])
def get_journals(request):
    try:
        journal_name = request.query_params.get("journalName")

        if request.method == "GET":
            if journal_name:
                return get_journals_by_name(journal_name)

            journals = Journal.objects.all()[:50]

            journals_serializer = JournalSerializer(journals, many=True)
            return Response(journals_serializer.data, status.HTTP_200_OK)
    except Exception:
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


def get_journals_by_name(journal_name):
    journals = (
        Journal.objects.annotate(
            similarity=TrigramSimilarity("journalName", journal_name),
        )
        .filter(similarity__gte=0.1)
        .order_by("-similarity")[:10]
    )

    if journals:
        journals_serializer = JournalSerializer(journals, many=True)
        return Response(journals_serializer.data, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### accounts #####
@api_view(["GET"])
def get_accounts(request):
    try:
        return Response(get_accounts_scraped(), status.HTTP_200_OK)
    except Exception as e:
        print(e)
        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_amount_for_distribution(request):
    algod_client = settings.ALGOD_CLIENT
    app_address = settings.SMART_CONTRACT_ADDRESS

    smart_contract_info = algod_client.account_info(app_address)

    # print(smart_contract_info)

    smart_contract_info["amount_for_distribution"] = (
        smart_contract_info["amount"] - smart_contract_info["min-balance"]
    )

    return Response(smart_contract_info, status.HTTP_200_OK)


@api_view(["GET"])
def get_amount_distributed_todate(request):
    algod_client = settings.ALGOD_CLIENT
    app_id = settings.SMART_CONTRACT_ID

    app = algod_client.application_info(app_id)
    global_state = (
        app["params"]["global-state"] if "global-state" in app["params"] else []
    )

    app_info = decode_state(global_state)

    # print(f"global_state for app_id {app_id}: ", app_info)

    return Response(app_info, status.HTTP_200_OK)


##### donate #####
@api_view(["GET"])
def distribute_donations(request):
    """
    distribution workflow:
    if the balance of the contract is above the threshold:
    AND if the manager account has enough funds:
    grab all accounts that have scraped at least one paper,
    create a distribute_donations txn for every 4 accounts,
    create an atomic group (batch) for every 16 txns,
    take a snapshot of the contract (take_snapshot contract method),
    submit batches
    """

    token = request.query_params.get("distributeToken")

    if token != env.get_value("DISTRIBUTE_DONATIONS_TOKEN"):
        return Response(None, status.HTTP_400_BAD_REQUEST)

    # TODO: increase after testing
    DISTRIBUTION_THRESHOLD = 1_000_000
    MAX_TRIES = 5
    SLEEP = 0.05
    LONG_SLEEP = 5

    algod_client = settings.ALGOD_CLIENT
    app_id = int(settings.SMART_CONTRACT_ID)
    app_address = settings.SMART_CONTRACT_ADDRESS
    manager_address = settings.SMART_CONTRACT_MANAGER_ADDRESS

    info = algod_client.account_info(app_address)

    if info["amount"] >= DISTRIBUTION_THRESHOLD:
        # TODO: add choice of mainnet and testnet
        signer = AccountTransactionSigner(env.get_value("DEPLOYMENT_PRIVATE"))

        take_snapshot_method = Method.from_signature("take_snapshot(uint64)void")
        distribute_donations_method = Method.from_signature(
            "distribute_donations()void"
        )

        accounts = get_accounts_scraped()
        # make sure manager has at least:
        # minimum_account_balance +
        # fees for each txn +
        # fees for each inner txn per acount
        manager_info = algod_client.account_info(manager_address)
        funds_needed = (
            manager_info["min-balance"]
            + ((ceil(len(accounts) / 4) * 1000))
            + (len(accounts) * 1000)
        )

        if manager_info["amount"] >= funds_needed:
            total_scraped = 0
            i = 0
            atc_list: list[AtomicTransactionComposer] = []

            # create txns
            while i < len(accounts):
                number_of_accounts_in_txn = min(4, len(accounts) - i)
                accounts_subset = accounts[i : i + number_of_accounts_in_txn]
                i += number_of_accounts_in_txn

                sp = algod_client.suggested_params()
                sp.fee = 1000 + (1000 * number_of_accounts_in_txn)
                sp.flat_fee = True
                args = [distribute_donations_method.get_selector()]
                accs = []

                for account in accounts_subset:
                    args.append(account["scraped"])
                    accs.append(account["algorandAddress"])

                    total_scraped += account["scraped"]

                if len(atc_list) == 0 or atc_list[-1].get_tx_count() == 16:
                    atc_list.append(AtomicTransactionComposer())

                atc_list[-1].add_transaction(
                    TransactionWithSigner(
                        txn=ApplicationNoOpTxn(
                            sender=manager_address,
                            sp=sp,
                            index=app_id,
                            app_args=args,
                            accounts=accs,
                        ),
                        signer=signer,
                    )
                )

            # take snapshot
            atc = AtomicTransactionComposer()
            atc.add_method_call(
                app_id=app_id,
                method=take_snapshot_method,
                sender=manager_address,
                sp=algod_client.suggested_params(),
                signer=signer,
                method_args=[total_scraped],
            )
            for tries in range(1, MAX_TRIES + 1):
                try:
                    resp: AtomicTransactionResponse = atc.execute(algod_client, 5)
                    print(
                        """
                        Took snapshot with {} papers scraped.
                        Confirmed round: {}
                        Txn ID: {}
                        """.format(
                            total_scraped, resp.confirmed_round, resp.tx_ids.pop()
                        )
                    )
                    break
                except Exception as e:
                    print(e)
                    if tries < MAX_TRIES:
                        print(
                            "Snapshot failed - trying again (attempt {}))".format(
                                tries + 1
                            )
                        )
                    else:
                        print("Max tries hit trying to take snapshot - aborting")
                        return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)
                tries += 1
                sleep(SLEEP)

            # submit distribution txns
            txns = []
            for atc in atc_list:
                for tries in range(1, MAX_TRIES + 1):
                    try:
                        txns.extend(atc.submit(algod_client))
                        break
                    except Exception as e:
                        if tries < MAX_TRIES:
                            print(
                                "Distribution failed to submit - trying again (attempt {}))".format(
                                    tries + 1
                                )
                            )
                        else:
                            print("Max tries hit trying to distribute - aborting")
                            return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)
                    tries += 1
                    sleep(SLEEP)

            # give time for txns to be committed (hopefully)
            sleep(LONG_SLEEP)

            # check for confirmation
            unconfirmed_txns = []
            failed_txns = []
            for tries in range(1, MAX_TRIES + 1):
                if len(unconfirmed_txns) == 0:
                    # only need to check every 16th txn since it's in an atomic group
                    # (if the txn succeeded then the next 15 txns must have too)
                    for i in range(0, len(txns), 16):
                        info = algod_client.pending_transaction_info(txns[i])
                        if "confirmed-round" in info.keys():
                            print(
                                "Txn {} confirmed in round {}".format(
                                    txns[i], info["confirmed-round"]
                                )
                            )
                        else:
                            if info["pool-error"] == "":
                                unconfirmed_txns.append(txns[i])
                                print("Txn {} not yet confirmed".format(txns[i]))
                            else:
                                failed_txns.append(txns[i])
                                print(
                                    "Txn {} errored with message: {}".format(
                                        txns[i], info["pool-error"]
                                    )
                                )
                        sleep(SLEEP)
                else:
                    for txn in unconfirmed_txns:
                        info = algod_client.pending_transaction_info(txn)
                        if "confirmed-round" in info.keys():
                            print(
                                "Txn {} confirmed in round {}".format(
                                    txn, info["confirmed-round"]
                                )
                            )
                            unconfirmed_txns.remove(txn)
                        else:
                            if info["pool-error"] == "":
                                print("Txn {} not yet confirmed".format(txn))
                            else:
                                print(
                                    "Txn {} errored with message: {}".format(
                                        txn, info["pool-error"]
                                    )
                                )
                                unconfirmed_txns.remove(txn)
                                failed_txns.append(txn)

                if len(unconfirmed_txns) == 0:
                    break

                # TODO: do something about failed txns (maybe?)

                # give time for txns to be committed (hopefully)
                tries += 1
                sleep(LONG_SLEEP)

            if len(unconfirmed_txns) > 0 or len(failed_txns) > 0:
                print(
                    "Some/all txns were not confirmed/failed:\nUnconfirmed: {}\nFailed: {}".format(
                        unconfirmed_txns, failed_txns
                    )
                )
                return Response(
                    {"unconfirmed": unconfirmed_txns, "failed": failed_txns},
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            print(
                "Manager has insufficient funds to run distribution ({} microALGO needed)".format(
                    funds_needed
                )
            )
            return Response(None, status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(txns, status.HTTP_200_OK)

    return Response(None, status.HTTP_200_OK)


##### util #####
def update_article_account(article_id, algorand_address):
    if algorand_address:
        article = Article.objects.get(articleJstorID=article_id)

        account, account_created = Account.objects.get_or_create(
            algorandAddress=algorand_address,
            defaults={"algorandAddress": algorand_address},
        )

        # article.bucketURL = unscanned_bucket_url
        article.account = account
        article.save()


def get_accounts_scraped():
    accounts = Account.objects.annotate(
        scraped=Count("articles", filter=Q(articles__bucketURL__isnull=False))
    ).filter(scraped__gt=0)

    account_serializer = AccountSerializer(accounts, many=True)
    return account_serializer.data


# Adapted from Beaker (https://github.com/algorand-devrel/beaker/blob/master/beaker/client/state_decode.py)
def str_or_hex(v):
    decoded: str = ""
    try:
        decoded = v.decode("utf-8")
    except Exception:
        decoded = v.hex()

    return decoded


def decode_state(state, raw=False):

    decoded_state = {}

    for sv in state:

        raw_key = b64decode(sv["key"])

        key = raw_key if raw else str_or_hex(raw_key)
        val = None

        action = (
            sv["value"]["action"] if "action" in sv["value"] else sv["value"]["type"]
        )

        if action == 1:
            raw_val = b64decode(sv["value"]["bytes"])
            val = raw_val if raw else str_or_hex(raw_val)
        elif action == 2:
            val = sv["value"]["uint"]
        elif action == 3:
            val = None

        decoded_state[key] = val
    return decoded_state
