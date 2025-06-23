import re


def sentence_chunker(text: str) -> list[str]:
    """
    Splits text into sentences. Each sentence ends with its punctuation (., !, ?).
    """
    pattern = re.compile(r"[^.!?]*[.!?]")
    matches = pattern.findall(text)
    return [m.strip() for m in matches if m.strip()]
