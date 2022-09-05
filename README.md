# Getting Started With Aaron's Kit

## Prerequisites

You may need to use `python3` instead of `python` when following this guide if `python` calls Python 2 or is unrecognized by your terminal.

### Get gcloud CLI

[Installation notes](https://cloud.google.com/sdk/docs/install).

- If you already have it make sure it's using the correct account.
- Check the project list. If they are from another account then change the gcloud account.
`gcloud projects list`
- Change the gcloud account to correct one
`gcloud auth login`
- To push docker container images to gcp container registry
`gcloud auth configure-docker`

### Get Cloud SQL Auth Proxy

Follow the relevant steps [here](https://cloud.google.com/python/django/run#connect_sql_locally).

### Pull the Repo

`git clone https://github.com/FinHubSA/aarons_kit-backend`

## Confirm Python Version

`python -V`  

Make sure you have at least version 3.8.

## Set Up Virtual Environment

In the cloned repository:

```
python -m venv venv && \
source venv/bin/activate && \
pip install --upgrade pip && \
pip install -r requirements.txt
```

## Running Aaron's Kit locally

In the same directory as where your Cloud SQL Auth Proxy is installed:

`./cloud_sql_proxy -instances="aarons-kit-360209:europe-west6:aarons-kit"=tcp:5432`

Export some environment variables:

`export GOOGLE_CLOUD_PROJECT=aarons-kit-360209`

`export USE_CLOUD_SQL_AUTH_PROXY=true`

Back in the cloned repository:

`python manage.py runserver`

Then visit http://localhost:8000/

## Pushing updates to Cloud Run

Make migrations (if any):

python manage.py makemigrations && \
python manage.py makemigrations api

Submit a new build:

```
gcloud builds submit --config cloudmigrate.yaml \
    --substitutions _INSTANCE_NAME=aarons-kit,_REGION=europe-west6
```

Deploy to Cloud Run:

```
gcloud run deploy api-service \
    --platform managed \
    --region europe-west6 \
    --image gcr.io/aarons-kit-360209/api-service
```
