from typing import Literal

import numpy as np
from infinity_client import Client
from infinity_client.api.default import embeddings
from infinity_client.api.default import rerank as infinity_rerank
from infinity_client.models import (
    OpenAIEmbeddingInputText,
    OpenAIEmbeddingResult,
    RerankInput,
    ReRankObject,
    ReRankResult,
)

from src.config import settings
from src.ml_service.config import settings as ml_settings

i_client = Client(base_url=settings.ml_service.infinity_url)

task_prefix = {
    "query": "Represent the query for retrieving evidence documents: ",
    "passage": "Represent the document for retrieval: ",
}


async def embed(texts: list[str], task: Literal["query", "passage"] | None = None) -> list[np.ndarray]:
    prefix = task_prefix[task] if task else ""
    embeds: OpenAIEmbeddingResult = await embeddings.asyncio(
        client=i_client,
        body=OpenAIEmbeddingInputText.from_dict(
            {
                "input": [f"{prefix}{text}" for text in texts],
                "model": settings.ml_service.bi_encoder,
                "dimensions": ml_settings.LANCEDB_EMBEDDING_DIM,
            }
        ),
    )
    query_emb = [np.array(emb.to_dict()["embedding"]) for emb in embeds.data]
    return query_emb


async def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[ReRankObject]:
    reranks: ReRankResult = await infinity_rerank.asyncio(
        client=i_client,
        body=RerankInput.from_dict(
            {
                "query": query,
                "documents": documents,
                "top_n": top_n,
                "model": settings.ml_service.cross_encoder,
            }
        ),
    )
    return reranks.results
