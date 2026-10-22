"""Tareas congeladas (§1.B) + lint y QA de fixtures del piloto HITO19.

El QA de BUILD (obligatorio, §1.B) valida por tarea:
  (a) reference aplicada -> 100% de tests ocultos pasan;
  (b) workspace sin solución -> >=1 fallo público y <100% de ocultos.
"""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

TASK_IDS = [
    "checkout-rounding",
    "repo-cache-layer",
    "dsl-parser",
    "interval-scheduler",
    "seeded-bugs-billing",
    "cli-subcommand",
    "workflow-statemachine",
    "batch-coalescer",
    "schema-validator",
    "plugin-registry",
    "csv-diff-engine",
    "config-migration",
]

# Ejes de dureza declarados en la autoría (>=2 exigido por lint; §1.3).
TASK_AXES: dict[str, tuple[str, ...]] = {
    "checkout-rounding": ("multi-fichero", "limites-ocultos"),
    "repo-cache-layer": ("arquitectura", "contrato", "limites-ocultos"),
    "dsl-parser": ("contrato", "limites-ocultos"),
    "interval-scheduler": ("limites-ocultos", "arquitectura"),
    "seeded-bugs-billing": ("recuperacion", "multi-fichero"),
    "cli-subcommand": ("multi-fichero", "contrato"),
    "workflow-statemachine": ("limites-ocultos", "arquitectura"),
    "batch-coalescer": ("limites-ocultos", "contrato"),
    "schema-validator": ("contrato", "limites-ocultos"),
    "plugin-registry": ("arquitectura", "limites-ocultos"),
    "csv-diff-engine": ("contrato", "limites-ocultos"),
    "config-migration": ("multi-fichero", "contrato", "limites-ocultos"),
}

PUBLIC_TESTS_MIN = 4
HIDDEN_TESTS_MIN = 10
WORKSPACE_PY_MIN = 3


def sd_root() -> Path:
    return Path(__file__).resolve().parent


def task_dir(task_id: str) -> Path:
    return sd_root() / "sd_tasks" / task_id


def _count_tests(path: Path) -> int:
    if not path.is_dir():
        return 0
    n = 0
    for f in sorted(path.glob("**/test_*.py")):
        text = f.read_text(encoding="utf-8", errors="replace")
        n += len(re.findall(r"^\s*def test_", text, re.MULTILINE))
    return n


def _workspace_py_count(workspace: Path) -> int:
    return sum(1 for f in workspace.glob("**/*.py") if "tests_public" not in f.parts)


def lint_tasks(task_ids: list[str] | None = None) -> list[str]:
    """Problemas de estructura de fixtures (sin ejecutar pytest)."""
    problems: list[str] = []
    for tid in (task_ids or TASK_IDS):
        d = task_dir(tid)
        if not d.is_dir():
            problems.append(f"{tid}: falta el directorio")
            continue
        if not (d / "TASK.md").is_file():
            problems.append(f"{tid}: falta TASK.md")
        ws = d / "workspace"
        if not ws.is_dir():
            problems.append(f"{tid}: falta workspace/")
            continue
        if _workspace_py_count(ws) < WORKSPACE_PY_MIN:
            problems.append(f"{tid}: workspace con <{WORKSPACE_PY_MIN} ficheros .py de código")
        n_pub = _count_tests(ws / "tests_public")
        if n_pub < PUBLIC_TESTS_MIN:
            problems.append(f"{tid}: {n_pub} tests públicos (<{PUBLIC_TESTS_MIN})")
        hid = d / "tests_hidden"
        if not (hid / "conftest.py").is_file():
            problems.append(f"{tid}: falta tests_hidden/conftest.py")
        n_hid = _count_tests(hid)
        if n_hid < HIDDEN_TESTS_MIN:
            problems.append(f"{tid}: {n_hid} tests ocultos (<{HIDDEN_TESTS_MIN})")
        if not (d / "reference").is_dir() or not any((d / "reference").rglob("*.py")):
            problems.append(f"{tid}: reference/ vacío o ausente")
        axes = TASK_AXES.get(tid, ())
        if len(axes) < 2:
            problems.append(f"{tid}: ejes de dureza <2 declarados")
    return problems


def qa_task(task_id: str) -> dict:
    """QA de BUILD de una tarea (§1.3): referencia=100% ocultos; vacío<100%."""
    from evals.sd_pilot import verifier

    d = task_dir(task_id)
    out: dict = {"task": task_id, "ok": False}

    ref_ws = Path(tempfile.mkdtemp(prefix=f"qa_{task_id}_ref_"))
    try:
        shutil.copytree(d / "workspace", ref_ws, dirs_exist_ok=True)
        shutil.copytree(d / "reference", ref_ws, dirs_exist_ok=True)
        shutil.copytree(d / "tests_hidden", ref_ws / "tests_hidden")
        ref = verifier.hidden_score_dir(ref_ws)
        out["ref_score"] = ref["score"]
        out["ref_total"] = ref["total"]
        pub_ref = verifier.public_summary(ref_ws)
        out["ref_public"] = {"passed": pub_ref["passed"], "failed": pub_ref["failed"]}
    finally:
        shutil.rmtree(ref_ws, ignore_errors=True)

    emp_ws = Path(tempfile.mkdtemp(prefix=f"qa_{task_id}_emp_"))
    try:
        shutil.copytree(d / "workspace", emp_ws, dirs_exist_ok=True)
        shutil.copytree(d / "tests_hidden", emp_ws / "tests_hidden")
        emp_hid = verifier.hidden_score_dir(emp_ws)
        out["empty_score"] = emp_hid["score"]
        emp_pub = verifier.public_summary(emp_ws)
        out["empty_public"] = {"passed": emp_pub["passed"], "failed": emp_pub["failed"]}
    finally:
        shutil.rmtree(emp_ws, ignore_errors=True)

    out["ok"] = (out["ref_score"] == 100.0
                 and out["empty_public"]["failed"] >= 1
                 and out["empty_score"] < 100.0)
    return out


def qa_all() -> list[dict]:
    return [qa_task(tid) for tid in TASK_IDS]
