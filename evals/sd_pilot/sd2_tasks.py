"""Tareas SD-2 (HITO22): lint y QA de fixtures, sin LLM.

El vertical slice declara una tarea dev y una test de la familia F1. El resto
se añadirá tras la revisión del slice; el test no se calibra.
"""
from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

SD2_TASK_IDS = [
    "sd2-dev-f1-inventory",
    "sd2-test-f1-banking",
]
SD2_DEV_TASK_IDS = [
    "sd2-dev-f1-inventory",
]
SD2_TEST_TASK_IDS = [
    "sd2-test-f1-banking",
]

SD2_TASK_AXES: dict[str, tuple[str, ...]] = {
    "sd2-dev-f1-inventory": ("feedback", "multi-fichero", "limites-ocultos"),
    "sd2-test-f1-banking": ("feedback", "multi-fichero", "limites-ocultos"),
}

PUBLIC_TESTS_MIN = 4
HIDDEN_TESTS_MIN = 10
WORKSPACE_PY_MIN = 3


def sd2_root() -> Path:
    return Path(__file__).resolve().parent


def task_dir(task_id: str) -> Path:
    return sd2_root() / "sd_tasks_v2" / task_id


def _count_tests(path: Path) -> int:
    if not path.is_dir():
        return 0
    n = 0
    for f in sorted(path.glob("**/test_*.py")):
        text = f.read_text(encoding="utf-8", errors="replace")
        n += len(re.findall(r"^\s*def test_", text, re.MULTILINE))
    return n


def _workspace_py_count(workspace: Path) -> int:
    return sum(
        1 for f in workspace.glob("**/*.py") if "tests_public" not in f.parts
    )


def lint_tasks(task_ids: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    for tid in (task_ids or SD2_TASK_IDS):
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
            problems.append(
                f"{tid}: workspace con <{WORKSPACE_PY_MIN} ficheros .py de código"
            )
        n_pub = _count_tests(ws / "tests_public")
        if n_pub < PUBLIC_TESTS_MIN:
            problems.append(f"{tid}: {n_pub} tests públicos (<{PUBLIC_TESTS_MIN})")
        hid = d / "tests_hidden"
        if not (hid / "conftest.py").is_file():
            problems.append(f"{tid}: falta tests_hidden/conftest.py")
        n_hid = _count_tests(hid)
        if n_hid < HIDDEN_TESTS_MIN:
            problems.append(f"{tid}: {n_hid} tests ocultos (<{HIDDEN_TESTS_MIN})")
        if not (d / "reference").is_dir() or not any(
            (d / "reference").rglob("*.py")
        ):
            problems.append(f"{tid}: reference/ vacío o ausente")
        axes = SD2_TASK_AXES.get(tid, ())
        if len(axes) < 2:
            problems.append(f"{tid}: ejes de dureza <2 declarados")
    return problems


def qa_task(task_id: str) -> dict:
    from evals.sd_pilot import verifier

    d = task_dir(task_id)
    out: dict = {"task": task_id, "ok": False}

    ref_ws = Path(tempfile.mkdtemp(prefix=f"qa_sd2_{task_id}_ref_"))
    try:
        shutil.copytree(d / "workspace", ref_ws, dirs_exist_ok=True)
        shutil.copytree(d / "reference", ref_ws, dirs_exist_ok=True)
        shutil.copytree(d / "tests_hidden", ref_ws / "tests_hidden")
        ref = verifier.hidden_score_dir(ref_ws)
        out["ref_score"] = ref["score"]
        out["ref_total"] = ref["total"]
        pub_ref = verifier.public_summary(ref_ws)
        out["ref_public"] = {
            "passed": pub_ref["passed"],
            "failed": pub_ref["failed"],
        }
    finally:
        shutil.rmtree(ref_ws, ignore_errors=True)

    emp_ws = Path(tempfile.mkdtemp(prefix=f"qa_sd2_{task_id}_emp_"))
    try:
        shutil.copytree(d / "workspace", emp_ws, dirs_exist_ok=True)
        shutil.copytree(d / "tests_hidden", emp_ws / "tests_hidden")
        emp_hid = verifier.hidden_score_dir(emp_ws)
        out["empty_score"] = emp_hid["score"]
        emp_pub = verifier.public_summary(emp_ws)
        out["empty_public"] = {
            "passed": emp_pub["passed"],
            "failed": emp_pub["failed"],
        }
    finally:
        shutil.rmtree(emp_ws, ignore_errors=True)

    out["ok"] = (
        out["ref_score"] == 100.0
        and out["empty_public"]["failed"] >= 1
        and out["empty_score"] < 100.0
    )
    return out


def qa_all(task_ids: list[str] | None = None) -> list[dict]:
    return [qa_task(tid) for tid in (task_ids or SD2_TASK_IDS)]
