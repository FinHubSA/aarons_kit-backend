<<<<<<< HEAD
import os
import os.path

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB"),
        "USER": os.environ.get("POSTGRES_USER"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
        "HOST": "db",
        "PORT": 5432,
    }
}

# redis settings
REDIS_HOST="localhost" # "redis" # for docker
REDIS_PORT="6379"

# celery settings
CELERY_BROKER_URL = "redis://"+REDIS_HOST+":"+REDIS_PORT
CELERY_RESULT_BACKEND = "redis://"+REDIS_HOST+":"+REDIS_PORT

SCRAPE_MINUTE = '*'
SCRAPE_HOUR = '*'
SCRAPE_DAY_OF_WEEK = '*'
SCRAPE_DAY_OF_MONTH = '*'
SCRAPE_MONTH_OF_YEAR = '*'
=======
from .settings import env

# To use local settings, rename this file to be local_settings.py
# DB name is: <initials>_test_masterlist
def update_db_settings(db_settings):
    db_settings["TEST"] = {'NAME': 'tc_test_masterlist'}
    return db_settings


>>>>>>> d25ed0b8307e348b41334bfcc1412ecddd72c990
