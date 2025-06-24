from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.api.logging_ import logger
from src.modules.parsers.routes import run_parse_route
from src.modules.sources_enum import InfoSources


async def run_parsers():
    await run_parse_route(InfoSources.campuslife)
    await run_parse_route(InfoSources.eduwiki)
    await run_parse_route(InfoSources.hotel)
    print("Parsers complete job")


def start_scheduler():
    print("Scheduler is running")
    scheduler = AsyncIOScheduler()

    scheduler.add_job(run_parsers, trigger=IntervalTrigger(days=1), next_run_time=datetime.now())

    scheduler.start()
    logger.info("Scheduler started")
