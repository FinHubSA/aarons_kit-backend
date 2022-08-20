from django.conf import settings
from celery import shared_task
from celery.utils.log import get_task_logger
from aarons_kit.celery import app as celery_app
from celery.schedules import crontab

import redis

# Connect to our Redis instance
redis_instance = redis.StrictRedis(host=settings.REDIS_HOST,port=settings.REDIS_PORT, db=0)
    
@celery_app.on_after_finalize.connect
def setup_tasks(sender, **kwargs):
    print("*** task setup ***")
    
    # set up the periodic run
    sender.add_periodic_task(
        crontab(
            minute=settings.SCRAPE_MINUTE, 
            hour=settings.SCRAPE_HOUR, 
            day_of_week=settings.SCRAPE_DAY_OF_WEEK,
            day_of_month=settings.SCRAPE_DAY_OF_MONTH,
            month_of_year=settings.SCRAPE_MONTH_OF_YEAR),
        process_masterlist_task.s(),
    )

    # schedule for the first time
    process_masterlist_task.delay()

    # sender.add_periodic_task(60.0, process_masterlist_task.s(), expires=20, name='scrap masterlist')

@celery_app.task
def process_masterlist_task():
    from .masterlist_scraper import scrape_all_journals

    scrape_all_journals()
    


