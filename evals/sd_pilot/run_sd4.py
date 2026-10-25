#!/usr/bin/env python3
"""Corredor SD-4 (HITO24): probe de cola larga.

Modos:
  --presupuesto  Coste/turnos del probe (sin LLM).
  --probe        3 tareas desechables x {A1,A5}, max_turns=16, cap 70k,
                 techo 250k. A5 en canal b2. Gates R1-R6.

El probe no construye las 24 tareas: solo decide si existe headroom limpio.
Si R1-R6 no se cumplen, H24 cierra NO CUMPLE y no se lanza nada más.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

SD_ROOT = Path(__file__).resolve().parent
REPO = SD_ROOT.parents[1]
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_TURNS = 16
CELL_CAP = 70_000
TECHO = 250_000
VARIANTS = ("A1", "A5")
SNAP_TURNS = (4, 8, 12, 16)

WS_PROBE = Path("/tmp/opencode/sd4_probe")
STATE_PROBE = SD_ROOT / "_run_state_sd4_probe.json"
TRACES_PROBE = SD_ROOT / "traces_sd4_probe.sqlite"
RESULT_PROBE = REPO / "evals" / "results" / "result_sd4_probe.json"
HEARTBEAT_PROBE = SD_ROOT / "_heartbeat_sd4_probe.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import evals.sd_pilot.sd3_tasks as _old_tasks
from evals.sd_pilot import run_sd3 as base
from evals.sd_pilot import sd4_sens, sd4_tasks

base.MAX_TURNS = MAX_TURNS
base.CELL_CAP = CELL_CAP
base.TECHO = TECHO
base.VARIANTS = VARIANTS
base.SNAP_TURNS = SNAP_TURNS
base.PRESUPUESTO_BASE_16["A5"] = 70_000
base.WS_PROBE = WS_PROBE
base.STATE_PROBE = STATE_PROBE
base.TRACES_PROBE = TRACES_PROBE
base.RESULT_PROBE = RESULT_PROBE
base.HEARTBEAT_PROBE = HEARTBEAT_PROBE
_old_tasks.task_dir = sd4_tasks.task_dir

log = base.log


def _lock_sha256() -> str:
    path = SD_ROOT / sd4_tasks.LOCK_NAME
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def modo_presupuesto(max_turns: int, n_tareas: int, techo: int) -> int:
    payload = base._proyeccion(max_turns, n_tareas, techo or TECHO)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    log(
        f"probe: {payload['total']} tok (techo {payload['techo']}) "
        f"{payload['veredicto']}"
    )
    return 0 if payload["cabe"] else 2


def modo_probe(model: str, resume: bool) -> int:
    base._load_env(model)
    problems = sd4_tasks.verify_lock()
    if problems:
        log(f"ABORTADO: lock SD-4 con problemas: {problems[:10]}")
        return 3
    if resume:
        if not STATE_PROBE.is_file():
            log("ERROR: --resume sin estado de probe previo")
            return 3
    elif STATE_PROBE.is_file():
        log(
            f"ERROR: ya existe {STATE_PROBE.name}; usa --resume o archiva "
            "el estado documentándolo"
        )
        return 3
    else:
        base._write_json(STATE_PROBE, {"mode": "probe", "cells": {}})
        if TRACES_PROBE.exists():
            TRACES_PROBE.unlink()

    lint = sd4_tasks.lint_tasks(sd4_tasks.SD4_PROBE_TASK_IDS)
    if lint:
        log(f"ABORTADO: lint del probe con problemas: {lint[:10]}")
        return 3
    qa = sd4_tasks.qa_all(sd4_tasks.SD4_PROBE_TASK_IDS)
    if not all(item["ok"] for item in qa):
        log(f"ABORTADO: QA del probe con problemas: {qa}")
        return 3

    presupuesto = base._proyeccion(
        MAX_TURNS, len(sd4_tasks.SD4_PROBE_TASK_IDS), sd4_sens.PROBE_TECHO
    )
    if not presupuesto["cabe"]:
        log(
            f"ABORTADO: proyección {presupuesto['total']} > "
            f"{sd4_sens.PROBE_TECHO}"
        )
        return 3

    pairs = [
        (v, t) for t in sd4_tasks.SD4_PROBE_TASK_IDS for v in VARIANTS
    ]
    log(
        f"probe SD-4: {len(pairs)} celdas, modelo={model}, "
        f"max_turns={MAX_TURNS}, cap={CELL_CAP}, "
        f"techo={sd4_sens.PROBE_TECHO}, canal A5=b2"
    )
    run = base._run_many(
        pairs,
        state_path=STATE_PROBE,
        cap=CELL_CAP,
        techo=sd4_sens.PROBE_TECHO,
        proj_by_variant=presupuesto["por_variante"],
        resume=resume,
    )

    ev = sd4_sens.probe_gates(
        run["matrix"],
        run["cells"],
        sd4_tasks.SD4_PROBE_TASK_IDS,
        techo=sd4_sens.PROBE_TECHO,
        max_turns=MAX_TURNS,
    )
    result = {
        "hito": 24,
        "modo": "probe",
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": model,
        "tareas": sd4_tasks.SD4_PROBE_TASK_IDS,
        "variantes": list(VARIANTS),
        "max_turns": MAX_TURNS,
        "cap_por_celda": CELL_CAP,
        "techo": sd4_sens.PROBE_TECHO,
        "presupuesto": presupuesto,
        "qa": qa,
        "matriz": run["matrix"],
        "gates": ev["gates"],
        "cumple": ev["cumple"],
        "medias": ev["medias"],
        "diferencia_A1_A5": ev["diferencia_A1_A5"],
        "A1_lt_100": ev["A1_lt_100"],
        "A5_lt_100": ev["A5_lt_100"],
        "A5_ge_80": ev["A5_ge_80"],
        "A5_writes": ev["A5_writes"],
        "A5_not_stuck": ev["A5_not_stuck"],
        "valid_tasks": ev["valid_tasks"],
        "coste": ev["coste"],
        "celdas": run["cells"],
        "trazas": str(TRACES_PROBE.relative_to(REPO)),
        "lock_problems": sd4_tasks.verify_lock(),
        "lock_sha256": _lock_sha256(),
        "commits": base._git_head(),
    }
    base._write_json(RESULT_PROBE, result)
    log(f"resultado: {RESULT_PROBE.relative_to(REPO)}")
    for name, gate in ev["gates"].items():
        log(
            f"  gate {name}: {'OK' if gate['ok'] else 'FALLA'} "
            f"valor={gate['valor']}"
        )
    log(
        f"PROBE CUMPLE={ev['cumple']} "
        f"coste={ev['coste']['total_tokens']} tokens"
    )
    return 0 if ev["cumple"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corredor SD-4 (HITO24)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--presupuesto", action="store_true")
    group.add_argument("--probe", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument("--n-tareas", type=int, default=3)
    parser.add_argument("--techo", type=int, default=0)
    parser.add_argument("--modelo", default=MODEL)
    args = parser.parse_args(argv)

    if args.presupuesto:
        return modo_presupuesto(args.max_turns, args.n_tareas, args.techo)
    return modo_probe(args.modelo, args.resume)


if __name__ == "__main__":
    raise SystemExit(main())
