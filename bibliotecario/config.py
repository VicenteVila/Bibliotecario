from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_DATA_DIR = Path("data")
_LLM_MODEL = "gemini-3.6-flash"
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EMBED_DIM = 384


def _load_env():
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()


def gemini_api_key() -> str | None:
    keys = gemini_api_keys()
    return keys[0] if keys else None


def gemini_api_keys() -> list[str]:
    """Cadena de keys: principal + fallbacks (GEMINI_API_KEY, GEMINI_API_KEY_2, ...)."""
    keys: list[str] = []
    for i in range(1, 6):
        suffix = "" if i == 1 else f"_{i}"
        v = os.environ.get(f"GEMINI_API_KEY{suffix}")
        if v and v not in keys:
            keys.append(v)
    return keys


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN_PAT")


def data_dir() -> Path:
    p = _DEFAULT_DATA_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    return data_dir() / "bibliotecario.db"


def vector_index_path() -> Path:
    return data_dir() / "embeddings.index"
