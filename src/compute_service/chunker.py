from typing import Any

from langchain_text_splitters import TextSplitter
from transformers import BertTokenizerFast
from transformers.tokenization_utils_base import VERY_LARGE_INTEGER


class CustomTokenTextSplitter(TextSplitter):
    """Splitting text to tokens using model tokenizer."""

    def __init__(
        self,
        tokenizer: BertTokenizerFast,
        chunk_size: int,
        **kwargs: Any,
    ) -> None:
        """Create a new TextSplitter."""
        super().__init__(**kwargs, chunk_size=chunk_size)

        self.tokenizer = tokenizer

    def split_text(self, text: str) -> list[str]:
        return split_text_on_tokens(
            text=text, chunk_size=self._chunk_size, chunk_overlap=self._chunk_overlap, tokenizer=self.tokenizer
        )


def split_text_on_tokens(*, text: str, chunk_size: int, chunk_overlap: int, tokenizer: BertTokenizerFast):
    """Split incoming text and return chunks using tokenizer."""
    splits = []
    tokenization = tokenizer(text, add_special_tokens=False, truncation=False, max_length=VERY_LARGE_INTEGER)
    input_ids = tokenization["input_ids"]
    assert len(tokenization.encodings) <= 1, "Should be Only one encoding"
    encodings = tokenization.encodings[0]
    start_idx = 0
    cur_idx = min(start_idx + chunk_size, len(input_ids))

    while start_idx < len(input_ids):
        start, _ = encodings.token_to_chars(start_idx)
        _, end = encodings.token_to_chars(cur_idx - 1)
        splits.append(text[start:end])
        if cur_idx == len(input_ids):
            break
        start_idx += chunk_size - chunk_overlap
        cur_idx = min(start_idx + chunk_size, len(input_ids))

    return splits
