import json
import logging
import re
import time
from typing import TypedDict

import httpx
import pymupdf
import pymupdf4llm
from langchain_text_splitters import SentenceTransformersTokenTextSplitter
from retriv import DenseRetriever

from src.config import settings
from src.modules.compute.schemas import Corpora
from src.modules.minio.schemas import MoodleFileObject

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("compute.prepare")

_1 = time.monotonic()
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_OVERLAP = 25
chunk_splitter = SentenceTransformersTokenTextSplitter(model_name=MODEL_NAME, chunk_overlap=CHUNK_OVERLAP)
maximum_tokens_per_chunk = chunk_splitter.maximum_tokens_per_chunk
dense_retriever = DenseRetriever(
    "innohassle-search", max_length=maximum_tokens_per_chunk, model=MODEL_NAME, use_ann=False
)
_2 = time.monotonic()

logger.info(f"DenseRetriever loaded in {_2 - _1:.2f} seconds")


def get_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    )


def fetch_corpora() -> Corpora:
    with get_client() as session:
        response = session.get("/corpora")
        response.raise_for_status()
        corpora_data = response.json()
        corpora = Corpora.model_validate(corpora_data)
    return corpora


def get_document_from_url(file_uri: str) -> pymupdf.Document:
    with get_client() as session:
        response = session.get(file_uri)
        response.raise_for_status()

        doc = pymupdf.Document(stream=response.content)
        return doc


class Chunk(TypedDict):
    text: str
    page_number: int


def to_plain_text(text: str) -> str:
    # remove html tags
    text = re.sub(r"<[^>]*>", "", text)
    return text


def file_pipeline(file_uri, id_kwargs):
    doc = get_document_from_url(file_uri)
    output = pymupdf4llm.process_document(doc)
    doc.close()
    chunks = []
    for i, page_chunk in enumerate(output["page_chunks"]):
        page_text = to_plain_text(page_chunk["text"])
        splitted = chunk_splitter.split_text(page_text)
        for j, text in enumerate(splitted):
            key = json.dumps({**id_kwargs, "page_number": i, "chunk_number": j})
            chunks.append({"text": text, "id": key})

    return chunks


def moodle_file_object_to_url(obj: MoodleFileObject) -> str:
    return f"{settings.compute_settings.api_url}/moodle/preview?course_id={obj.course_id}&module_id={obj.module_id}&filename={obj.filename}"


def pdf_to_text_job(corpora: Corpora):
    items = [moodle_file_object_to_url(obj) for obj in corpora.moodle_files]

    logger.info(f"[PDF-Text worker]: Processing {len(items)} items")
    collection = []

    _1 = time.monotonic()
    for url, obj in zip(items, corpora.moodle_files):
        if obj.filename.endswith(".pdf"):
            file_chunks = file_pipeline(
                url, {"course_id": obj.course_id, "module_id": obj.module_id, "filename": obj.filename}
            )
            collection.extend(file_chunks)
    _2 = time.monotonic()
    logger.info(f"[PDF-Text worker]: Processed {len(collection)} chunks in {_2 - _1:.2f} seconds")

    _1 = time.monotonic()
    dense_retriever.index(collection, use_gpu=True, show_progress=False)
    _2 = time.monotonic()
    logger.info(f"[PDF-Text worker]: Indexed {len(collection)} chunks in {_2 - _1:.2f} seconds")


def no_corpora_changes(prev_corpora: Corpora | None, corpora: Corpora) -> bool:
    if prev_corpora is None:
        return False
    prev_moodle_files = prev_corpora.moodle_files
    corpora_moodle_files = corpora.moodle_files

    _prev = [_.model_dump(exclude={"minio_data"}) for _ in prev_moodle_files]
    _curr = [_.model_dump(exclude={"minio_data"}) for _ in corpora_moodle_files]
    return _prev == _curr


def main():
    logger.info(f"Fetch corpora from API every {settings.compute_settings.corpora_update_period} seconds")
    prev_corpora = None
    while True:
        corpora = fetch_corpora()

        if no_corpora_changes(prev_corpora, corpora):
            logger.info("No corpora changes")
        else:
            logger.info(f"Populated by {len(corpora.moodle_files)} corpora entries")
            pdf_to_text_job(corpora)
            prev_corpora = corpora

        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.corpora_update_period)


if __name__ == "__main__":
    main()
