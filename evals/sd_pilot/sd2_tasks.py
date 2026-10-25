"""Tareas SD-2 (HITO22): lint y QA de fixtures, sin LLM.

El vertical slice declara una tarea dev y una test de la familia F1. El resto
se añadirá tras la revisión del slice; el test no se calibra.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SD2_DEV_TASK_IDS = [
    "sd2-dev-f1-inventory",
    "sd2-dev-f2-inventory",
    "sd2-dev-f3-inventory",
    "sd2-dev-f1-reservations",
    "sd2-dev-f2-reservations",
    "sd2-dev-f3-reservations",
    "sd2-dev-f1-payroll",
    "sd2-dev-f2-payroll",
    "sd2-dev-f3-payroll",
    "sd2-dev-f1-routing",
    "sd2-dev-f2-routing",
    "sd2-dev-f3-routing",
]
SD2_TEST_TASK_IDS = [
    "sd2-test-f1-banking",
    "sd2-test-f2-banking",
    "sd2-test-f3-banking",
    "sd2-test-f1-healthcare",
    "sd2-test-f2-healthcare",
    "sd2-test-f3-healthcare",
    "sd2-test-f1-logistics",
    "sd2-test-f2-logistics",
    "sd2-test-f3-logistics",
    "sd2-test-f1-media",
    "sd2-test-f2-media",
    "sd2-test-f3-media",
]
SD2_TASK_IDS = SD2_DEV_TASK_IDS + SD2_TEST_TASK_IDS

SD2_TASK_FAMILY: dict[str, str] = {
    task_id: task_id.split("-")[2].upper()
    for task_id in SD2_TASK_IDS
}
SD2_TASK_DOMAIN: dict[str, str] = {
    task_id: task_id.split("-", 3)[3]
    for task_id in SD2_TASK_IDS
}

SD2_TASK_AXES: dict[str, tuple[str, ...]] = {
    "sd2-dev-f1-inventory": ("feedback", "multi-fichero", "limites-ocultos"),
    "sd2-dev-f2-inventory": ("feedback", "contrato", "limites-ocultos"),
    "sd2-dev-f3-inventory": ("feedback", "refactor", "estado"),
    "sd2-dev-f1-reservations": ("feedback", "multi-fichero", "capacidad"),
    "sd2-dev-f2-reservations": ("feedback", "contrato", "capacidad"),
    "sd2-dev-f3-reservations": ("feedback", "refactor", "estado"),
    "sd2-dev-f1-payroll": ("feedback", "calculo", "limites-ocultos"),
    "sd2-dev-f2-payroll": ("feedback", "contrato", "calculo"),
    "sd2-dev-f3-payroll": ("feedback", "refactor", "estado"),
    "sd2-dev-f1-routing": ("feedback", "grafo", "limites-ocultos"),
    "sd2-dev-f2-routing": ("feedback", "contrato", "grafo"),
    "sd2-dev-f3-routing": ("feedback", "refactor", "estado"),
    "sd2-test-f1-banking": ("feedback", "multi-fichero", "limites-ocultos"),
    "sd2-test-f2-banking": ("feedback", "contrato", "limites-ocultos"),
    "sd2-test-f3-banking": ("feedback", "refactor", "estado"),
    "sd2-test-f1-healthcare": ("feedback", "prioridad", "limites-ocultos"),
    "sd2-test-f2-healthcare": ("feedback", "contrato", "prioridad"),
    "sd2-test-f3-healthcare": ("feedback", "refactor", "estado"),
    "sd2-test-f1-logistics": ("feedback", "calculo", "limites-ocultos"),
    "sd2-test-f2-logistics": ("feedback", "contrato", "calculo"),
    "sd2-test-f3-logistics": ("feedback", "refactor", "estado"),
    "sd2-test-f1-media": ("feedback", "seleccion", "limites-ocultos"),
    "sd2-test-f2-media": ("feedback", "contrato", "seleccion"),
    "sd2-test-f3-media": ("feedback", "refactor", "estado"),
}

PUBLIC_TESTS_MIN = 4
HIDDEN_TESTS_MIN = 10
WORKSPACE_PY_MIN = 3


def sd2_root() -> Path:
    return Path(__file__).resolve().parent


def task_dir(task_id: str) -> Path:
    return sd2_root() / "sd_tasks_v2" / task_id


LOCK_NAME = "SD2_LOCK.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _task_files(task_id: str) -> list[Path]:
    root = task_dir(task_id)
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )


def _split_payload() -> dict:
    return {
        "dev_task_ids": SD2_DEV_TASK_IDS,
        "test_task_ids": SD2_TEST_TASK_IDS,
        "task_axes": SD2_TASK_AXES,
        "task_family": SD2_TASK_FAMILY,
        "task_domain": SD2_TASK_DOMAIN,
    }


def build_lock() -> dict:
    files = {
        str(path.relative_to(sd2_root())): _sha256_file(path)
        for task_id in SD2_TASK_IDS
        for path in _task_files(task_id)
    }
    split = _split_payload()
    split_bytes = json.dumps(
        split, sort_keys=True, ensure_ascii=True
    ).encode("utf-8")
    return {
        "version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "task_count": len(SD2_TASK_IDS),
        "split_sha256": hashlib.sha256(split_bytes).hexdigest(),
        "split": split,
        "files_sha256": files,
    }


def write_lock(path: Path | None = None) -> Path:
    target = path or (sd2_root() / LOCK_NAME)
    target.write_text(
        json.dumps(build_lock(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def verify_lock(path: Path | None = None) -> list[str]:
    target = path or (sd2_root() / LOCK_NAME)
    if not target.is_file():
        return [f"falta {target}"]
    try:
        expected = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"lock ilegible: {exc}"]
    actual = build_lock()
    problems: list[str] = []
    if expected.get("task_count") != actual["task_count"]:
        problems.append("task_count distinto")
    if expected.get("split_sha256") != actual["split_sha256"]:
        problems.append("split distinto")
    expected_files = expected.get("files_sha256", {})
    actual_files = actual["files_sha256"]
    for name in sorted(set(expected_files) | set(actual_files)):
        if expected_files.get(name) != actual_files.get(name):
            problems.append(f"hash distinto: {name}")
    return problems


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
