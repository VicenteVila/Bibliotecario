"""`config.py`: el .env del cwd debe surtir efecto en las constantes de entorno.

Hasta 2026-10-21 `_load_env()` corría AL FINAL del módulo, después de leer
`NVIDIA_MODEL` (y `GROQ_MODEL`, `NVIDIA_FALLBACK_MODEL`,
`BIBLIOTECARIO_DATA_DIR`): esas constantes cogían el valor por defecto en
silencio mientras las keys sí funcionaban (se leen perezosas). Se comprueba en
subproceso porque el orden ocurre en la importación, que es única por sesión.
"""

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
_VARS = ("NVIDIA_MODEL", "GROQ_MODEL", "NVIDIA_FALLBACK_MODEL", "BIBLIOTECARIO_DATA_DIR")


def _constante(name: str, cwd: Path, exportada: str | None = None) -> str:
    """Valor de `config.<name>` importando en `cwd` con un entorno saneado."""
    env = {k: v for k, v in os.environ.items() if k not in _VARS}
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    if exportada is not None:
        env["NVIDIA_MODEL"] = exportada
    code = f"from bibliotecario import config; print(config.{name})"
    r = subprocess.run([sys.executable, "-c", code], cwd=str(cwd), env=env,
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


def test_dotenv_del_cwd_surte_efecto_en_las_constantes(tmp_path):
    (tmp_path / ".env").write_text("NVIDIA_MODEL=modelo-de-prueba-123\n",
                                   encoding="utf-8")
    assert _constante("_NVIDIA_MODEL", tmp_path) == "modelo-de-prueba-123"


def test_lo_exportado_en_el_entorno_manda_sobre_dotenv(tmp_path):
    (tmp_path / ".env").write_text("NVIDIA_MODEL=modelo-del-archivo\n",
                                   encoding="utf-8")
    assert _constante("_NVIDIA_MODEL", tmp_path, exportada="modelo-exportado") == "modelo-exportado"


def test_sin_dotenv_ni_variable_cae_en_el_defecto(tmp_path):
    assert _constante("_NVIDIA_MODEL", tmp_path) == "nvidia/nemotron-3-super-120b-a12b"
