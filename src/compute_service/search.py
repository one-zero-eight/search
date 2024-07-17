import logging
import multiprocessing
import queue
import time
from multiprocessing import Manager, Process

import httpx
import numpy as np
from pydantic import TypeAdapter
from qdrant_client import QdrantClient, models
from qdrant_client.models import ScoredPoint
from sentence_transformers import SentenceTransformer, CrossEncoder
from torch import cuda

from src.compute_service.bm25 import Bm25
from src.compute_service.text import clean_text
from src.config import settings
from src.modules.compute.schemas import SearchTask, SearchResult, MoodleFileResult

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)

QDRANT_COLLECTION = settings.compute_settings.qdrant_collection_name
t1 = time.monotonic()
qdrant = QdrantClient(url=settings.compute_settings.qdrant_url.get_secret_value())
t2 = time.monotonic()

logger = logging.getLogger("compute.search")
logger.info(f"Connected to Qdrant loaded in {t2 - t1:.2f} seconds")

t1 = time.monotonic()
device = "cuda" if cuda.is_available() else "cpu"
bi_encoder = SentenceTransformer(settings.compute_settings.bi_encoder_name, trust_remote_code=True, device=device)
cross_encoder = CrossEncoder(settings.compute_settings.cross_encoder_name, trust_remote_code=True, device=device)
bi_encoder.share_memory()
bm25 = Bm25()
t2 = time.monotonic()

logger = logging.getLogger("compute.search")
logger.info(f"Loaded bi and cross encoders on ({device}) in {t2 - t1:.2f} seconds")


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
    tasks = type_adapter.validate_python(pending_searches_data)
    return tasks


_processed_tasks = set()


def rerank(query: str, scored_points: list[ScoredPoint], score_threshold: float | None = None) -> list[ScoredPoint]:
    scored_points = np.array(scored_points)

    sentences = []
    for scored_point in scored_points:
        sentences.append([query, scored_point.payload["text"]])

    # get cross encoder scores
    _1 = time.monotonic()
    reranked_scores: np.ndarray = cross_encoder.predict(
        sentences, batch_size=settings.compute_settings.cross_encoder_batch_size, show_progress_bar=False
    )
    _2 = time.monotonic()
    logger.info(f"Reranked by CrossEncoder in {_2 - _1:.2f} seconds")

    if score_threshold is not None:
        filtered_amount = len(reranked_scores[reranked_scores > score_threshold])
    else:
        filtered_amount = len(reranked_scores)

    # get indexes of values to keep sorted (reversed) order
    indexes = np.argsort(reranked_scores)[::-1][:filtered_amount]

    # apply indexes to make sorted list and revert it with better matches first
    reranked_scores = reranked_scores[indexes]
    reranked_scored_points = scored_points[indexes]

    for score, point in zip(reranked_scores, reranked_scored_points):
        point.score = score

    return list(reranked_scored_points)


def search(query: str) -> list[MoodleFileResult]:
    query = clean_text(query)

    # text to vector repr
    _1 = time.monotonic()

    dense_embedding: np.array = bi_encoder.encode(
        query,
        batch_size=settings.compute_settings.bi_encoder_batch_size,
        show_progress_bar=False,
        prompt_name="s2p_query" if settings.compute_settings.bi_encoder_name.__contains__("stella") else None,
    )
    _2 = time.monotonic()
    logger.info(f"Text encoded by BiEncoder in {_2 - _1:.2f} seconds")

    # text to sparse vector repr
    _1 = time.monotonic()
    bm25_embedding = bm25.query_embed(query)
    _2 = time.monotonic()
    logger.info(f"Text encoded by BM25 in {_2 - _1:.2f} seconds")

    # ann for limit amount of chunks (points)
    _1 = time.monotonic()
    scored_points = qdrant.query_points(
        QDRANT_COLLECTION,
        prefetch=[
            models.Prefetch(
                query=bm25_embedding,
                using="bm25",
                limit=1000,
            ),
            models.Prefetch(
                query=dense_embedding,
                using="dense",
                limit=1000,
            ),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=100,
    ).points

    _2 = time.monotonic()
    logger.info(f"Qdrant Search completed in {_2 - _1:.2f} seconds")

    # apply cross encoder to rerank (with threshold possible) and set new scores
    reranked_scored_points: list[ScoredPoint] = rerank(query, scored_points, 0.0)

    added_ids = set()
    results: list[MoodleFileResult] = []
    for reranked_scored_point in reranked_scored_points:
        if reranked_scored_point.payload is None:
            continue

        doc_ref: dict | None = reranked_scored_point.payload.get("document-ref", None)
        if doc_ref is None:
            continue

        if "course_id" not in doc_ref or "module_id" not in doc_ref or "filename" not in doc_ref:
            continue

        course_id = doc_ref["course_id"]
        module_id = doc_ref["module_id"]
        filename = doc_ref["filename"]

        if (course_id, module_id, filename) not in added_ids:
            added_ids.add((course_id, module_id, filename))
            result = MoodleFileResult(
                course_id=course_id,
                module_id=module_id,
                filename=filename,
                score=reranked_scored_point.score,
            )
            results.append(result)

    return results


def process_tasks(tasks: list[SearchTask]) -> None:
    _1 = time.monotonic()
    _results = {task.task_id: search(task.query) for task in tasks}
    _2 = time.monotonic()
    logger.info(f"Processed {len(tasks)} tasks in {_2 - _1:.2f} seconds")

    results = []
    for task in tasks:
        result = _results.get(task.task_id, None)
        if result is None:
            results.append(SearchResult(task_id=task.task_id, status="failed"))
        else:
            results.append(SearchResult(task_id=task.task_id, status="completed", result=result))

    type_adapter = TypeAdapter(list[SearchResult])
    # Post result to the API
    try:
        _1 = time.monotonic()
        with get_client() as session:
            response = session.post("/completed-searchs", json=type_adapter.dump_python(results))
            response.raise_for_status()
        _2 = time.monotonic()
        if len(results) > 0:
            logger.info(f"Stored {len(results[0].result)} results in {_2 - _1:.2f} seconds")
        else:
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
