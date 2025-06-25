from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.api.logging_ import logger
from src.modules.parsers.routes import run_parse_route
from src.modules.sources_enum import InfoSources


async def run_parsers():
    for source in (InfoSources.campuslife, InfoSources.eduwiki, InfoSources.hotel):
        try:
            await run_parse_route(source, indexing_is_needed=True, parsing_is_needed=True)
        except Exception as e:
            logger.error(f"Error during parsing or saving: {e}", exc_info=True)

    logger.info("Parsers complete job")


def start_scheduler():
    logger.info("Scheduler is running")
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_parsers, trigger=IntervalTrigger(days=1), next_run_time=datetime.now() + timedelta(hours=1))
    scheduler.start()
    logger.info("Scheduler started")
