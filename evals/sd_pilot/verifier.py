"""Verificador determinista (§1.4): pytest público (herramienta del agente) y
oculto (m_h(x), el score del piloto). 0 tokens de juez.

El verificador de ocultos copia el workspace final a un dir limpio y añade
`tests_hidden/` tal y como hizo el QA de BUILD — supuesto no-adversarial
declarado en §1.B.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_TIMEOUT_PUBLIC = 60
_TIMEOUT_HIDDEN = 120


def run_pytest(cwd: Path, target: str, tb: str = "no", timeout: int = 60) -> dict:
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
    cmd = [sys.executable, "-m", "pytest", target, "-q", f"--tb={tb}", "-p", "no:cacheprovider"]
    try:
        proc = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env,
                              capture_output=True, text=True, timeout=timeout,
                              check=False)
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "errors": 1, "total": 1,
                "timeout": True, "output": "TIMEOUT"}
    out = (proc.stdout or "") + (proc.stderr or "")

    def _n(pattern: str) -> int:
        m = re.search(pattern, out)
        return int(m.group(1)) if m else 0

    passed = _n(r"(\d+) passed")
    failed = _n(r"(\d+) failed")
    errors = _n(r"(\d+) error")
    total = passed + failed + errors
    if total == 0:
        errors, total = 1, 1
    return {"passed": passed, "failed": failed, "errors": errors, "total": total,
            "timeout": False, "output": out[-6000:]}


def public_summary(workspace: Path, tb: str = "line") -> dict:
    """Resumen de tests públicos (herramienta `run_tests` del agente)."""
    if not workspace.is_dir():
        return {"passed": 0, "failed": 0, "errors": 1, "total": 1,
                "timeout": False, "output": "workspace inexistente"}
    return run_pytest(workspace, "tests_public", tb, _TIMEOUT_PUBLIC)


def hidden_score_dir(cwd: Path) -> dict:
    """Ejecuta tests_hidden ya presentes dentro de `cwd` y devuelve score %."""
    res = run_pytest(cwd, "tests_hidden", "no", _TIMEOUT_HIDDEN)
    res["score"] = round(100.0 * res["passed"] / res["total"], 4) if res["total"] else 0.0
    return res


def hidden_score(final_workspace: Path, task_dir: Path) -> dict:
    """m_h(x): % de tests ocultos que pasan contra el workspace final."""
    if not final_workspace.is_dir():
        return {"passed": 0, "failed": 0, "errors": 1, "total": 1, "score": 0.0,
                "timeout": False, "output": "workspace del agente inexistente"}
    tmp = Path(tempfile.mkdtemp(prefix="sd_hidden_"))
    try:
        dst = tmp / "workspace"
        shutil.copytree(final_workspace, dst)
        shutil.copytree(task_dir / "tests_hidden", dst / "tests_hidden")
        return hidden_score_dir(dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
