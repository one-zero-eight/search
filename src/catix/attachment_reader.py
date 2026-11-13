"""Isolated attachment decoder. Only the parent chooses its paths and arguments."""
import io
import json
import os
import re
import resource
import subprocess
import sys
import unicodedata
from collections import Counter
from pathlib import Path

MAX_BYTES = 10 * 1024 * 1024
MAX_TEXT = 60_000
MAX_PIXELS = 40_000_000
IMAGE_FORMATS = {".png": ("PNG", "image/png"), ".jpg": ("JPEG", "image/jpeg"),
                 ".jpeg": ("JPEG", "image/jpeg"), ".webp": ("WEBP", "image/webp")}


def _image(data: bytes, suffix: str):
    from PIL import Image, ImageOps
    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    im = Image.open(io.BytesIO(data))
    if im.format != IMAGE_FORMATS[suffix][0] or im.width * im.height > MAX_PIXELS or getattr(im, "n_frames", 1) != 1:
        raise ValueError("image limits/format")
    im.verify()  # validate container checksums/trailer as well as decodable pixels
    im = Image.open(io.BytesIO(data))
    im.load()
    return ImageOps.exif_transpose(im)


def _png(im) -> bytes:
    from PIL import Image
    # 1000x1000 is an upper bound even for very unusual aspect ratios.
    im.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    rgba = im.convert("RGBA")
    background = Image.new("RGBA", rgba.size, "white")
    Image.alpha_composite(background, rgba).convert("RGB").save(out, format="PNG")
    return out.getvalue()


def _pdf(data: bytes):
    import pdfplumber
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-1024:]:
        raise ValueError("PDF structure")
    pdf = pdfplumber.open(io.BytesIO(data), strict_metadata=True)
    if pdf.doc.encryption or not 1 <= len(pdf.pages) <= 20:
        pdf.close()
        raise ValueError("encrypted PDF or page limit")
    return pdf


def _page_nodes(nodes: list[dict], page: int, inherited: int | None = None) -> list[dict]:
    result = []
    for node in nodes:
        number = node.get("page number", inherited)
        if number is None or not isinstance(number, int):
            raise ValueError("missing page attribution")
        copy = dict(node)
        for key in ("kids", "list items", "rows", "cells"):
            if key in node:
                copy[key] = _page_nodes(node[key] or [], page, number)
        if number == page or any(copy.get(key) for key in ("kids", "list items", "rows", "cells")):
            if number != page:
                copy.pop("content", None)
            result.append(copy)
    return result


def _pdf_text(data: bytes) -> dict:
    import opendataloader_pdf
    from contextlib import redirect_stdout, redirect_stderr
    from catix.wiki.sources.opendataloader import text_of

    with _pdf(data) as pdf:
        count = len(pdf.pages)
        # pdfplumber is only a completeness check, never a text fallback.
        # Conservatively flag even intentional ODL omissions (e.g. page-number footers).
        source_chars = [Counter(c for c in unicodedata.normalize("NFKC", "".join(ch["text"] for ch in p.chars))
                                if not c.isspace()) for p in pdf.pages]
    path = Path("input.pdf")
    path.write_bytes(data)
    os.environ["JAVA_TOOL_OPTIONS"] = (
        "-Xmx384m -Xms32m -Xss512k -XX:+UseSerialGC -XX:ActiveProcessorCount=2 "
        "-XX:ReservedCodeCacheSize=64m -XX:CompressedClassSpaceSize=64m "
        "-XX:MaxMetaspaceSize=192m -XX:-UsePerfData -XX:ErrorFile=/dev/null"
    )
    # ODL's Python wrapper can relay parser output: never put that in our protocol/logs.
    with open(os.devnull, "w") as sink, redirect_stdout(sink), redirect_stderr(sink):
        opendataloader_pdf.convert(input_path=str(path), output_dir=".", format="json", image_output="off",
                                   quiet=True, keep_line_breaks=True, include_header_footer=True, threads="1",
                                   content_safety_off="off-page")
    doc = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
    if doc.get("number of pages") != count or not isinstance(doc.get("kids"), list):
        raise ValueError("incomplete extraction")
    pages = []
    for page in range(1, count + 1):
        text = text_of({"kids": _page_nodes(doc["kids"], page)}, known=frozenset())
        extracted = Counter(c for c in unicodedata.normalize("NFKC", text) if not c.isspace())
        incomplete = bool(source_chars[page - 1] - extracted)
        item = {"text": text[:MAX_TEXT], "truncated": len(text) > MAX_TEXT or incomplete}
        if incomplete:
            item["note"] = "Text extraction was incomplete; view the page image."
        elif not text.strip():
            item["note"] = "No extractable text on this page; it may be scanned or blank. View the page image; no OCR was performed."
        pages.append(item)
    return {"media_type": "application/pdf", "pages": pages}


def render(data: bytes, suffix: str, page: int) -> bytes:
    if suffix in IMAGE_FORMATS and page == 1:
        return _png(_image(data, suffix))
    if suffix == ".pdf":
        from PIL import Image
        with _pdf(data) as pdf:
            if not 1 <= page <= len(pdf.pages):
                raise ValueError("page")
        Path("input.pdf").write_bytes(data)
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-scale-to", "1000",
                        "-png", "input.pdf", "page"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with Image.open("page.png") as im:
            return _png(im)
    raise ValueError("page or format")


def extract(data: bytes, suffix: str) -> dict:
    if suffix == ".pdf":
        return _pdf_text(data)
    if suffix in IMAGE_FORMATS:
        _image(data, suffix)
        return {"media_type": IMAGE_FORMATS[suffix][1], "pages": [
            {"text": "", "truncated": False, "note": "Image page; no text extraction or OCR was performed. View the page image."}]}
    if suffix != ".txt":
        raise ValueError("format")
    text = data.decode("utf-8-sig")
    if (any(ord(c) < 32 and c not in "\t\r\n" for c in text)
            or re.search(r"<\s*(?:!doctype|html|head|body|script|svg|\?xml)\b", text, re.I)):
        raise ValueError("not plain text")
    return {"media_type": "text/plain", "pages": [{"text": text[:MAX_TEXT], "truncated": len(text) > MAX_TEXT}]}


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
    resource.setrlimit(resource.RLIMIT_FSIZE, (32 * 1024**2, 32 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    data = sys.stdin.buffer.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("size")
    page = int(sys.argv[2])
    output = render(data, sys.argv[1], page) if page else json.dumps(extract(data, sys.argv[1])).encode()
    sys.stdout.buffer.write(output)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never disclose file content, filenames, parser diagnostics, or local paths.
        sys.exit(1)
