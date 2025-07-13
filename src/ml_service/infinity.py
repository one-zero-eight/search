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

i_client = Client(base_url=settings.ml_service.infinity_url)

task_prefix = {
    "jinaai/jina-embeddings-v3": {
        "query": "Represent the query for retrieving evidence documents: ",
        "passage": "Represent the document for retrieval: ",
    },
    "intfloat/multilingual-e5-large-instruct": {
        "query": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",
        "passage": "",
    },
}


async def embed(texts: list[str], task: Literal["query", "passage"]) -> list[np.ndarray]:
    prefix = task_prefix[settings.ml_service.bi_encoder][task]
    embeds: OpenAIEmbeddingResult = await embeddings.asyncio(
        client=i_client,
        body=OpenAIEmbeddingInputText.from_dict(
            {
                "input": [f"{prefix}{text}" for text in texts],
                "model": settings.ml_service.bi_encoder,
                "dimensions": settings.ml_service.bi_encoder_dim,
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
