import string
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Union

import mmh3
import Stemmer
from nltk import NLTKWordTokenizer
from nltk.corpus import stopwords
from qdrant_client.uploader.uploader import iter_batch
from qdrant_client.models import SparseVector


class Bm25:
    """Implements traditional BM25 in a form of sparse embeddings.
    Uses a count of tokens in the document to evaluate the importance of the token.

    WARNING: This model is expected to be used with `modifier="idf"` in the sparse vector index of Qdrant.

    BM25 formula:

    score(q, d) = SUM[ IDF(q_i) * (f(q_i, d) * (k + 1)) / (f(q_i, d) + k * (1 - b + b * (|d| / avg_len))) ],

    where IDF is the inverse document frequency, computed on Qdrant's side
    f(q_i, d) is the term frequency of the token q_i in the document d
    k, b, avg_len are hyperparameters, described below.

    Args:
        k (float, optional): The k parameter in the BM25 formula. Defines the saturation of the term frequency.
            I.e. defines how fast the moment when additional terms stop to increase the score. Defaults to 1.2.
        b (float, optional): The b parameter in the BM25 formula. Defines the importance of the document length.
            Defaults to 0.75.
        avg_len (float, optional): The average length of the documents in the corpus. Defaults to 256.0.
    Raises:
        ValueError: If the model_name is not in the format <org>/<model> e.g. BAAI/bge-base-en.
    """

    def __init__(self, k: float = 1.2, b: float = 0.75, avg_len: float = 256.0):
        self.k = k
        self.b = b
        self.avg_len = avg_len

        self.punctuation = set(string.punctuation)
        self.stopwords = set(stopwords.words("english") + stopwords.words("russian"))
        self.stemmer = Stemmer.Stemmer("english")
        self.tokenizer = NLTKWordTokenizer()

    def _embed_documents(
        self,
        documents: Union[str, Iterable[str]],
        batch_size: int = 256,
        parallel: Optional[int] = None,
    ) -> Iterable[SparseVector]:
        is_small = False

        if isinstance(documents, str):
            documents = [documents]
            is_small = True

        if isinstance(documents, list):
            if len(documents) < batch_size:
                is_small = True

        if parallel is None or is_small:
            for batch in iter_batch(documents, batch_size):
                yield from self.raw_embed(batch)
        else:
            # TODO: Implement parallel processing
            raise NotImplementedError

    def embed(
        self,
        documents: Union[str, Iterable[str]],
        batch_size: int = 256,
        parallel: Optional[int] = None,
    ) -> Iterable[SparseVector]:
        """
        Encode a list of documents into list of embeddings.
        We use mean pooling with attention so that the model can handle variable-length inputs.

        Args:
            documents: Iterator of documents or single document to embed
            batch_size: Batch size for encoding -- higher values will use more memory, but be faster
            parallel:
                If > 1, data-parallel encoding will be used, recommended for offline encoding of large datasets.
                If 0, use all available cores.
                If None, don't use data-parallel processing, use default onnxruntime threading instead.

        Returns:
            List of embeddings, one per document
        """
        yield from self._embed_documents(
            documents=documents,
            batch_size=batch_size,
            parallel=parallel,
        )

    def _stem(self, tokens: List[str]) -> List[str]:
        stemmed_tokens = []
        for token in tokens:
            if token in self.punctuation:
                continue

            if token in self.stopwords:
                continue

            stemmed_token = self.stemmer.stemWord(token)

            if stemmed_token:
                stemmed_tokens.append(stemmed_token)
        return stemmed_tokens

    def raw_embed(
        self,
        documents: List[str],
    ) -> List[SparseVector]:
        embeddings = []
        for document in documents:
            tokens = self.tokenizer.tokenize(document)
            stemmed_tokens = self._stem(tokens)
            token_id2value = self._term_frequency(stemmed_tokens)
            embeddings.append(SparseVector(indices=list(token_id2value.keys()), values=list(token_id2value.values())))
        return embeddings

    def _term_frequency(self, tokens: List[str]) -> Dict[int, float]:
        """Calculate the term frequency part of the BM25 formula.

        (
            f(q_i, d) * (k + 1)
        ) / (
            f(q_i, d) + k * (1 - b + b * (|d| / avg_len))
        )

        Args:
            tokens (List[str]): The list of tokens in the document.

        Returns:
            Dict[int, float]: The token_id to term frequency mapping.
        """
        tf_map = {}
        counter = defaultdict(int)
        for stemmed_token in tokens:
            counter[stemmed_token] += 1

        doc_len = len(tokens)
        for stemmed_token in counter:
            token_id = self.compute_token_id(stemmed_token)
            num_occurrences = counter[stemmed_token]
            tf_map[token_id] = num_occurrences * (self.k + 1)
            tf_map[token_id] /= num_occurrences + self.k * (1 - self.b + self.b * doc_len / self.avg_len)
        return tf_map

    @classmethod
    def compute_token_id(cls, token: str) -> int:
        return abs(mmh3.hash(token))

    def query_embed(self, query: str) -> SparseVector:
        """To emulate BM25 behaviour, we don't need to use weights in the query, and
        it's enough to just hash the tokens and assign a weight of 1.0 to them.
        """
        tokens = self.tokenizer.tokenize(query)
        stemmed_tokens = self._stem(tokens)
        token_ids = list(set(self.compute_token_id(token) for token in stemmed_tokens))
        values = [1.0] * len(token_ids)
        return SparseVector(indices=token_ids, values=values)
