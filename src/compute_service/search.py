import itertools
import json
import logging
import multiprocessing
import queue
import time
from multiprocessing import Manager, Process
from typing import Iterable

import httpx
import retriv.base_retriever
from pydantic import TypeAdapter
from retriv import DenseRetriever

from src.config import settings
from src.modules.compute.schemas import SearchTask, SearchResult, MoodleFileResult

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

_1 = time.monotonic()
dense_retriever = DenseRetriever.load("innohassle-search")
_2 = time.monotonic()

logger = logging.getLogger("compute.search")
logger.info(f"DenseRetriever loaded in {_2 - _1:.2f} seconds")
logger.info(f"Doc Count: {dense_retriever.doc_count}")


def get_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    )


def map_internal_ids_to_original_ids(self, doc_ids: Iterable) -> list[str]:
    return [self.id_mapping[doc_id] for doc_id in doc_ids if doc_id != -1]


retriv.base_retriever.BaseRetriever.map_internal_ids_to_original_ids = map_internal_ids_to_original_ids


def fetch_tasks() -> list[SearchTask]:
    with get_client() as session:
        response = session.get("/pending-searchs")
        response.raise_for_status()
        pending_searches_data = response.json()
    type_adapter = TypeAdapter(list[SearchTask])
    tasks = type_adapter.validate_python(pending_searches_data)
    return tasks


_processed_tasks = set()


def process_tasks(tasks: list[SearchTask]) -> None:
    _1 = time.monotonic()
    _results = {task.task_id: dense_retriever.search(task.query) for task in tasks}
    _2 = time.monotonic()
    logger.info(f"Processed {len(tasks)} tasks in {_2 - _1:.2f} seconds")

    results = []
    for task in tasks:
        result = _results.get(task.task_id, None)
        if result is None:
            results.append(SearchResult(task_id=task.task_id, status="failed"))
        else:
            relevant_chunks = [
                {
                    "id": json.loads(_["id"]),
                    "score": float(_["score"]),
                }
                for _ in result
            ]
            # [
            #     {
            #         "id": {
            #             "course_id": 1114,
            #             "module_id": 83459,
            #             "filename": "Lab 5 (AddersSubtractors).pdf",
            #             "page_number": 2,
            #             "chunk_number": 0,
            #         },
            #         "score": 0.286164253950119,
            #     },
            # ]
            # Collect chunks to documents
            relevant_documents = []
            # sort
            _key = lambda _: (_["id"]["course_id"], _["id"]["module_id"], _["id"]["filename"])  # noqa: E731
            relevant_chunks.sort(key=_key)

            for (course_id, module_id, filename), grouping in itertools.groupby(relevant_chunks, key=_key):
                relevant_documents.append(
                    MoodleFileResult(
                        course_id=course_id,
                        module_id=module_id,
                        filename=filename,
                        score=[item["score"] for item in grouping],
                    )
                )
            relevant_documents.sort(key=lambda _: max(_.score), reverse=True)

            results.append(
                SearchResult(
                    task_id=task.task_id,
                    status="completed",
                    result=relevant_documents,
                )
            )
    type_adapter = TypeAdapter(list[SearchResult])
    # Post result to the API
    try:
        _1 = time.monotonic()
        with get_client() as session:
            response = session.post("/completed-searchs", json=type_adapter.dump_python(results))
            response.raise_for_status()
        _2 = time.monotonic()
        logger.info(f"Stored {len(results)} results in {_2 - _1:.2f} seconds")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to store result for tasks: {e}")
    _processed_tasks.update(task.task_id for task in tasks)


def fetcher(namespace):
    logger.info(f"Fetch tasks from API every {settings.compute_settings.check_search_queue_period} seconds")
    while True:
        try:
            tasks = fetch_tasks()
        except httpx.HTTPStatusError as e:
            logger.error(f"Failed to fetch tasks: {e}")
            time.sleep(settings.compute_settings.check_search_queue_period)
            continue

        logger.debug(f"Populated by {len(tasks)} tasks")

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
                pack = [task for task in pack if task.task_id not in _processed_tasks]
                if not pack:
                    continue
                logger.info(f"Processing {len(pack)} items")
                process_tasks(pack)

        fetcher_process.join()


if __name__ == "__main__":
    main()
