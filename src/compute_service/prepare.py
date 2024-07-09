import re
import time
from functools import partial
from multiprocessing import Pool
from typing import TypedDict

import httpx
import pymupdf
import pymupdf4llm
from langchain_text_splitters import SentenceTransformersTokenTextSplitter
from pymupdf4llm.to_markdown import Output
from retriv import HybridRetriever

from src.config import settings
from src.modules.compute.schemas import Corpora
from src.modules.minio.schemas import MoodleFileObject

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_OVERLAP = 25
chunk_splitter = SentenceTransformersTokenTextSplitter(model_name=MODEL_NAME, chunk_overlap=CHUNK_OVERLAP)
maximum_tokens_per_chunk = chunk_splitter.maximum_tokens_per_chunk
hybrid_retriever = HybridRetriever("innohassle-search", max_length=maximum_tokens_per_chunk, dr_model=MODEL_NAME)


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
    with httpx.Client() as session:
        response = session.get(file_uri)
        response.raise_for_status()

        doc = pymupdf.Document(stream=response.stream)
        return doc


def pdf_to_pages(doc: pymupdf.Document) -> Output:
    return pymupdf4llm.process_document(doc)


class Chunk(TypedDict):
    text: str
    page_number: int


def to_plain_text(text: str) -> str:
    # remove html tags
    text = re.sub(r"<[^>]*>", "", text)
    return text


def output_to_chunks(output: Output) -> list[Chunk]:
    chunks: list[Chunk] = []

    for i, page_chunk in enumerate(output["page_chunks"]):
        page_text = to_plain_text(page_chunk["text"])
        splitted = chunk_splitter.split_text(page_text)
        for text in splitted:
            chunks.append({"text": text, "page_number": i})
    return chunks


def file_pipeline(file_uri):
    doc = get_document_from_url(file_uri)
    output = pdf_to_pages(doc)
    chunks = output_to_chunks(output)
    return output, chunks


def moodle_file_object_to_url(obj: MoodleFileObject) -> str:
    return f"{settings.compute_settings.api_url}/moodle/preview?course_id={obj.course_id}&module_id={obj.module_id}&filename={obj.filename}"


def pdf_to_text_job(corpora: Corpora):
    pdf_urls = [moodle_file_object_to_url(obj) for obj in corpora.moodle_files]

    print(f"[PDF-Text worker]: Processing {len(pdf_urls)} items")

    with Pool(processes=settings.compute_settings.num_workers) as pool:
        _results = pool.map(partial(file_pipeline, splitter=chunk_splitter), pdf_urls)


def main():
    print(f"Fetch tasks from API every {settings.compute_settings.check_search_queue_period} seconds")
    prev_corpora = None
    while True:
        corpora = fetch_corpora()
        if prev_corpora != corpora:
            print(f"Populated by {len(corpora.moodle_files)} corpora entries")
            pdf_to_text_job(corpora)
            prev_corpora = corpora
        else:
            print("No corpora changes")

        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.corpora_update_period)


if __name__ == "__main__":
    main()
