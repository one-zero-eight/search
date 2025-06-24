# src/utils/scheduler.py
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.api.logging_ import logger
from src.modules.parsers.routes import upload_markdown_file
from src.modules.sources_enum import InfoSources


async def run_parsers():
    await upload_markdown_file(InfoSources.campuslife)
    await upload_markdown_file(InfoSources.eduwiki)
    await upload_markdown_file(InfoSources.hotel)
    print("Parsers complete job")


def start_scheduler():
    print("Scheduler is running")
    scheduler = AsyncIOScheduler()

    scheduler.add_job(run_parsers, trigger=IntervalTrigger(days=1), next_run_time=datetime.now())

    scheduler.start()
    logger.info("Scheduler started")
