import asyncio
import re

import lancedb
import pandas as pd
from sentence_transformers import SentenceTransformer

from src.ml_service.config import settings
from src.ml_service.text import clean_text
from src.modules.sources_enum import InfoSources

bi_encoder = SentenceTransformer(settings.BI_ENCODER_MODEL, device=settings.DEVICE)


async def search_pipeline(
    query: str,
    resources: list[InfoSources],
    return_chunks: bool = False,
    limit: int = 5,
):
    query_emb = bi_encoder.encode(clean_text(query), convert_to_numpy=True)
    print("Query embedding (first 5 dims):", query_emb[:5], "…")
    all_results = []
    lance_db = await lancedb.connect_async(settings.LANCEDB_URI)
    for resource in resources:
        tbl_name = f"chunks_{resource}"
        if tbl_name not in await lance_db.table_names():
            continue
        tbl = await lance_db.open_table(tbl_name)
        results: pd.DataFrame = (
            await tbl.query()
            .nearest_to(query_emb)
            .distance_type("cosine")
            .nearest_to_text(query)
            .limit(limit)
            .to_pandas()
        )
        print(f"\nRaw results for {resource}:")
        print(results.head())
        for _, row in results.iterrows():
            snippet = row["content"]
            snippet = re.sub(r"#{2,}\s*", "", snippet)
            all_results.append(
                {
                    "resource": resource,
                    "mongo_id": row["mongo_id"],
                    "score": 1 - row["_distance"],
                    "snippet": snippet,
                }
            )
    print(len(all_results), "is length of results")
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:limit] if not return_chunks else all_results[:limit]


if __name__ == "__main__":
    print("📥 Starting search pipeline…")
    q = "How much does room for 2 people rent cost?"
    results = asyncio.run(
        search_pipeline(
            q, resources=[InfoSources.moodle, InfoSources.hotel, InfoSources.eduwiki, InfoSources.campuslife]
        )
    )
    for i, r in enumerate(results, 1):
        print(f"{i}. ({r['resource']}) [{r['score']:.3f}]: {r['snippet']}")
