# src/utils/scheduler.py
import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.modules.campus_life.__main__ import main as campus_life
from src.modules.dorms.__main__ import process_pages as dorms

logger = logging.getLogger(__name__)


def start_scheduler():
    print("Scheduler is running")
    scheduler = BackgroundScheduler()

    scheduler.add_job(campus_life, trigger=IntervalTrigger(seconds=120), next_run_time=datetime.now())

    scheduler.add_job(
        dorms,
        args=["https://hotel.innopolis.university/", "/", 10],
        trigger=IntervalTrigger(seconds=120),
        next_run_time=datetime.now(),
    )

    scheduler.start()
    logger.info("Scheduler started")
