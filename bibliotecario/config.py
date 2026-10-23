from __future__ import annotations

import os
from pathlib import Path


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


# Carga ANTES de cualquier constante de entorno. Hasta 2026-10-21 estaba al
# final del módulo: NVIDIA_MODEL, GROQ_MODEL, NVIDIA_FALLBACK_MODEL y
# BIBLIOTECARIO_DATA_DIR del .env se leían antes de existir y se ignoraban en
# silencio (solo las keys, que se leen perezosas dentro de funciones,
# funcionaban). `setdefault` mantiene la prioridad: lo exportado en el entorno
# manda sobre el .env.
_load_env()

# Anclado a la raiz del repo, no al cwd. Con Path("data"), lanzar el harness
# desde otro directorio (p.ej. evals/) creaba data/ vacio en silencio y se
# evaluaba contra un corpus inexistente en lugar de fallar. Sigue siendo
# sobreescribible por entorno para los tests y los usos con otra ruta.
_DEFAULT_DATA_DIR = Path(
    os.environ.get("BIBLIOTECARIO_DATA_DIR")
    or Path(__file__).resolve().parent.parent / "data"
)
_LLM_MODEL = "gemini-3.6-flash"
# Reparado 2026-10-15: llama-3.3-70b-versatile fue dado de baja en Groq (404
# model_not_found) y la key antigua daba 403 (Cloudflare 1010 por UA). Con la
# key rotada, el lineup vivo de Groq ya no incluye llama-3.3; el elegido tras
# probar la API es openai/gpt-oss-120b (120B, buen código, UA del cliente
# aceptado). Sigue siendo sobreescribible por GROQ_MODEL.
_GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
# NVIDIA: nemotron-3-super-120b es el que mejor sostiene los prompts largos del loop
# (calidad + 1.8s). El 30b "lightning" degrada a basura con contexto largo; por eso
# el respaldo es gpt-oss-20b (otra familia) y no un modelo de la misma serie.
_NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b")
_NVIDIA_FALLBACK = os.environ.get("NVIDIA_FALLBACK_MODEL", "openai/gpt-oss-20b")
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_EMBED_DIM = 384


def gemini_api_key() -> str | None:
    keys = gemini_api_keys()
    return keys[0] if keys else None


def gemini_api_keys() -> list[str]:
    """SIEMPRE la misma clave (política del dueño 2026-10-23): se usa
    `GEMINI_API_KEY` (principal) y nada más, para que cada run consuma una
    cuota conocida y presupuestable. `_2`/`_3` son reserva manual: solo
    entran si falta la principal (sin rotación automática)."""
    principal = os.environ.get("GEMINI_API_KEY")
    if principal:
        return [principal]
    keys: list[str] = []
    for i in range(2, 6):
        v = os.environ.get(f"GEMINI_API_KEY_{i}")
        if v and v not in keys:
            keys.append(v)
    return keys


def groq_api_key() -> str | None:
    return os.environ.get("GROQ_API_KEY") or None


def nvidia_api_key() -> str | None:
    return os.environ.get("NVIDIA_API_KEY") or None


def github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN_PAT")


def data_dir() -> Path:
    p = _DEFAULT_DATA_DIR
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    # Corpus por dominio: si BIBLIOTECARIO_DB apunta a otra DB se usa esa
    # (p. ej. data/corpora/game_development.db durante la ingesta de dominio).
    # Sin la variable, la ruta por defecto es exactamente la de siempre.
    override = os.environ.get("BIBLIOTECARIO_DB")
    if override:
        p = Path(override)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p
    return data_dir() / "bibliotecario.db"


def vector_index_path() -> Path:
    return data_dir() / "embeddings.index"
