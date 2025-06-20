# src/utils/scheduler.py
import logging
import subprocess
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


def run_module(module_name: str, *args):
    try:
        logger.info(f"Running module: {module_name}")
        subprocess.run(["poetry", "run", "python", "-m", module_name, *args], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running module {module_name}: {e}")


def start_scheduler():
    print("Scheduler is running")
    scheduler = BackgroundScheduler()

    jobs = [("src.modules.dorms", ["https://hotel.innopolis.university/", "-t 30"]), ("src.modules.campus_life", [])]

    for module_name, args in jobs:
        scheduler.add_job(
            run_module, args=[module_name, *args], trigger=IntervalTrigger(seconds=120), next_run_time=datetime.now()
        )

    scheduler.start()
    logger.info("Scheduler started")
