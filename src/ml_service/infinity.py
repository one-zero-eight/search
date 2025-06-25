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


async def embed(texts: list[str]) -> list[np.ndarray]:
    with i_client as client:
        embeds: OpenAIEmbeddingResult = await embeddings.asyncio(
            client=client,
            body=OpenAIEmbeddingInputText.from_dict({"input": texts, "model": settings.ml_service.bi_encoder}),
        )
        query_emb = [np.array(emb.to_dict()["embedding"]) for emb in embeds.data]
        return query_emb


async def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[ReRankObject]:
    with i_client as client:
        reranks: ReRankResult = await infinity_rerank.asyncio(
            client=client,
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
