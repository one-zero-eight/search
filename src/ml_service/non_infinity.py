from dataclasses import dataclass
from typing import Literal

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder

from src.config import settings

bi_encoder = SentenceTransformer(
    settings.ml_service.bi_encoder,
    trust_remote_code=True,
    truncate_dim=settings.ml_service.bi_encoder_dim,
)
cross_encoder = CrossEncoder(
    settings.ml_service.cross_encoder,
    model_kwargs={"torch_dtype": "auto"},
    trust_remote_code=True,
    device="cuda" if torch.cuda.is_available() else "cpu",
)

model_x_task = {
    "jinaai/jina-embeddings-v3": {
        "query": "retrieval.query",
        "passage": "retrieval.passage",
    }
}

task_prefix = {
    "intfloat/multilingual-e5-large-instruct": {
        "query": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",
        "passage": "",
    },
}


async def embed(texts: list[str], task: Literal["query", "passage"]) -> list[np.ndarray]:
    prefix = task_prefix.get(settings.ml_service.bi_encoder, {}).get(task)
    if prefix:
        texts = [f"{prefix}{text}" for text in texts]
    task = model_x_task.get(settings.ml_service.bi_encoder, {}).get(task)
    return bi_encoder.encode(texts, convert_to_numpy=True, task=task, prompt_name=task)


@dataclass
class Ranking:
    index: int
    relevance_score: float


async def rerank(query: str, documents: list[str], top_n: int | None = None) -> list[Ranking]:
    rankings = cross_encoder.rank(query, documents, return_documents=True, convert_to_tensor=False)
    return [Ranking(index=ranking["corpus_id"], relevance_score=ranking["score"]) for ranking in rankings][:top_n]
