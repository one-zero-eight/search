import logging
import multiprocessing
import queue
import time
from multiprocessing import Manager, Process

import httpx
from pydantic import TypeAdapter
from retriv import HybridRetriever

from src.config import settings
from src.modules.compute.schemas import SearchTask, SearchResult

_1 = time.monotonic()
hybrid_retriever = HybridRetriever.load("innohassle-search")
_2 = time.monotonic()

logger = logging.getLogger("compute.search")
logger.info(f"HybridRetriever loaded in {_2 - _1:.2f} seconds")


def get_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    )


def fetch_tasks() -> list[SearchTask]:
    with get_client() as session:
        response = session.get("/pending-searchs")
        response.raise_for_status()
        pending_searches_data = response.json()
    type_adapter = TypeAdapter(list[SearchTask])
    tasks = type_adapter.validate_python(pending_searches_data["queries"])
    return tasks


def process_tasks(tasks: list[SearchTask]) -> None:
    _1 = time.monotonic()
    _results: dict = hybrid_retriever.msearch([{"id": task.task_id, "text": task.query} for task in tasks])
    _2 = time.monotonic()
    logger.info(f"Processed {len(tasks)} tasks in {_2 - _1:.2f} seconds")

    results = []
    for task in tasks:
        result = _results.get(task.task_id, None)
        if result is None:
            results.append(SearchResult(task_id=task.task_id, status="failed", result={"message": "No result found"}))
        else:
            results.append(SearchResult(task_id=task.task_id, status="completed", result=result))

    # Post result to the API
    try:
        _1 = time.monotonic()
        with get_client() as session:
            response = session.post("/completed-searchs", json=results)
            response.raise_for_status()
        _2 = time.monotonic()
        logger.info(f"Stored {len(results)} results in {_2 - _1:.2f} seconds")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to store result for tasks: {e}")


def fetcher(namespace):
    logger.info(f"Fetch tasks from API every {settings.compute_settings.check_search_queue_period} seconds")
    while True:
        try:
            tasks = fetch_tasks()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch tasks: {e}")
            time.sleep(settings.compute_settings.check_search_queue_period)
            continue

        logger.info(f"Populated by {len(tasks)} tasks")

        for task in tasks:
            namespace.search_queue: multiprocessing.Queue
            namespace.search_queue.put_nowait(task)

        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.check_search_queue_period)


def main():
    with Manager() as manager:
        namespace = manager.Namespace()
        namespace.search_queue = manager.Queue()

        # spawn fetcher
        fetcher_process = Process(target=fetcher, args=(namespace,))
        fetcher_process.start()

        while True:
            pack = []
            while True:
                try:
                    namespace.search_queue: multiprocessing.Queue
                    task = namespace.search_queue.get_nowait()
                    pack.append(task)
                except queue.Empty:
                    break

            if not pack:
                time.sleep(0.001)  # Avoid busy waiting
                continue
            else:
                logger.info(f"Processing {len(pack)} items")
                process_tasks(pack)

        fetcher_process.join()


if __name__ == "__main__":
    main()
