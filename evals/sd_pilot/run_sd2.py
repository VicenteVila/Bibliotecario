#!/usr/bin/env python3
"""Corredor SD-2 (HITO22): calibración dev y corrida oficial test.

Modos:
  --presupuesto   Coste/turnos de antemano (sin LLM) de calibración y oficial.
  --calibracion   12 tareas dev x {A1,A5}, max_turns=12, cap 100k/celda,
                  techo 700k. Gates C1-C4; stop/go antes del oficial.
  --oficial       12 tareas test x A1-A5, max_turns=12, cap 150k/celda,
                  techo 2,8M. Gates U1-U10; exige calibración C1-C4 OK,
                  `SD2_LOCK.json` intacto y Harness Card presente.

Disciplina:
  - `--resume` reanuda celdas ya puntuadas; no repite evidencia.
  - Modelo fijo y fallback al mismo modelo; clave PILOTO para evaluación.
  - El test no se edita: el lock se verifica antes de cada modo con LLM.
  - La calibración es stop/go, no un bucle de endurecimiento.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

SD_ROOT = Path(__file__).resolve().parent
REPO = SD_ROOT.parents[1]
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_TURNS = 12
CAL_CELL_CAP = 100_000
CAL_TECHO = 700_000
OFICIAL_CELL_CAP = 150_000
OFICIAL_TECHO = 2_800_000
CAL_VARIANTS = ("A1", "A5")
OFICIAL_VARIANTS = ("A1", "A2", "A3", "A4", "A5")
SNAP_TURNS = (4, 8, 12)

PRESUPUESTO_BASE_16 = {
    "A1": 5_479,
    "A2": 105_545,
    "A3": 90_278,
    "A4": 127_635,
    "A5": 97_983,
}
PRESUPUESTO_EXPONENTE = 3

WS_CAL = Path("/tmp/opencode/sd2_calibracion")
WS_OFICIAL = Path("/tmp/opencode/sd2_oficial")
STATE_CAL = SD_ROOT / "_run_state_sd2_calibracion.json"
STATE_OFICIAL = SD_ROOT / "_run_state_sd2.json"
TRACES_CAL = SD_ROOT / "traces_sd2_calibracion.sqlite"
TRACES_OFICIAL = SD_ROOT / "traces_sd2.sqlite"
RESULT_CAL = REPO / "evals" / "results" / "result_sd2_calibracion.json"
RESULT_OFICIAL = REPO / "evals" / "results" / "result_sd2.json"
HARNESS_CARD = REPO / "evals" / "HARNESS_CARD_SD2.md"
HEARTBEAT_CAL = SD_ROOT / "_heartbeat_sd2_calibracion.json"
HEARTBEAT_OFICIAL = SD_ROOT / "_heartbeat_sd2.json"

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _load_env(model: str) -> None:
    envf = REPO / ".env"
    if envf.is_file():
        for line in envf.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(
                key.strip(), value.strip().strip('"').strip("'")
            )
    os.environ["LLM_PROVIDERS"] = "nvidia"
    os.environ["NVIDIA_MODEL"] = model
    os.environ["NVIDIA_FALLBACK_MODEL"] = model
    if os.environ.get("NVIDIA_API_KEY_PILOTO"):
        os.environ["NVIDIA_API_KEY"] = os.environ["NVIDIA_API_KEY_PILOTO"]
        log("clave NVIDIA: PILOTO (separada de bibliotecario; valor no mostrado)")
    else:
        log("AVISO: falta NVIDIA_API_KEY_PILOTO en .env — este run usa la "
            "principal compartida con bibliotecario (RPM mezclados)")


def _git_head() -> dict:
    def _sh(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", "-C", str(REPO), *args],
                capture_output=True, text=True, timeout=10, check=False,
            ).stdout.strip()
        except Exception:
            return ""

    return {
        "head": _sh("rev-parse", "HEAD"),
        "dirty": bool(_sh("status", "--porcelain")),
    }


def _write_json(path: Path, obj) -> None:
    from evals.sd_pilot.io_atomico import escribir_texto_atomico

    escribir_texto_atomico(
        path, json.dumps(obj, ensure_ascii=False, indent=1)
    )


def _make_llm():
    from bibliotecario.core import llm as BLLM

    def llm_fn(prompt: str, max_tokens: int) -> str:
        out = BLLM.generate(
            prompt, max_tokens=max_tokens, retries=2, strict_fallback=True
        )
        if not out or not out.strip():
            raise RuntimeError("LLM devolvio vacio")
        return out

    return llm_fn


def _estimar_tokens_celda(base16: int, max_turns: int) -> int:
    return round(base16 * (max_turns / 16) ** PRESUPUESTO_EXPONENTE)


def _proyeccion(
    max_turns: int,
    n_tareas: int,
    variants: tuple[str, ...],
    techo: int,
) -> dict:
    por_variante = {
        name: (
            PRESUPUESTO_BASE_16[name]
            if name == "A1"
            else _estimar_tokens_celda(PRESUPUESTO_BASE_16[name], max_turns)
        )
        for name in variants
    }
    total = sum(por_variante.values()) * n_tareas
    return {
        "max_turns": max_turns,
        "n_tareas": n_tareas,
        "variantes": list(variants),
        "celdas": n_tareas * len(variants),
        "por_variante": por_variante,
        "total": total,
        "techo": techo,
        "cabe": total <= techo,
        "veredicto": "COSTE_OK" if total <= techo else "EXCEDE_TECHO",
    }


def _coste(cells: dict) -> dict:
    total = {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for cell in cells.values():
        usage = cell.get("usage") or {}
        for key in total:
            total[key] += int(usage.get(key) or 0)
    return total


def _variante(name: str):
    from evals.sd_pilot.variants import VARIANTS

    var = VARIANTS[name]
    if var.one_shot:
        return var
    return replace(var, max_turns=MAX_TURNS)


def _run_cell(
    vname: str,
    tid: str,
    tracing_db: Path,
    *,
    ws_root: Path,
    cap: int,
    techo: int,
    spent: int,
    proj_cell: int,
    heartbeat: Path,
) -> dict:
    from bibliotecario.core import llm as BLLM
    from evals.sd_pilot import verifier
    from evals.sd_pilot.harness import Cell
    from evals.sd_pilot.sd2_tasks import task_dir

    td = task_dir(tid)
    var = _variante(vname)
    ws = ws_root / f"{vname}_{tid}"
    BLLM.reset_usage()
    t0 = time.time()

    def _on_turn(info: dict) -> None:
        try:
            _write_json(heartbeat, {
                "celda": f"{vname}_{tid}",
                "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S"),
                **info,
            })
        except OSError as exc:
            log(f"heartbeat: no se pudo escribir {heartbeat.name}: {exc}")

    import traceforge

    token = traceforge.set_metadata_context(
        variant=vname, task=tid, model=os.environ.get("NVIDIA_MODEL", ""),
        run_id=f"{vname}_{tid}",
    )[1]
    try:
        cell = Cell(
            var,
            tid,
            td,
            ws,
            _make_llm(),
            skills_dir=SD_ROOT / "skills_pack",
            tracing=True,
            canal="oficial",
            cell_token_cap=cap,
            snap_turns=SNAP_TURNS,
            ceiling_watch=(spent, proj_cell, techo),
            on_turn=_on_turn,
        )
        res = cell.run()
    finally:
        traceforge.reset_metadata_context(token)

    usage = BLLM.usage_totals()
    score = verifier.hidden_score(ws, td)
    elapsed = round(time.time() - t0, 1)
    infra_error = bool(res.llm_error) or res.stopped_by == "error_llm"
    record = {
        "task": tid,
        "variant": vname,
        "model": MODEL,
        "max_turns": MAX_TURNS,
        "variant_max_turns": var.max_turns,
        "score": score["score"],
        "hidden": {
            "passed": score["passed"],
            "total": score["total"],
        },
        "turns": res.turns,
        "llm_calls": res.llm_calls,
        "tool_calls": res.tool_calls,
        "invalid_actions": res.invalid_actions,
        "pf_fires": res.pf_fires,
        "regulation": res.regulation,
        "stopped_by": res.stopped_by,
        "llm_error": res.llm_error,
        "infra_error": infra_error,
        "errors": res.errors[:8],
        "final": res.final[:300],
        "elapsed_s": elapsed,
        "writes": res.writes,
        "snapshots": res.snapshots,
        "usage": {
            key: usage.get(key)
            for key in (
                "calls",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
            )
        },
    }
    log(
        f"{vname}/{tid}: score={record['score']}% turns={res.turns} "
        f"llm={res.llm_calls} tools={res.tool_calls} writes={res.writes} "
        f"paro={res.stopped_by} tok={usage.get('total_tokens')} {elapsed}s"
        + (f" LLM_ERROR={res.llm_error}" if res.llm_error else "")
    )
    return record


def _run_many(
    pairs: list[tuple[str, str]],
    *,
    tracing_db: Path,
    state_path: Path,
    mode: str,
    ws_root: Path,
    cap: int,
    techo: int,
    proj_by_variant: dict[str, int],
    heartbeat: Path,
    resume: bool,
) -> dict:
    import traceforge

    traceforge.configure(collector="sqlite", db_path=str(tracing_db))
    state: dict = {"mode": mode, "cells": {}}
    if resume and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("mode") not in (None, mode):
            raise RuntimeError(
                f"estado de {state.get('mode')} no sirve para {mode}"
            )
        log(
            f"resume: {len(state.get('cells', {}))} celdas ya puntuadas "
            f"de {state_path.name}"
        )
    cells: dict = state.setdefault("cells", {})
    matrix: dict[str, dict[str, float]] = {}
    for vname, tid in pairs:
        key = f"{vname}_{tid}"
        prior = cells.get(key)
        if (
            prior
            and prior.get("score") is not None
            and not prior.get("infra_error")
        ):
            log(f"{key}: ya puntuada ({prior['score']}%), se omite")
        else:
            spent = _coste(cells)["total_tokens"]
            if spent >= techo:
                log(
                    f"TECHO alcanzado antes de {key}: {spent} >= {techo}; "
                    "no se ejecuta"
                )
                break
            proj = proj_by_variant.get(vname, 0)
            cells[key] = _run_cell(
                vname,
                tid,
                tracing_db,
                ws_root=ws_root,
                cap=cap,
                techo=techo,
                spent=spent,
                proj_cell=proj,
                heartbeat=heartbeat,
            )
            state["mode"] = mode
            _write_json(state_path, state)
        matrix.setdefault(vname, {})[tid] = float(cells[key]["score"])
    return {"matrix": matrix, "cells": cells, "state": state}


def _presupuesto_payload(max_turns: int, n_tareas: int, techo: int) -> dict:
    cal = _proyeccion(
        max_turns, n_tareas, CAL_VARIANTS, techo or CAL_TECHO
    )
    oficial = _proyeccion(
        max_turns, n_tareas, OFICIAL_VARIANTS, OFICIAL_TECHO
    )
    return {
        "modelo": MODEL,
        "max_turns": max_turns,
        "calibracion": cal,
        "oficial": oficial,
        "cabe_calibracion": cal["cabe"],
        "cabe_oficial": oficial["cabe"],
    }


def modo_presupuesto(max_turns: int, n_tareas: int, techo: int) -> int:
    payload = _presupuesto_payload(max_turns, n_tareas, techo)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    log(
        f"calibración: {payload['calibracion']['total']} tok "
        f"(techo {payload['calibracion']['techo']}) "
        f"{payload['calibracion']['veredicto']}"
    )
    log(
        f"oficial: {payload['oficial']['total']} tok "
        f"(techo {payload['oficial']['techo']}) "
        f"{payload['oficial']['veredicto']}"
    )
    return 0 if payload["cabe_calibracion"] and payload["cabe_oficial"] else 2


def _lock_problems() -> list[str]:
    from evals.sd_pilot.sd2_tasks import verify_lock

    return verify_lock()


def _lock_sha256() -> str:
    from evals.sd_pilot.sd2_tasks import LOCK_NAME, sd2_root

    path = sd2_root() / LOCK_NAME
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _abort_if_lock() -> bool:
    problems = _lock_problems()
    if problems:
        log(f"ABORTADO: lock SD-2 con problemas: {problems[:10]}")
        return True
    return False


def modo_calibracion(model: str, resume: bool) -> int:
    _load_env(model)
    if _abort_if_lock():
        return 3
    if resume:
        if not STATE_CAL.is_file():
            log("ERROR: --resume sin estado de calibración previo")
            return 3
    elif STATE_CAL.is_file():
        log(
            f"ERROR: ya existe {STATE_CAL.name}; usa --resume o archiva "
            "el estado documentándolo"
        )
        return 3
    else:
        _write_json(STATE_CAL, {"mode": "calibracion", "cells": {}})
        if TRACES_CAL.exists():
            TRACES_CAL.unlink()

    from evals.sd_pilot.sd2_sens import CAL_TASKS
    from evals.sd_pilot.sd2_tasks import lint_tasks

    problems = lint_tasks(CAL_TASKS)
    if problems:
        log(f"ABORTADO: lint de dev con problemas: {problems[:10]}")
        return 3

    presupuesto = _proyeccion(
        MAX_TURNS, len(CAL_TASKS), CAL_VARIANTS, CAL_TECHO
    )
    if not presupuesto["cabe"]:
        log(f"ABORTADO: proyección {presupuesto['total']} > {CAL_TECHO}")
        return 3

    pairs = [(v, t) for t in CAL_TASKS for v in CAL_VARIANTS]
    log(
        f"calibración SD-2: {len(pairs)} celdas, modelo={model}, "
        f"max_turns={MAX_TURNS}, cap={CAL_CELL_CAP}, techo={CAL_TECHO}"
    )
    run = _run_many(
        pairs,
        tracing_db=TRACES_CAL,
        state_path=STATE_CAL,
        mode="calibracion",
        ws_root=WS_CAL,
        cap=CAL_CELL_CAP,
        techo=CAL_TECHO,
        proj_by_variant=presupuesto["por_variante"],
        heartbeat=HEARTBEAT_CAL,
        resume=resume,
    )

    from evals.sd_pilot.sd2_sens import calibration_gates

    ev = calibration_gates(run["matrix"], run["cells"], CAL_TASKS)
    result = {
        "hito": 22,
        "modo": "calibracion",
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": model,
        "tareas": CAL_TASKS,
        "variantes": list(CAL_VARIANTS),
        "max_turns": MAX_TURNS,
        "cap_por_celda": CAL_CELL_CAP,
        "techo": CAL_TECHO,
        "presupuesto": presupuesto,
        "matriz": run["matrix"],
        "gates": ev["gates"],
        "cumple": ev["cumple"],
        "medias": ev["medias"],
        "diferencia_A1_A5": ev["diferencia_A1_A5"],
        "valid_tasks": ev["valid_tasks"],
        "coste": ev["coste"],
        "celdas": run["cells"],
        "trazas": str(TRACES_CAL.relative_to(REPO)),
        "lock_problems": _lock_problems(),
        "lock_sha256": _lock_sha256(),
        "commits": _git_head(),
    }
    _write_json(RESULT_CAL, result)
    log(f"resultado: {RESULT_CAL.relative_to(REPO)}")
    for name, gate in ev["gates"].items():
        log(f"  gate {name}: {'OK' if gate['ok'] else 'FALLA'} valor={gate['valor']}")
    log(
        f"CALIBRACIÓN CUMPLE={ev['cumple']} "
        f"coste={ev['coste']['total_tokens']} tokens"
    )
    return 0 if ev["cumple"] else 2


def _calibracion_ok() -> bool:
    if not RESULT_CAL.is_file():
        return False
    try:
        result = json.loads(RESULT_CAL.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(
        result.get("cumple")
        and result.get("lock_problems") == []
        and result.get("lock_sha256") == _lock_sha256()
    )


def modo_oficial(model: str, resume: bool) -> int:
    _load_env(model)
    if _abort_if_lock():
        return 3
    if not HARNESS_CARD.is_file():
        log(f"ABORTADO: falta Harness Card {HARNESS_CARD.relative_to(REPO)}")
        return 3
    if not _calibracion_ok():
        log(
            "ABORTADO: calibración C1-C4 no consta como CUMPLE; "
            "no se lanza el oficial"
        )
        return 3
    if resume:
        if not STATE_OFICIAL.is_file():
            log("ERROR: --resume sin estado oficial previo")
            return 3
    elif STATE_OFICIAL.is_file():
        log(
            f"ERROR: ya existe {STATE_OFICIAL.name}; usa --resume o archiva "
            "el estado documentándolo"
        )
        return 3
    else:
        _write_json(STATE_OFICIAL, {"mode": "oficial", "cells": {}})
        if TRACES_OFICIAL.exists():
            TRACES_OFICIAL.unlink()

    from evals.sd_pilot.sd2_sens import OFFICIAL_TASKS
    from evals.sd_pilot.sd2_tasks import lint_tasks

    problems = lint_tasks(OFFICIAL_TASKS)
    if problems:
        log(f"ABORTADO: lint de test con problemas: {problems[:10]}")
        return 3

    presupuesto = _proyeccion(
        MAX_TURNS, len(OFFICIAL_TASKS), OFICIAL_VARIANTS, OFICIAL_TECHO
    )
    if not presupuesto["cabe"]:
        log(f"ABORTADO: proyección {presupuesto['total']} > {OFICIAL_TECHO}")
        return 3

    pairs = [(v, t) for t in OFFICIAL_TASKS for v in OFICIAL_VARIANTS]
    log(
        f"oficial SD-2: {len(pairs)} celdas, modelo={model}, "
        f"max_turns={MAX_TURNS}, cap={OFICIAL_CELL_CAP}, "
        f"techo={OFICIAL_TECHO}"
    )
    run = _run_many(
        pairs,
        tracing_db=TRACES_OFICIAL,
        state_path=STATE_OFICIAL,
        mode="oficial",
        ws_root=WS_OFICIAL,
        cap=OFICIAL_CELL_CAP,
        techo=OFICIAL_TECHO,
        proj_by_variant=presupuesto["por_variante"],
        heartbeat=HEARTBEAT_OFICIAL,
        resume=resume,
    )

    from evals.sd_pilot.sd2_sens import official_gates

    ev = official_gates(
        run["matrix"],
        run["cells"],
        lock_ok=not _lock_problems(),
        harness_card_ok=HARNESS_CARD.is_file(),
        model=model,
    )
    result = {
        "hito": 22,
        "modo": "oficial",
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": model,
        "tareas": OFFICIAL_TASKS,
        "variantes": list(OFICIAL_VARIANTS),
        "max_turns": MAX_TURNS,
        "cap_por_celda": OFICIAL_CELL_CAP,
        "techo": OFICIAL_TECHO,
        "presupuesto": presupuesto,
        "matriz": run["matrix"],
        "q_h": ev["q_h"],
        "spread": ev["spread"],
        "sens": ev["sens"],
        "n_sens_finitos": ev["n_sens_finitos"],
        "n_sens_positivos": ev["n_sens_positivos"],
        "gates": ev["gates"],
        "cumple": ev["cumple"],
        "medias": ev["medias"],
        "A1_lt_100": ev["A1_lt_100"],
        "A5_lt_100": ev["A5_lt_100"],
        "infra_error": ev["infra_error"],
        "varianza": ev["varianza"],
        "ic95": ev["ic95"],
        "coste": ev["coste"],
        "celdas": run["cells"],
        "trazas": str(TRACES_OFICIAL.relative_to(REPO)),
        "lock_problems": _lock_problems(),
        "lock_sha256": _lock_sha256(),
        "commits": _git_head(),
    }
    _write_json(RESULT_OFICIAL, result)
    log(f"resultado: {RESULT_OFICIAL.relative_to(REPO)}")
    for name, gate in ev["gates"].items():
        log(f"  gate {name}: {'OK' if gate['ok'] else 'FALLA'} valor={gate['valor']}")
    log(
        f"OFICIAL CUMPLE={ev['cumple']} coste={ev['coste']['total_tokens']} "
        f"tokens ({len(ev['infra_error'])} celdas con infra_error)"
    )
    return 0 if ev["cumple"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corredor SD-2 (HITO22)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--presupuesto", action="store_true")
    group.add_argument("--calibracion", action="store_true")
    group.add_argument("--oficial", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-turns", type=int, default=MAX_TURNS)
    parser.add_argument("--n-tareas", type=int, default=12)
    parser.add_argument("--techo", type=int, default=0)
    parser.add_argument("--modelo", default=MODEL)
    args = parser.parse_args(argv)

    if args.presupuesto:
        return modo_presupuesto(
            args.max_turns, args.n_tareas, args.techo
        )
    if args.calibracion:
        return modo_calibracion(args.modelo, args.resume)
    return modo_oficial(args.modelo, args.resume)


if __name__ == "__main__":
    raise SystemExit(main())
