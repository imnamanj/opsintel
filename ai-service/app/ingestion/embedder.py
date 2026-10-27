"""Turn text into 384-number vectors using a small local model."""
from pathlib import Path
from threading import Lock
from typing import List, Optional, Sequence

from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
CACHE_DIR = Path.home() / ".cache" / "opsintel-models"

_model: Optional[TextEmbedding] = None
_lock = Lock()


def _get_model() -> TextEmbedding:
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(CACHE_DIR))
    return _model


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    if not texts:
        return []
    vectors = _get_model().embed(list(texts))
    return [[float(x) for x in vector] for vector in vectors]