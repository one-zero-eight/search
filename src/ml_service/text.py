import re


def clean_text(text: str) -> str:
    """
    Simple cleaning: lowercase, collapse whitespace, strip.
    """
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()
