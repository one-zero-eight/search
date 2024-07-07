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
from pydantic import ValidationError, TypeAdapter
from pymupdf4llm.to_markdown import Output
from sentence_transformers import SentenceTransformer

from src.config import settings
from src.modules.compute.schemas import Result, Task, TaskAdapter, PdfTask, SearchTask


def get_client() -> httpx.Client:
    return httpx.Client(
        base_url=f"{settings.compute_settings.api_url}/compute",
        headers={"Authorization": f"Bearer {settings.compute_settings.auth_token}"},
    )


def fetch_tasks() -> list[Task]:
    with get_client() as session:
        response = session.get("/tasks/pending")
        response.raise_for_status()
        tasks_data = response.json()

    tasks = []
    for task_data in tasks_data:
        try:
            task = TaskAdapter.validate_python(task_data)
            tasks.append(task)
        except ValidationError as e:
            print(f"Validation error: {e}")
    return tasks


def process_task(task: Task) -> None:
    # Simulate task processing
    print(f"Processing task {task.id} of type {task.type}")
    time.sleep(1)  # Simulate time taken to process the task

    # Create a result
    result = Result(
        task_id=task.id, task_type=task.type, status="completed", result={"message": f"Processed task {task.id}"}
    )
    type_adapter = TypeAdapter(list[Result])

    # Post result to the API
    try:
        with get_client() as session:
            response = session.post("/tasks/completed", json=type_adapter.dump_python([result]))
            response.raise_for_status()
            print(f"Task {task.id} result stored successfully")
    except httpx.HTTPStatusError as e:
        print(f"Failed to store result for task {task.id}: {e}")


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


def output_to_chunks(output: Output, splitter) -> list[Chunk]:
    chunks: list[Chunk] = []

    for i, page_chunk in enumerate(output["page_chunks"]):
        page_text = to_plain_text(page_chunk["text"])
        splitted = splitter.split_text(page_text)
        for text in splitted:
            chunks.append({"text": text, "page_number": i})
    return chunks


def file_pipeline(file_uri, splitter, model):
    doc = get_document_from_url(file_uri)
    output = pdf_to_pages(doc)
    chunks = output_to_chunks(output, splitter)
    embeddings = model.encode([chunk["text"] for chunk in chunks])
    return output, chunks, embeddings


def pdf_to_text_worker(namespace):
    print("[PDF-Text worker]: Started")

    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    CHUNK_OVERLAP = 25
    model = SentenceTransformer(MODEL_NAME)
    chunk_splitter = SentenceTransformersTokenTextSplitter(model_name=MODEL_NAME, chunk_overlap=CHUNK_OVERLAP)

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
            _results = pool.map(
                partial(file_pipeline, splitter=chunk_splitter, model=model), [task.pdf_url for task in pack]
            )


def fetcher(namespace):
    print(f"Fetch tasks from API every {settings.compute_settings.period} seconds")
    while True:
        tasks = fetch_tasks()
        print(f"Populated by {len(tasks)} tasks")
        for task in tasks:
            if isinstance(task, SearchTask):
                namespace.search_queue: multiprocessing.Queue
                namespace.search_queue.put_nowait(task)
            elif isinstance(task, PdfTask):
                namespace.pdf_processor_queue: multiprocessing.Queue
                namespace.pdf_processor_queue.put_nowait(task)

        # Wait for the specified period before fetching tasks again
        time.sleep(settings.compute_settings.period)


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
