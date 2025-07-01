import asyncio
import time

import lancedb
import pandas as pd

from src.api.logging_ import logger
from src.config import settings
from src.ml_service.text import clean_text
from src.modules.sources_enum import InfoSources


async def search_pipeline(
    query: str,
    resources: list[InfoSources],
    limit: int = 5,
):
    start_time = time.perf_counter()
    logger.info(f"🔍 Searching for {query} in {resources}")
    # Time bi-encoder encoding
    bi_encoder_start = time.perf_counter()
    if settings.ml_service.infinity_url:
        import src.ml_service.infinity

        query_emb = (
            await src.ml_service.infinity.embed(
                [clean_text(query)],
                task="query",
            )
        )[0]
    else:
        import src.ml_service.non_infinity

        query_emb = (
            await src.ml_service.non_infinity.embed(
                [clean_text(query)],
                task="query",
            )
        )[0]
    bi_encoder_time = time.perf_counter() - bi_encoder_start
    logger.info(f"⏱️  Bi-encoder encoding: {bi_encoder_time:.3f}s")

    all_results = []
    db_query_start = time.perf_counter()
    lance_db = await lancedb.connect_async(settings.ml_service.lancedb_uri)
    for resource in resources:
        resource_start = time.perf_counter()
        tbl_name = f"chunks_{resource}"
        if tbl_name not in await lance_db.table_names():
            continue
        tbl = await lance_db.open_table(tbl_name)
        results: pd.DataFrame = (
            await tbl.query()
            .nearest_to(query_emb)
            .distance_type("cosine")
            # .nearest_to_text(query) TODO: For now it will not work if /tmp and /home are on different partitions: https://github.com/lancedb/lancedb/issues/2461
            .limit(settings.ml_service.bi_encoder_search_limit_per_table)
            .to_pandas()
        )
        resource_time = time.perf_counter() - resource_start
        logger.info(f"⏱️  {resource} query: {resource_time:.3f}s")
        logger.info(f"\nRaw results for {resource}:\n{results.drop(columns=['embedding']).head(3)}")
        for _, row in results.iterrows():
            if "_relevance_score" in row:
                score = row["_relevance_score"]
            elif "_score" in row:
                score = row["_score"]
            elif "_distance" in row:
                score = 1 - row["_distance"]
            else:
                score = 0

            all_results.append(
                {
                    "resource": resource,
                    "mongo_id": row["mongo_id"],
                    "score": score,
                    "content": clean_text(row["content"]),
                }
            )
    db_query_time = time.perf_counter() - db_query_start
    logger.info(f"⏱️  Total database queries: {db_query_time:.3f}s")
    logger.info(f"🔍 Found {len(all_results)} results")

    # Rerank with cross encoder
    cross_encoder_time = 0
    if all_results:
        logger.info("🔄 Reranking with cross encoder...")
        cross_encoder_start = time.perf_counter()
        documents = [result["content"] for result in all_results]

        if settings.ml_service.infinity_url:
            import src.ml_service.infinity

            rankings = await src.ml_service.infinity.rerank(
                clean_text(query),
                documents,
                top_n=limit,
            )
        else:
            import src.ml_service.non_infinity

            rankings = await src.ml_service.non_infinity.rerank(
                clean_text(query),
                documents,
                top_n=limit,
            )

        cross_encoder_time = time.perf_counter() - cross_encoder_start
        logger.info(f"⏱️  Cross-encoder reranking: {cross_encoder_time:.3f}s")

        # Create reranked results based on cross encoder rankings
        reranked_results = []
        for ranking in rankings:
            original_result = all_results[ranking.index]
            reranked_results.append(
                {
                    "resource": original_result["resource"],
                    "mongo_id": original_result["mongo_id"],
                    "score": ranking.relevance_score,
                    "content": clean_text(original_result["content"]),
                }
            )

        all_results = reranked_results
        logger.info(f"🔄 Cross encoder reranking completed for {len(all_results)} results")

    # Deduplicate chunks per document (resource, mongo_id), keep highest bi-encoder score
    unique: dict[tuple[str, str], dict] = {}
    for result in all_results:
        key = (result["resource"], result["mongo_id"])
        # if this document is new or has a higher score than previously seen
        if key not in unique or result["score"] > unique[key]["score"]:
            unique[key] = result
    # rebuild list from map values
    all_results = list(unique.values())
    # sort deduplicated results by score descending
    all_results.sort(key=lambda r: r["score"], reverse=True)

    total_time = time.perf_counter() - start_time
    logger.info(f"⏱️  Total search pipeline: {total_time:.3f}s")
    logger.info(
        f"⏱️  Breakdown: Bi-encoder ({bi_encoder_time:.3f}s) + DB queries ({db_query_time:.3f}s) + Cross-encoder ({cross_encoder_time:.3f}s) = {total_time:.3f}s"
    )

    # Results are already sorted by cross encoder scores (highest first)
    return all_results


if __name__ == "__main__":
    logger.info("📥 Starting search pipeline…")
    q = "How much does room for 2 people rent cost?"
    results = asyncio.run(
        search_pipeline(
            q,
            resources=[
                InfoSources.moodle,
                InfoSources.hotel,
                InfoSources.eduwiki,
                InfoSources.campuslife,
            ],
        )
    )
    for i, r in enumerate(results, 1):
        logger.info(f"{i}. ({r['resource']}) [{r['score']:.3f}]: {r['content']}")
