from __future__ import annotations

import hashlib
from collections.abc import Iterable

import numpy as np

from bibliotecario.config import _EMBED_MODEL

try:
    from sentence_transformers import SentenceTransformer as _ST
except ImportError:  # pragma: no cover
    _ST = None


def _model():
    if _ST is None:
        raise RuntimeError("sentence-transformers no instalado (pip install sentence-transformers)")
    global _m
    if _m is None:
        _m = _ST(_EMBED_MODEL)
    return _m


_m = None


def encode(texts: Iterable[str], batch_size: int = 32) -> np.ndarray:
    """Devuelve matrices de embeddings normalizados (n, dim)."""
    m = _model()
    out = m.encode(list(texts), batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False)
    if isinstance(out, list):
        out = np.asarray(out)
    return out.astype(np.float32)


def encode_one(text: str) -> np.ndarray:
    return encode([text])[0]


def embed_blob(vec: np.ndarray) -> bytes:
    return vec.astype(np.float32).tobytes()


def blob_to_vec(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def text_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]