import hashlib
import math
import os
import time
from typing import Any, List, Optional

class EmbeddingEngine:
    """Local embedding adapter with a deterministic fallback.

    The normal path uses Sentence Transformers on the user's machine. The
    fallback keeps the app usable when the optional model has not been
    downloaded yet; it is deliberately exposed in status so it cannot be
    mistaken for a production-quality semantic model.
    """

    def __init__(self, model_name: Optional[str] = None, dimension: int = 384):
        self.model_name = model_name or os.getenv(
            "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.device = os.getenv("EMBEDDING_DEVICE", "cpu")
        self.dimension = dimension
        self._st_model = None
        self._model_load_error: Optional[str] = None
        self.last_embedding_latency_ms = 0.0
        self.embedding_source = "fallback"

    def _get_st_model(self):
        if self._st_model is None:
            if self.model_name.lower() in ("fallback", "mock", "none", "hash"):
                self._st_model = "fallback"
                self.embedding_source = "fallback"
                return self._st_model
            try:
                # pyrefly: ignore [missing-import]
                from sentence_transformers import SentenceTransformer  # pyright: ignore[reportMissingImports]
                self._st_model = SentenceTransformer(self.model_name, device=self.device)
                get_dimension = getattr(
                    self._st_model,
                    "get_embedding_dimension",
                    self._st_model.get_sentence_embedding_dimension,
                )
                loaded_dimension = get_dimension()
                if loaded_dimension:
                    self.dimension = int(loaded_dimension)
                self.embedding_source = "sentence-transformers"
            except Exception as exc:
                self._model_load_error = f"{type(exc).__name__}: {exc}"
                self._st_model = "fallback"
        return self._st_model

    def _encode(self, text: str, *, query: bool = False) -> List[float]:
        started = time.perf_counter()
        model = self._get_st_model()
        if model != "fallback":
            try:
                # encode_query/document are preferred for asymmetric search
                # models, while the compatibility fallback works for older
                # Sentence Transformers releases and MiniLM.
                encode_method: Any = getattr(
                    model,
                    "encode_query" if query else "encode_document",
                    None,
                )
                if encode_method is None:
                    encode_method = model.encode
                emb = encode_method(
                    text,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                )
                self.last_embedding_latency_ms = round(
                    (time.perf_counter() - started) * 1000, 3
                )
                return emb.tolist()
            except Exception as exc:
                self._model_load_error = f"Encoding failed: {type(exc).__name__}: {exc}"

        # Deterministic local fallback for first-run/offline use.
        vector = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            self.last_embedding_latency_ms = round((time.perf_counter() - started) * 1000, 3)
            return vector

        for idx, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            pos = h % self.dimension
            weight = 1.0 / math.sqrt(idx + 1)
            vector[pos] += weight

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [x / norm for x in vector]
        self.last_embedding_latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return vector

    def embed_query(self, text: str) -> List[float]:
        return self._encode(text, query=True)

    def embed_document(self, text: str) -> List[float]:
        return self._encode(text, query=False)

    def embed_text(self, text: str) -> List[float]:
        """Backward-compatible alias used by older callers."""
        return self.embed_document(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_document(t) for t in texts]

    def status(self) -> dict:
        return {
            "model": self.model_name,
            "device": self.device,
            "source": self.embedding_source,
            "dimension": self.dimension,
            "model_load_error": self._model_load_error,
        }

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 <= 0 or norm2 <= 0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm1 * norm2)))
