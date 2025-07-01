import re

_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(text: str) -> str:
    no_tags = _TAG_RE.sub("", text)

    return no_tags.strip()
