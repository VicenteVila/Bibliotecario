#!/usr/bin/env python3
"""
Lint de las suites del scorer Capa B-1 v2 (§5.2.2.c).

Valida la ESTRUCTURA de cada suite de evals/preflight/suites_v2/ contra el
contrato del motor (check_suite_v2.gd) y del runner (suite_runner_v2.py):

  * `task` == nombre del fichero (stem); ids de check únicos
  * kind ∈ conjuntos conocidos (motor + runner); campos requeridos por kind
  * `build` es el primer check; `no_runtime_errors` el último (si está)
  * suma de frames (explícitos o por defecto del motor) ≤ MAX_FRAMES (6000)
  * cobertura: las 52 tareas de evals/game_tasks_expanded.yaml tienen suite

NO ejecuta Godot ni valida contenido semántico: eso lo hace el motor al
correr la suite contra un juego concreto. Uso:

    python evals/preflight/lint_suites_v2.py
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SUITES = HERE / "suites_v2"
TASKS_YAML = ROOT / "evals/game_tasks_expanded.yaml"
MAX_FRAMES = 6000

ENGINE_KINDS = {
    "build", "node_exists", "node_is", "canvas", "label_match", "scene_count",
    "has_method", "collision", "moves", "jump", "camera_follows", "falls",
    "lands", "settles", "hud_value_changes", "state_after_action",
    "wait_accumulates", "reaches_state", "restart_resets",
    "resource_within_bounds", "timing_window",
}
RUNNER_KINDS = {"no_runtime_errors"}
ALL_KINDS = ENGINE_KINDS | RUNNER_KINDS

REQUIRED = {
    "build": [],
    "node_exists": ["names"],
    "node_is": ["names", "is"],
    "canvas": [],
    "label_match": ["text"],
    "scene_count": [],
    "has_method": ["names", "method"],
    "collision": ["names"],
    "moves": [],
    "jump": [],
    "camera_follows": [],
    "falls": [],
    "lands": [],
    "settles": [],
    "hud_value_changes": ["label"],
    "state_after_action": ["names", "property"],
    "wait_accumulates": ["label"],
    "reaches_state": ["texts"],
    "restart_resets": ["watch_label"],
    "resource_within_bounds": [],  # label o property; min o max — abajo
    "timing_window": ["names", "cue_at", "watch_label", "window", "outside"],
    "no_runtime_errors": [],
}

OPTIONAL = {
    "frames", "action", "rise", "min", "max", "property", "label",
    "watch_label", "drive_action", "restart_action", "texts", "cue_op",
    "axis", "names",  # cinéticos y bounds con property resuelven target/nodo
}

BEH_DEFAULT_FRAMES = {
    "moves": 45, "jump": 30, "camera_follows": 90, "falls": 90, "lands": 90,
    "settles": 90, "hud_value_changes": 45, "state_after_action": 45,
    "reaches_state": 320, "restart_resets": 300, "wait_accumulates": 400,
    "resource_within_bounds": 150, "timing_window": 120,
}


def lint_file(path: Path) -> list[str]:
    errs: list[str] = []
    stem = path.stem
    try:
        suite = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return [f"{stem}: YAML inválido — {e}"]
    if not isinstance(suite, dict) or "task" not in suite or "checks" not in suite:
        return [f"{stem}: falta `task` o `checks`"]
    if suite["task"] != stem:
        errs.append(f"{stem}: task={suite['task']!r} != nombre del fichero")
    checks = suite["checks"]
    if not checks:
        errs.append(f"{stem}: sin checks")
        return errs

    ids = [str(c.get("id", "?")) for c in checks]
    dup = [i for i, n in Counter(ids).items() if n > 1]
    if dup:
        errs.append(f"{stem}: ids duplicados {dup}")

    if checks[0].get("kind") != "build":
        errs.append(f"{stem}: el primer check debe ser build")
    if checks[-1].get("kind") == "no_runtime_errors" and len(checks) > 1:
        pass  # orden correcto
    elif any(c.get("kind") == "no_runtime_errors" for c in checks[:-1]):
        errs.append(f"{stem}: no_runtime_errors debe ir el último")

    frames_total = 0
    for c in checks:
        kind = str(c.get("kind", ""))
        cid = str(c.get("id", "?"))
        if kind not in ALL_KINDS:
            errs.append(f"{stem}/{cid}: kind desconocido {kind!r}")
            continue
        for f in REQUIRED.get(kind, []):
            if f not in c:
                errs.append(f"{stem}/{cid}: falta el campo {f!r} (kind {kind})")
        if kind == "resource_within_bounds":
            if "label" not in c and "property" not in c:
                errs.append(f"{stem}/{cid}: resource_within_bounds requiere label o property")
            if "max" not in c and "min" not in c:
                errs.append(f"{stem}/{cid}: resource_within_bounds requiere min o max")
        unknown = set(c) - {"id", "kind", "desc"} - set(REQUIRED.get(kind, [])) - OPTIONAL
        if unknown:
            errs.append(f"{stem}/{cid}: campos no previstos {sorted(unknown)}")
        if kind in BEH_DEFAULT_FRAMES:
            frames_total += int(c.get("frames", BEH_DEFAULT_FRAMES[kind]))
    if frames_total > MAX_FRAMES:
        errs.append(f"{stem}: presupuesto {frames_total} > MAX_FRAMES {MAX_FRAMES}")
    return errs


def main() -> int:
    tasks = yaml.safe_load(TASKS_YAML.read_text(encoding="utf-8"))["suite"]
    expected = {t["id"]: t["family"] for t in tasks}
    files = sorted(SUITES.glob("*.yaml"))
    stems = {f.stem for f in files}

    all_errs: list[str] = []
    for f in files:
        all_errs.extend(lint_file(f))

    missing = sorted(set(expected) - stems)
    if missing:
        all_errs.append(f"sin suite: {missing}")
    extra_real = sorted(
        s for s in stems - set(expected)
        if s not in {"v2-fixture", "v2-compat"}
    )
    if extra_real:
        all_errs.append(f"suites huérfanas: {extra_real}")

    if all_errs:
        print("LINT FAILED")
        for e in all_errs:
            print(f"  - {e}")
        return 1

    fam = Counter(expected[s] for s in expected)
    kinds: Counter = Counter()
    n_checks = 0
    for f in files:
        suite = yaml.safe_load(f.read_text(encoding="utf-8"))
        for c in suite["checks"]:
            kinds[c["kind"]] += 1
            n_checks += 1
    print("LINT PASSED")
    print(f"  suites: {len(files)} (52 reales + 2 de validación)")
    print(f"  checks: {n_checks} en total")
    print(f"  familias (tareas reales): {len(fam)} — " +
          ", ".join(f"{k}={v}" for k, v in sorted(fam.items())))
    print("  kinds usados:")
    for k, n in sorted(kinds.items(), key=lambda x: (-x[1], x[0])):
        print(f"    {k:<26} {n:>3}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
