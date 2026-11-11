"""Isolated reader of a course file a user uploaded (moodle_files.read_file runs it). Only the parent chooses its arguments.

argv[1] is the file's suffix, stdin its bytes; stdout is one JSON object {"text", "method", "pages", "skipped"}. Exit 75:
the OCR server did not answer (retry later); any other failure exits 1 without saying anything about the file."""

import io
import json
import resource
import sys
from pathlib import Path

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 40_000_000
AWAY = 75
IMAGE_FORMATS = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".webp": "WEBP"}
OFFICE = {".doc", ".docx", ".rtf", ".odt", ".ppt", ".pptx", ".odp", ".xls", ".xlsx", ".ods"}


def _image(data: bytes, suffix: str):
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    im = Image.open(io.BytesIO(data))
    if im.format != IMAGE_FORMATS[suffix] or im.width * im.height > MAX_PIXELS or getattr(im, "n_frames", 1) != 1:
        raise ValueError("image limits/format")
    im.verify()
    im = Image.open(io.BytesIO(data))
    im.load()
    return ImageOps.exif_transpose(im)


def _plain(data: bytes) -> dict:
    text = data.decode("utf-8-sig")
    if any(ord(c) < 32 and c not in "\t\r\n" for c in text):
        raise ValueError("not plain text")
    return {"text": text, "method": "plain text", "pages": 1}


def _ocr_image(data: bytes, suffix: str) -> dict:
    import httpx
    from PIL import Image

    from catix.docs.sources import lighton

    im = _image(data, suffix)
    rgba = im.convert("RGBA")
    Image.alpha_composite(Image.new("RGBA", rgba.size, "white"), rgba).convert("RGB").save("page.png", format="PNG")
    if not lighton.available():
        sys.exit(AWAY)
    try:
        markdown = lighton.read_page(Path("page.png"))
    except httpx.HTTPError:
        if not lighton.available():
            sys.exit(AWAY)
        raise
    return {"text": lighton.text_of_pages([markdown]), "method": lighton.METHOD, "pages": 1}


def _pdf(pdf: Path) -> dict:
    from catix.docs.sources import regulations

    pages = regulations.pages_of(pdf)
    if pages > regulations.MAX_PAGES:
        return {"text": None, "method": "", "pages": pages, "skipped": f"more than {regulations.MAX_PAGES} pages"}
    layer = regulations.layer_text(pdf)
    if layer is not None:
        return {"text": layer[0], "method": layer[1], "pages": pages}
    if pages > regulations.MAX_OCR_PAGES:
        return {"text": None, "method": "", "pages": pages, "skipped": "scan too long for OCR"}
    try:
        text, method = regulations.ocr_text(pdf)
    except regulations.NotRead as e:
        if e.away:
            sys.exit(AWAY)
        raise
    return {"text": text, "method": method, "pages": pages}


def read(data: bytes, suffix: str) -> dict:
    if suffix in (".txt", ".md"):
        return _plain(data)
    if suffix in IMAGE_FORMATS:
        return _ocr_image(data, suffix)
    if suffix != ".pdf" and suffix not in OFFICE:
        raise ValueError("format")
    path = Path(f"input{suffix}")
    path.write_bytes(data)
    if suffix in OFFICE:
        from catix.docs.sources import regulations

        path = regulations.to_pdf(path)
        if not path.exists():
            raise ValueError("conversion")
    return _pdf(path)


def main() -> None:
    resource.setrlimit(resource.RLIMIT_AS, (4 * 1024**3, 4 * 1024**3))
    resource.setrlimit(resource.RLIMIT_CPU, (1200, 1200))
    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024**2, 512 * 1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE, (1024, 1024))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    data = sys.stdin.buffer.read(MAX_BYTES + 1)
    if not data or len(data) > MAX_BYTES:
        raise ValueError("size")
    # Imported modules may print (tracing banner): only the result goes to the real stdout.
    out, sys.stdout = sys.stdout, sys.stderr
    out.write(json.dumps(read(data, sys.argv[1])))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # Never disclose file content, filenames, parser diagnostics, or local paths.
        sys.exit(1)
