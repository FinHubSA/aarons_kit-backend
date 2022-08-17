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
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
