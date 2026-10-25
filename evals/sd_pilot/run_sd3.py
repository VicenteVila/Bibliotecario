#!/usr/bin/env python3
"""Corredor SD-3 (HITO23): probe de constructo.

Modos:
  --presupuesto  Coste/turnos del probe (sin LLM).
  --probe        3 tareas desechables x {A1,A5}, max_turns=12, cap 80k,
                 techo 250k. A5 en canal b2. Gates P1-P5.

El probe no construye las 24 tareas: solo decide si existe headroom. Si P1-P5
no se cumplen, H23 cierra NO CUMPLE y no se lanza nada más.
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
CELL_CAP = 80_000
TECHO = 250_000
VARIANTS = ("A1", "A5")
SNAP_TURNS = (4, 8, 12)

PRESUPUESTO_BASE_16 = {
    "A1": 5_479,
    "A5": 97_983,
}
PRESUPUESTO_EXPONENTE = 3

WS_PROBE = Path("/tmp/opencode/sd3_probe")
STATE_PROBE = SD_ROOT / "_run_state_sd3_probe.json"
TRACES_PROBE = SD_ROOT / "traces_sd3_probe.sqlite"
RESULT_PROBE = REPO / "evals" / "results" / "result_sd3_probe.json"
HEARTBEAT_PROBE = SD_ROOT / "_heartbeat_sd3_probe.json"

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
    os.environ["BIBLIOTECARIO_CANAL_B_VERSION"] = "b2"
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


def _proyeccion(max_turns: int, n_tareas: int, techo: int) -> dict:
    por_variante = {
        name: (
            PRESUPUESTO_BASE_16[name]
            if name == "A1"
            else _estimar_tokens_celda(PRESUPUESTO_BASE_16[name], max_turns)
        )
        for name in VARIANTS
    }
    total = sum(por_variante.values()) * n_tareas
    return {
        "max_turns": max_turns,
        "n_tareas": n_tareas,
        "variantes": list(VARIANTS),
        "celdas": n_tareas * len(VARIANTS),
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
    from evals.sd_pilot.variants import VARIANTS as VARS

    var = VARS[name]
    if var.one_shot:
        return var
    return replace(var, max_turns=MAX_TURNS)


def _run_cell(
    vname: str,
    tid: str,
    *,
    cap: int,
    techo: int,
    spent: int,
    proj_cell: int,
) -> dict:
    from bibliotecario.core import llm as BLLM
    from evals.sd_pilot import verifier
    from evals.sd_pilot.harness import Cell
    from evals.sd_pilot.sd3_tasks import task_dir

    td = task_dir(tid)
    var = _variante(vname)
    ws = WS_PROBE / f"{vname}_{tid}"
    BLLM.reset_usage()
    t0 = time.time()

    def _on_turn(info: dict) -> None:
        try:
            _write_json(HEARTBEAT_PROBE, {
                "celda": f"{vname}_{tid}",
                "actualizado": time.strftime("%Y-%m-%dT%H:%M:%S"),
                **info,
            })
        except OSError as exc:
            log(f"heartbeat: no se pudo escribir {HEARTBEAT_PROBE.name}: {exc}")

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
            canal="b",
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
        "canal": "b2" if not var.one_shot else "one_shot",
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
    state_path: Path,
    cap: int,
    techo: int,
    proj_by_variant: dict[str, int],
    resume: bool,
) -> dict:
    import traceforge

    traceforge.configure(collector="sqlite", db_path=str(TRACES_PROBE))
    state: dict = {"mode": "probe", "cells": {}}
    if resume and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if state.get("mode") not in (None, "probe"):
            raise RuntimeError(
                f"estado de {state.get('mode')} no sirve para probe"
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
                cap=cap,
                techo=techo,
                spent=spent,
                proj_cell=proj,
            )
            _write_json(state_path, state)
        matrix.setdefault(vname, {})[tid] = float(cells[key]["score"])
    return {"matrix": matrix, "cells": cells, "state": state}


def _lock_problems() -> list[str]:
    from evals.sd_pilot.sd3_tasks import verify_lock

    return verify_lock()


def _lock_sha256() -> str:
    from evals.sd_pilot.sd3_tasks import LOCK_NAME, sd3_root

    path = sd3_root() / LOCK_NAME
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _abort_if_lock() -> bool:
    problems = _lock_problems()
    if problems:
        log(f"ABORTADO: lock SD-3 con problemas: {problems[:10]}")
        return True
    return False


def modo_presupuesto(max_turns: int, n_tareas: int, techo: int) -> int:
    payload = _proyeccion(max_turns, n_tareas, techo or TECHO)
    print(json.dumps(payload, ensure_ascii=False, indent=1))
    log(
        f"probe: {payload['total']} tok (techo {payload['techo']}) "
        f"{payload['veredicto']}"
    )
    return 0 if payload["cabe"] else 2


def modo_probe(model: str, resume: bool) -> int:
    _load_env(model)
    if _abort_if_lock():
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
        _write_json(STATE_PROBE, {"mode": "probe", "cells": {}})
        if TRACES_PROBE.exists():
            TRACES_PROBE.unlink()

    from evals.sd_pilot.sd3_sens import PROBE_TECHO
    from evals.sd_pilot.sd3_tasks import (
        SD3_PROBE_TASK_IDS,
        lint_tasks,
        qa_all,
    )

    problems = lint_tasks(SD3_PROBE_TASK_IDS)
    if problems:
        log(f"ABORTADO: lint del probe con problemas: {problems[:10]}")
        return 3
    qa = qa_all(SD3_PROBE_TASK_IDS)
    if not all(item["ok"] for item in qa):
        log(f"ABORTADO: QA del probe con problemas: {qa}")
        return 3

    presupuesto = _proyeccion(MAX_TURNS, len(SD3_PROBE_TASK_IDS), PROBE_TECHO)
    if not presupuesto["cabe"]:
        log(f"ABORTADO: proyección {presupuesto['total']} > {PROBE_TECHO}")
        return 3

    pairs = [(v, t) for t in SD3_PROBE_TASK_IDS for v in VARIANTS]
    log(
        f"probe SD-3: {len(pairs)} celdas, modelo={model}, "
        f"max_turns={MAX_TURNS}, cap={CELL_CAP}, techo={PROBE_TECHO}, canal A5=b2"
    )
    run = _run_many(
        pairs,
        state_path=STATE_PROBE,
        cap=CELL_CAP,
        techo=PROBE_TECHO,
        proj_by_variant=presupuesto["por_variante"],
        resume=resume,
    )

    from evals.sd_pilot.sd3_sens import probe_gates

    ev = probe_gates(
        run["matrix"], run["cells"], SD3_PROBE_TASK_IDS,
        techo=PROBE_TECHO, max_turns=MAX_TURNS,
    )
    result = {
        "hito": 23,
        "modo": "probe",
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": model,
        "tareas": SD3_PROBE_TASK_IDS,
        "variantes": list(VARIANTS),
        "max_turns": MAX_TURNS,
        "cap_por_celda": CELL_CAP,
        "techo": PROBE_TECHO,
        "presupuesto": presupuesto,
        "qa": qa,
        "matriz": run["matrix"],
        "gates": ev["gates"],
        "cumple": ev["cumple"],
        "medias": ev["medias"],
        "diferencia_A1_A5": ev["diferencia_A1_A5"],
        "A1_lt_100": ev["A1_lt_100"],
        "A5_lt_100": ev["A5_lt_100"],
        "A5_writes": ev["A5_writes"],
        "A5_not_stuck": ev["A5_not_stuck"],
        "valid_tasks": ev["valid_tasks"],
        "coste": ev["coste"],
        "celdas": run["cells"],
        "trazas": str(TRACES_PROBE.relative_to(REPO)),
        "lock_problems": _lock_problems(),
        "lock_sha256": _lock_sha256(),
        "commits": _git_head(),
    }
    _write_json(RESULT_PROBE, result)
    log(f"resultado: {RESULT_PROBE.relative_to(REPO)}")
    for name, gate in ev["gates"].items():
        log(f"  gate {name}: {'OK' if gate['ok'] else 'FALLA'} valor={gate['valor']}")
    log(
        f"PROBE CUMPLE={ev['cumple']} "
        f"coste={ev['coste']['total_tokens']} tokens"
    )
    return 0 if ev["cumple"] else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Corredor SD-3 (HITO23)")
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
