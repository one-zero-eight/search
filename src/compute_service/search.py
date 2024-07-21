import logging
import time
from contextlib import contextmanager

import numpy as np
from qdrant_client import QdrantClient, models
from qdrant_client.models import ScoredPoint
from sentence_transformers import SentenceTransformer, CrossEncoder
from torch import cuda

from src.compute_service.bm25 import Bm25
from src.compute_service.text import clean_text_common, clean_text_for_sparse
from src.config import settings
from src.modules.compute.schemas import MoodleFileResult

logger = logging.getLogger("compute.search")


@contextmanager
def timeit(name):
    start_time = time.monotonic()
    yield
    end_time = time.monotonic()
    logger.info(f"{name} completed in {end_time - start_time:.2f} seconds")


QDRANT_COLLECTION = settings.compute_settings.qdrant_collection_name
qdrant = QdrantClient(url=settings.compute_settings.qdrant_url.get_secret_value())

with timeit("BiEncoder, BM25 and CrossEncoder loading"):
    device = "cuda" if cuda.is_available() else "cpu"
    bi_encoder = SentenceTransformer(settings.compute_settings.bi_encoder_name, trust_remote_code=True, device=device)
    cross_encoder = CrossEncoder(settings.compute_settings.cross_encoder_name, trust_remote_code=True, device=device)
    bi_encoder.share_memory()
    bm25 = Bm25()

    logger.info(f"Device: {device}")


def rerank(query: str, scored_points: list[ScoredPoint], score_threshold: float | None = None) -> list[ScoredPoint]:
    scored_points = np.array(scored_points)

    sentences = []
    for scored_point in scored_points:
        sentences.append([query, scored_point.payload["text"]])

    with timeit("CrossEncoder reranking"):
        reranked_scores: np.ndarray = cross_encoder.predict(
            sentences, batch_size=settings.compute_settings.cross_encoder_batch_size, show_progress_bar=False
        )

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


def search_pipeline(query: str) -> list[MoodleFileResult]:
    query = clean_text_common(query)

    # text to vector repr
    with timeit("Dense (BiEncoder) encoding"):
        dense_embedding: np.array = bi_encoder.encode(
            query,
            batch_size=settings.compute_settings.bi_encoder_batch_size,
            show_progress_bar=False,
            prompt_name="s2p_query" if settings.compute_settings.bi_encoder_name.__contains__("stella") else None,
        )

    with timeit("Sparse (BM25) encoding"):
        bm25_embedding = bm25.query_embed(clean_text_for_sparse(query))

    with timeit("Qdrant Search"):
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

    # apply cross encoder to rerank (with threshold possible) and set new scores
    if scored_points:
        reranked_scored_points: list[ScoredPoint] = rerank(
            query, scored_points, settings.compute_settings.cross_encoder_threshold
        )
    else:
        reranked_scored_points = []

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
