import multiprocessing
import queue
import re
import time
from functools import partial
from multiprocessing import Pool, Manager, Process
from typing import TypedDict

import httpx
import pymupdf
import pymupdf4llm
from langchain_text_splitters import SentenceTransformersTokenTextSplitter
from pymupdf4llm.to_markdown import Output
from retriv import HybridRetriever

from src.config import settings

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


def fetch_corpora():
    with get_client() as session:
        response = session.get("/corpora")
        response.raise_for_status()
        corpora_data = response.json()
    return corpora_data


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


def pdf_to_text_worker(namespace):
    print("[PDF-Text worker]: Started")

    while True:
        pack = []
        while True:
            try:
                namespace.pdf_processor_queue: multiprocessing.Queue
                task = namespace.pdf_processor_queue.get_nowait()
                pack.append(task)
            except queue.Empty:
                break

        if not pack:
            print("[PDF-Text worker]: Idle")
            time.sleep(1)  # Avoid busy waiting
            continue
        else:
            print(f"[PDF-Text worker]: Processing {len(pack)} items")

        with Pool(processes=settings.compute_settings.num_workers) as pool:
            _results = pool.map(partial(file_pipeline, splitter=chunk_splitter), [task.pdf_url for task in pack])


def fetcher(namespace):
    print(f"Fetch tasks from API every {settings.compute_settings.check_search_queue_period} seconds")
    while True:
        corpora = fetch_corpora()
        print(f"Populated by {len(corpora)} corpora entries")
        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.corpora_update_period)


def main():
    with Manager() as manager:
        namespace = manager.Namespace()
        namespace.search_queue = manager.Queue()
        namespace.pdf_processor_queue = manager.Queue()

        # spawn fetcher
        fetcher_process = Process(target=fetcher, args=(namespace,))
        pdf_to_text_process = Process(target=pdf_to_text_worker, args=(namespace,))
        fetcher_process.start()
        pdf_to_text_process.start()
        fetcher_process.join()
        pdf_to_text_process.join()


if __name__ == "__main__":
    main()
