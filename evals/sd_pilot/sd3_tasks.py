"""Tareas SD-3 (HITO23): probe, lint, QA y lock, sin LLM.

El probe es desechable. Las tareas dev/test de la Fase 2 se añadirán solo si
P1-P5 pasan; este módulo mantiene el mismo contrato de QA/lock para ambas.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

SD3_PROBE_TASK_IDS = [
    "sd3-probe-breadth",
    "sd3-probe-runtime",
    "sd3-probe-contract",
]

# Fase 2: se rellenan solo tras un probe verde y con presupuesto nuevo.
SD3_DEV_TASK_IDS: list[str] = []
SD3_TEST_TASK_IDS: list[str] = []
SD3_TASK_IDS = SD3_PROBE_TASK_IDS + SD3_DEV_TASK_IDS + SD3_TEST_TASK_IDS

SD3_TASK_AXES: dict[str, tuple[str, ...]] = {
    "sd3-probe-breadth": ("amplitud", "salida", "multi-fichero"),
    "sd3-probe-runtime": ("runtime", "estado", "secuencias"),
    "sd3-probe-contract": ("contrato-parcial", "oraculo-parcial", "generalizacion"),
}

PUBLIC_TESTS_MIN = 1
HIDDEN_TESTS_MIN = 4
WORKSPACE_PY_MIN = 2

LOCK_NAME = "SD3_PROBE_LOCK.json"


def sd3_root() -> Path:
    return Path(__file__).resolve().parent


def task_dir(task_id: str) -> Path:
    return sd3_root() / "sd_tasks_v3" / task_id


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
        "probe_task_ids": SD3_PROBE_TASK_IDS,
        "dev_task_ids": SD3_DEV_TASK_IDS,
        "test_task_ids": SD3_TEST_TASK_IDS,
        "task_axes": SD3_TASK_AXES,
    }


def build_lock() -> dict:
    files = {
        str(path.relative_to(sd3_root())): _sha256_file(path)
        for task_id in SD3_TASK_IDS
        for path in _task_files(task_id)
    }
    split = _split_payload()
    split_bytes = json.dumps(
        split, sort_keys=True, ensure_ascii=True
    ).encode("utf-8")
    return {
        "version": 1,
        "created_utc": datetime.now(UTC).isoformat(),
        "task_count": len(SD3_TASK_IDS),
        "split_sha256": hashlib.sha256(split_bytes).hexdigest(),
        "split": split,
        "files_sha256": files,
    }


def write_lock(path: Path | None = None) -> Path:
    target = path or (sd3_root() / LOCK_NAME)
    target.write_text(
        json.dumps(build_lock(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def verify_lock(path: Path | None = None) -> list[str]:
    target = path or (sd3_root() / LOCK_NAME)
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
    for tid in (task_ids or SD3_TASK_IDS):
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
        axes = SD3_TASK_AXES.get(tid, ())
        if len(axes) < 2:
            problems.append(f"{tid}: ejes de dureza <2 declarados")
    return problems


def qa_task(task_id: str) -> dict:
    from evals.sd_pilot import verifier

    d = task_dir(task_id)
    out: dict = {"task": task_id, "ok": False}

    ref_ws = Path(tempfile.mkdtemp(prefix=f"qa_sd3_{task_id}_ref_"))
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

    emp_ws = Path(tempfile.mkdtemp(prefix=f"qa_sd3_{task_id}_emp_"))
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

    out["ok"] = bool(
        out["ref_score"] == 100.0
        and out["ref_public"]["failed"] == 0
        and out["empty_score"] < 100.0
        and out["empty_public"]["failed"] > 0
    )
    return out


def qa_all(task_ids: list[str] | None = None) -> list[dict]:
    return [qa_task(tid) for tid in (task_ids or SD3_TASK_IDS)]
