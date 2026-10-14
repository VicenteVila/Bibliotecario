#!/usr/bin/env python3
"""
Orquestador del scorer Capa B-1 **v2** (2026-10-14 — §5.2.2 y §11).

v2 = v1 + 5 kind's nuevos (hud_value_changes, state_after_action,
wait_accumulates, reaches_state, restart_resets). v1 sigue runnable con
suite_runner.py. Este runner NO modifica a v1.

Qué hace
--------
Para cada tarea de la suite:
  1. copia el workspace del juego a un dir temporal   (ReaGame NO se toca)
  2. escribe `_checks.json` con las features pedidas
  3. ejecuta `godot --headless --script check_suite_v2.gd`
  4. parsea `M = pass/total` y `VALIDATION_PASSED|FAILED`
  5. calcula el Score de Capa B-1

Reglas del benchmark
--------------------
* GameDevBench §2.2 — cada test verifica UNA feature pedida en la instrucción.
* BUILD = 0  →  SCORE = 0  (cero, no techo).
* M = tests que pasan / tests escritos.
* Motor v2 NO congela lo ya congelado: Godot 4.7.1 se mantiene; el archivo
  del motor es nuevo (v2) y v1 queda intacto y runnable.

Uso
---
  python evals/preflight/suite_runner.py                     # todas las tareas
  python evals/preflight/suite_runner.py platformer-juego    # una
  python evals/preflight/suite_runner.py --workspace PATH --task ID
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
SUITES = HERE / "suites_v2"
ENGINE = HERE / "check_suite_v2.gd"

GODOT_CANDIDATES = [
    Path("/mnt/c/EG/.tools/godot"),
    Path("/mnt/c/EG/.tools/godot4"),
]
DEFAULT_WORKSPACE = Path("/mnt/c/EG/workspace/current")


@dataclass
class TaskResult:
    task: str
    m_pass: int = 0
    m_total: int = 0
    validation: str = "FAILED"
    build_ok: bool = False
    score: float = 0.0
    failed: list = field(default_factory=list)
    log: str = ""


def find_godot() -> Path:
    for p in GODOT_CANDIDATES:
        if p.exists():
            return p
    raise SystemExit(
        "No se encontró el binario de Godot. Esperado en:\n  "
        + "\n  ".join(str(p) for p in GODOT_CANDIDATES)
    )


def load_suite(path: Path) -> dict:
    import yaml  # PyYAML

    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_task(godot: Path, workspace: Path, suite: dict, timeout: int = 180) -> TaskResult:
    task_id = suite["task"]
    res = TaskResult(task=task_id)

    tmp = Path(tempfile.mkdtemp(prefix=f"b1v2_{task_id}_"))
    try:
        # 1. copia del juego — ReaGame queda intacto
        for item in workspace.iterdir():
            dst = tmp / item.name
            if item.is_dir():
                shutil.copytree(item, dst)
            else:
                shutil.copy2(item, dst)

        # 2. configuración de checks
        (tmp / "_checks.json").write_text(
            json.dumps({"task": task_id, "checks": suite["checks"]}, ensure_ascii=False),
            encoding="utf-8",
        )

        # 3. copia del motor al dir temporal (Godot sólo carga res://)
        shutil.copy2(ENGINE, tmp / "check_suite_v2.gd")

        # 4. ejecución
        try:
            proc = subprocess.run(
                [str(godot), "--headless", "--path", str(tmp), "--script", "check_suite_v2.gd"],
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired as e:
            # el motor debe poder colgarse CERO; si aun así pasa, se declara
            out = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
            res.log = out
            res.validation = "TIMEOUT"
            res.failed = ["_timeout"]
            print(f"   TIMEOUT tras {timeout}s — el motor no terminó")
            return res
        res.log = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")

        # 5. parseo
        m = re.search(r"=== M = (\d+)/(\d+) ===", proc.stdout)
        if m:
            res.m_pass, res.m_total = int(m.group(1)), int(m.group(2))
        if "VALIDATION_PASSED" in proc.stdout:
            res.validation = "PASSED"
        if re.search(r"\[FAIL\] (\S+)", proc.stdout):
            res.failed = re.findall(r"\[FAIL\] (\S+)", proc.stdout)
        if "BUILD = 0" in proc.stdout:
            res.build_ok = False
            res.score = 0.0
            return res

        res.build_ok = res.m_total > 0
        # BUILD gate: sin escena cargable → 0
        if not res.build_ok:
            res.score = 0.0
            return res

        # Capa B-1: Score = BUILD × M   (D/V/A esperan a B-2)
        res.score = round(100.0 * res.m_pass / res.m_total, 2)
        return res
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Scorer Capa B-1 v2 — tests de comportamiento en Godot (v1 + kind's v2)")
    ap.add_argument("task", nargs="?", help="id de tarea (omitir = todas)")
    ap.add_argument("--workspace", default=str(DEFAULT_WORKSPACE), help="workspace del juego")
    ap.add_argument("--suites", default=str(SUITES), help="dir con las suites .yaml")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    args = ap.parse_args()

    godot = find_godot()
    ws = Path(args.workspace)
    if not (ws / "project.godot").exists():
        raise SystemExit(f"No hay project.godot en {ws}")

    suite_dir = Path(args.suites)
    files = sorted(suite_dir.glob("*.yaml"))
    if args.task:
        files = [f for f in files if f.stem == args.task]
        if not files:
            raise SystemExit(f"No existe la suite {args.task}.yaml en {suite_dir}")

    results: list[TaskResult] = []
    for f in files:
        suite = load_suite(f)
        print(f"\n── {suite['task']} ──")
        r = run_task(godot, ws, suite)
        results.append(r)
        print(f"   M = {r.m_pass}/{r.m_total}   BUILD={'ok' if r.build_ok else '0'}   "
              f"VALIDATION_{r.validation}   Score={r.score}")
        if r.failed:
            print(f"   fallan: {', '.join(r.failed)}")

    if len(results) > 1:
        print("\n[AVISO] Un workspace contiene UN juego, no ocho.")
        print("        Ejecutar todas las suites contra el mismo workspace es una")
        print("        PRUEBA DEL CORREDOR, no una medición. Uso correcto:")
        print("        generar el juego para la tarea X → correr SOLO esa suite X.")

    if args.json:
        print(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2))
        return 0

    print("\n" + "=" * 62)
    print("CAPA B-1 v2 · RESULTADO POR TAREA")
    print("=" * 62)
    print(f"{'tarea':<24} {'M':>8} {'BUILD':>6} {'VALID':>8} {'Score':>8}")
    print("-" * 62)
    for r in results:
        print(f"{r.task:<24} {r.m_pass:>3}/{r.m_total:<4} "
              f"{'ok' if r.build_ok else '0':>6} {r.validation:>8} {r.score:>8.2f}")
    total_pass = sum(r.m_pass for r in results)
    total = sum(r.m_total for r in results)
    print("-" * 62)
    print(f"{'AGREGADO':<24} {total_pass:>3}/{total:<4} {'':>6} {'':>8} "
          f"{(100.0 * total_pass / total if total else 0):>8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
