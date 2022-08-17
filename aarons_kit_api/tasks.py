from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger
from aarons_kit.celery import app as celery_app

import redis

# Connect to our Redis instance
redis_instance = redis.StrictRedis(host=settings.REDIS_HOST,port=settings.REDIS_PORT, db=0)

@celery_app.on_after_finalize.connect
def setup_tasks(sender, **kwargs):

    print("*** setup tasks! ***")

    process_masterlist_task.delay() 

@celery_app.task
def process_masterlist_task():
    from .masterlist_scraper import start_scraping

    # start scrapping data
    start_scraping()
    


