"""Local Tesseract OCR for indexed chat images."""
import asyncio
import csv
import io
import logging
import math
import os
import ssl
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import httpx
from PIL import Image, ImageOps

MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
MAX_SIDE = 2048
MAX_RESPONSE = 256 * 1024
MAX_TEXT = 24000
MAX_IMAGES = 10
JOB_TIMEOUT = 180  # Shorter than the database claim lease; includes all downloads and OCR.
TESSERACT_TIMEOUT = 10
TESSERACT_MAX_STDERR = 16 * 1024
TESSERACT_MIN_WORD_CONFIDENCE = 80
TESSERACT_MIN_MEAN_CONFIDENCE = 90
TESSERACT_MIN_NUMERIC_CONFIDENCE = 90
POLL_SECONDS = 2
log = logging.getLogger("catix.image_ocr")


class _MediaURLFilter(logging.Filter):
    """Redact CDN URLs before HTTPX's request records reach any handler."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                "[media URL redacted]" if isinstance(arg, httpx.URL)
                and any(arg.host.endswith("." + domain) for domain in ("oneme.ru", "okcdn.ru"))
                else arg for arg in record.args
            )
        return True


# Permanent, URL-scoped filtering, not a global level toggle racing concurrent requests.
logging.getLogger("httpx").addFilter(_MediaURLFilter())


class LimitedBuffer(io.BytesIO):
    """Telegram SDK download target: reject excess bytes before allocating them."""
    def write(self, data) -> int:
        if self.tell() + len(data) > MAX_BYTES:
            raise ValueError("Image size limit")
        return super().write(data)


async def download_url(url: str, *, verify: ssl.SSLContext | bool = True) -> bytes:
    """Download a MAX CDN image with no bot credentials, cookies, redirects or environment authentication."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    # MAX's media CDNs, not arbitrary URLs supplied in a chat or an HTML preview.
    if (parts.scheme != "https" or parts.username is not None or parts.password is not None
            or parts.port not in (None, 443) or "#" in url or any(ord(c) <= 32 for c in url)
            or not any(host.endswith("." + domain) for domain in ("oneme.ru", "okcdn.ru"))):
        raise ValueError("Unsupported image URL")
    async with asyncio.timeout(30), httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False,
                                                     verify=verify, headers={"Accept-Encoding": "identity"}) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            if response.headers.get("content-encoding", "identity").lower() != "identity":
                raise ValueError("Unsupported image encoding")
            if int(response.headers.get("content-length", "0")) > MAX_BYTES:
                raise ValueError("Image size limit")
            with LimitedBuffer() as body:
                async for chunk in response.aiter_bytes():
                    body.write(chunk)
                return body.getvalue()


def normalize(data: bytes) -> bytes:
    """Validate a bounded still image and discard metadata; do not reduce screenshots to thumbnails."""
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Image size limit")
    with Image.open(io.BytesIO(data)) as original:
        if (original.format not in {"PNG", "JPEG", "WEBP"} or original.width * original.height > MAX_PIXELS
                or getattr(original, "n_frames", 1) != 1):
            raise ValueError("Unsupported image")
        original.load()
        image = ImageOps.exif_transpose(original).convert("RGB")
        image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
        # A fresh image, not a copy retaining EXIF/ICC/text chunks.
        clean = Image.new("RGB", image.size)
        clean.paste(image)
        output = io.BytesIO()
        clean.save(output, format="PNG")
        return output.getvalue()


def _tesseract_text(tsv: str) -> str:
    """Reject an entire image if any word is uncertain; preserve TSV reading order."""
    fields = ("level", "page_num", "block_num", "par_num", "line_num", "conf", "text")
    words = []
    try:
        reader = csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE, strict=True)
        if not reader.fieldnames or not set(fields) <= set(reader.fieldnames):
            raise ValueError
        if len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError
            level, page, block, paragraph, line = (int(row[field]) for field in fields[:5])
            if not 1 <= level <= 5 or page < 1 or min(block, paragraph, line) < 0:
                raise ValueError
            text = row["text"].strip()
            if level != 5 or not text:
                continue
            if min(block, paragraph, line) < 1:
                raise ValueError
            confidence = float(row["conf"])
            if not math.isfinite(confidence) or not 0 <= confidence <= 100:
                raise ValueError
            words.append(((page, block, paragraph, line), text, confidence))
    except (ValueError, csv.Error):
        raise ValueError("Invalid Tesseract TSV") from None

    if not words or not any(char.isalnum() for _, text, _ in words for char in text):
        return ""
    if (any(conf < TESSERACT_MIN_WORD_CONFIDENCE
            or (any(char.isdigit() for char in text) and conf < TESSERACT_MIN_NUMERIC_CONFIDENCE)
            for _, text, conf in words)
            or sum(conf for _, _, conf in words) / len(words) < TESSERACT_MIN_MEAN_CONFIDENCE):
        return ""
    parts = []
    previous = None
    for position, text, _ in words:
        if previous is not None:
            parts.append("\n\n" if position[:3] != previous[:3] else "\n" if position != previous else " ")
        parts.append(text)
        previous = position
    result = "".join(parts)
    return result if len(result) <= MAX_TEXT else ""


class _ComplexImage(Exception):
    """OCR exceeded the work budget; the image can be skipped without retry."""


async def _read_tesseract(stream: asyncio.StreamReader, limit: int, *, stdout: bool) -> bytes:
    body = bytearray()
    while chunk := await stream.read(min(8192, limit + 1 - len(body))):
        if len(body) + len(chunk) > limit:
            if stdout:
                raise _ComplexImage
            raise ValueError("Tesseract stderr limit")
        body.extend(chunk)
    return bytes(body)


async def _write_tesseract(stream: asyncio.StreamWriter, png: bytes) -> None:
    try:
        stream.write(png)
        await stream.drain()
    except (BrokenPipeError, ConnectionResetError):
        pass  # A failed executable can close stdin before consuming the image.
    finally:
        stream.close()


async def _cleanup_tesseract(spawn: asyncio.Task, tasks: list[asyncio.Task]) -> None:
    try:
        process = await spawn
    except Exception:
        return
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass  # Natural exit raced the kill.
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    async def drain(stream):
        while await stream.read(8192):
            pass

    # Drain residual pipe buffers so a paused transport cannot prevent wait() from completing.
    await asyncio.gather(drain(process.stdout), drain(process.stderr), process.wait())


async def transcribe(data: bytes) -> str:
    png = await asyncio.to_thread(normalize, data)
    spawn = asyncio.create_task(asyncio.create_subprocess_exec(
        "tesseract", "stdin", "stdout", "-l", "rus+eng", "--psm", "3", "tsv",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    ))
    tasks = []
    try:
        async with asyncio.timeout(TESSERACT_TIMEOUT):
            process = await asyncio.shield(spawn)
            tasks = [
                asyncio.create_task(_write_tesseract(process.stdin, png)),
                asyncio.create_task(_read_tesseract(process.stdout, MAX_RESPONSE, stdout=True)),
                asyncio.create_task(_read_tesseract(process.stderr, TESSERACT_MAX_STDERR, stdout=False)),
                asyncio.create_task(process.wait()),
            ]
            _, stdout, stderr, code = await asyncio.gather(*tasks)
            # Tesseract can exit 0 with only one of the requested languages loaded.
            if code or b"Failed loading language" in stderr or b"Error opening data file" in stderr:
                raise ValueError("Tesseract failed")
        return _tesseract_text(stdout.decode("utf-8"))
    except (TimeoutError, _ComplexImage):
        return ""
    except (OSError, UnicodeError):
        raise ValueError("Tesseract unavailable or invalid output") from None
    finally:
        cleanup = asyncio.create_task(_cleanup_tesseract(spawn, tasks))
        # Explicit cancellation must propagate only after the child and all I/O have stopped.
        cancelled = False
        while not cleanup.done():
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                cancelled = True
        cleanup.result()
        if cancelled:
            raise asyncio.CancelledError


async def database_call(function, *args, **kwargs):
    """Cancellation must not outlive a SQL thread when the worker closes its DB pool."""
    operation = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    try:
        return await asyncio.shield(operation)
    except asyncio.CancelledError:
        while not operation.done():
            try:
                await asyncio.shield(operation)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if not operation.cancelled():
            operation.exception()
        raise


async def process(job: dict, download: Callable[[dict, str], Awaitable[bytes]],
                  allowed: Callable[[dict], Awaitable[bool]] | None = None) -> bool:
    """Complete only this version/claim; a failed or incomplete reading never becomes indexed text."""
    from catix.ingest import image_queue, publish

    try:
        async with asyncio.timeout(JOB_TIMEOUT):
            if allowed is not None and not await allowed(job):
                await database_call(image_queue.discard, job)
                return False
            refs = job["refs"]
            if not 1 <= len(refs) <= MAX_IMAGES:
                raise ValueError("Image count limit")
            texts = []
            for n, ref in enumerate(refs, 1):
                text = await transcribe(await download(job, ref))
                if text:
                    texts.append(f"[image {n}]\n{text}" if len(refs) > 1 else text)
            text = "\n\n".join(texts)
            if len(text) > MAX_TEXT:
                raise ValueError("OCR text limit")
            if allowed is not None and not await allowed(job):
                await database_call(image_queue.discard, job)
                return False
            stored = await database_call(image_queue.finish, job, text)
    except Exception:
        # Download exceptions may contain bot tokens, signed URLs or private message contents.
        log.warning("image OCR failed for message %s; recording bounded retry", job["message_id"])
        await database_call(image_queue.fail, job)
        return False
    if stored and job.get("image_source") != "maxuserbot":
        # The database embedding trigger is authoritative even when the optional Redis stream is unavailable.
        try:
            await publish.publish([(job["chat_id"], job["msg_id"])])
        except Exception:
            log.warning("OCR saved for message %s; stream notification unavailable", job["message_id"])
    return stored


async def run(source: str, download: Callable[[dict, str], Awaitable[bytes]],
              allowed: Callable[[dict], Awaitable[bool]] | None = None) -> None:
    """One globally leased image job at a time, across all messenger processes. Restarts resume the DB queue."""
    from catix.ingest import image_queue

    while True:
        try:
            job = await database_call(image_queue.claim, source)
            if job is not None:
                await process(job, download, allowed)
                continue
        except Exception:
            log.warning("image OCR queue unavailable for %s", source)
        await asyncio.sleep(POLL_SECONDS)
