"""BUILD de las 12 tareas B de HITO20 (composición multi-paquete).

Cada tarea B es un monorepo con DOS fixtures congeladas de H19. No modifica
los originales: copia workspace, reference, tests públicos y ocultos, y
prefija los tests para evitar colisiones. El endurecimiento declarado es
"alcance multi-paquete": el agente debe resolver ambos contratos.

Uso: `.venv/bin/python -m evals.sd_pilot.build_b_tasks`
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from evals.sd_pilot.tasks import B_DOMAINS, B_TASK_IDS, task_dir

SD = Path(__file__).resolve().parent
QA_OUT = SD.parent / "results" / "result_b_build_qa.json"


def _limpia(dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)


def _copia_workspace(src: Path, dst: Path, prefijo: str) -> None:
    for item in src.iterdir():
        if item.name in {"tests_public", "pytest.ini", "__pycache__"}:
            continue
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(item, target)
    pub = src / "tests_public"
    if pub.is_dir():
        for test in pub.glob("test_*.py"):
            shutil.copy2(test, dst / "tests_public"
                         / f"test_{prefijo}_{test.name.removeprefix('test_')}")


def _copia_hidden(src: Path, dst: Path, prefijo: str) -> None:
    for test in src.glob("test_*.py"):
        shutil.copy2(test, dst
                     / f"test_{prefijo}_{test.name.removeprefix('test_')}")


def _task_md(tid: str, a: str, b: str) -> str:
    ta = (task_dir(a) / "TASK.md").read_text(encoding="utf-8").strip()
    tb = (task_dir(b) / "TASK.md").read_text(encoding="utf-8").strip()
    return (
        f"# Tarea B: {tid} — monorepo con dos paquetes\n\n"
        "Esta tarea endurece el alcance: el repositorio contiene **dos "
        "paquetes independientes** y ambos contratos deben cumplirse. Los "
        "tests públicos de cada paquete son una guía incompleta; la "
        "especificación ejecutable son las dos partes de este documento.\n\n"
        "## PARTE A\n\n" + ta + "\n\n---\n\n## PARTE B\n\n" + tb + "\n"
    )


def build() -> list[dict]:
    import evals.sd_pilot.tasks as T

    hechos = []
    for i, tid in enumerate(B_TASK_IDS):
        a = B_DOMAINS[i]
        b = B_DOMAINS[(i + 1) % len(B_DOMAINS)]
        dst = task_dir(tid)
        _limpia(dst)
        (dst / "workspace" / "tests_public").mkdir(parents=True)
        (dst / "tests_hidden").mkdir()
        _copia_workspace(task_dir(a) / "workspace", dst / "workspace", "a")
        _copia_workspace(task_dir(b) / "workspace", dst / "workspace", "b")
        ini = task_dir(a) / "workspace" / "pytest.ini"
        if ini.is_file():
            shutil.copy2(ini, dst / "workspace" / "pytest.ini")
        else:
            (dst / "workspace" / "pytest.ini").write_text(
                "[pytest]\npythonpath = .\ntestpaths = tests_public\n",
                encoding="utf-8")
        shutil.copy2(task_dir(a) / "tests_hidden" / "conftest.py",
                     dst / "tests_hidden" / "conftest.py")
        _copia_hidden(task_dir(a) / "tests_hidden", dst / "tests_hidden", "a")
        _copia_hidden(task_dir(b) / "tests_hidden", dst / "tests_hidden", "b")
        for item in (task_dir(a) / "reference").iterdir():
            if item.name == "__pycache__":
                continue
            target = dst / "reference" / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(item, target)
        for item in (task_dir(b) / "reference").iterdir():
            if item.name == "__pycache__":
                continue
            target = dst / "reference" / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True,
                                ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(item, target)
        (dst / "TASK.md").write_text(_task_md(tid, a, b), encoding="utf-8")
        hechos.append({"task": tid, "parte_a": a, "parte_b": b})
        print(f"BUILD {tid}  ({a} + {b})")

    problemas = T.lint_tasks(B_TASK_IDS)
    if problemas:
        raise SystemExit("lint B tras construir:\n" + "\n".join(problemas))
    return hechos


def qa() -> list[dict]:
    import evals.sd_pilot.tasks as T
    res = T.qa_all(B_TASK_IDS)
    QA_OUT.parent.mkdir(parents=True, exist_ok=True)
    QA_OUT.write_text(json.dumps({"tareas": res, "ok": all(r["ok"] for r in res)},
                                 ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8")
    for r in res:
        print(f"QA {r['task']}: ok={r['ok']} ref={r['ref_score']} "
              f"empty_hidden={r['empty_score']} "
              f"empty_public_fail={r['empty_public']['failed']}")
    return res


if __name__ == "__main__":
    hechos = build()
    res = qa()
    sys.exit(0 if all(r["ok"] for r in res) else 1)
