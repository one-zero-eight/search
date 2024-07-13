from typing import Any, List

from langchain_text_splitters import TextSplitter, split_text_on_tokens
from transformers import BertTokenizerFast


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

    def split_text(self, text: str) -> List[str]:
        from langchain_text_splitters import Tokenizer

        def _encode(_text: str) -> List[int]:
            return self.tokenizer.encode(
                _text, add_special_tokens=False, truncation=False, max_length=1_000_000
            )  # unlimited length to suppress warning

        tokenizer = Tokenizer(
            chunk_overlap=self._chunk_overlap,
            tokens_per_chunk=self._chunk_size,
            decode=self.tokenizer.decode,
            encode=_encode,
        )

        return split_text_on_tokens(text=text, tokenizer=tokenizer)
