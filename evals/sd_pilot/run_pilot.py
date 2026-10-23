#!/usr/bin/env python3
"""Corredor del piloto HITO19 (Sens(x)) y del diagnóstico HITO20 (§0.1).

Modos:
  --g0       G0 humo (§1.7 HITO19): 2 tareas x {A1,A5} -> dictámen de arranque.
  --oficial  Corrida oficial ÚNICA de HITO19: 5 variantes x 12 tareas -> gates.
  --diagnostico  Diagnóstico HITO20 §0.1: celdas truncadas con max_turns=32
             (techo 450k, salidas propias, NO toca nada del oficial).
  --debug-celda A2:tarea   Una celda suelta, SOLO para BUILD (nunca es evidencia).

Disciplina:
  - La corrida oficial se lanza UNA sola vez; `--resume` reanuda celdas ya
    puntuadas sin repetirlas (queda en el log y en el estado por celda).
  - Modelo fijo: NVIDIA_MODEL se fuerza al nemotron del plan y
    NVIDIA_FALLBACK_MODEL = mismo modelo (sin mezcla dentro del proveedor).
  - Env se carga ANTES de importar bibliotecario (config lee env al importar).

Uso (con red y .env en la raíz):
  .venv/bin/python evals/sd_pilot/run_pilot.py --g0 \
      > evals/logs/sens_sd_g0.log 2>&1
  setsid .venv/bin/python evals/sd_pilot/run_pilot.py --oficial --resume \
      > evals/logs/sens_sd_pilot_run.log 2>&1 < /dev/null &
  setsid .venv/bin/python evals/sd_pilot/run_pilot.py --diagnostico \
      > evals/logs/sens_sd_diag_run.log 2>&1 < /dev/null &
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

SD_ROOT = Path(__file__).resolve().parent
REPO = SD_ROOT.parents[1]
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"  # §1.5: dueño 2026-10-22 antes de medir
G0_TASKS = ["checkout-rounding", "dsl-parser"]
TECHO_TOKENS = 7_000_000  # §1.8: enmienda 2026-10-22 (dueño, tras G0, N=12 intacto)
STATE_OFICIAL = SD_ROOT / "_run_state_oficial.json"
TRACES_OFICIAL = SD_ROOT / "traces.sqlite"
TRACES_OTROS = SD_ROOT / "traces_g0.sqlite"

# Diagnóstico HITO20 §0.1 (declarado 2026-10-23 ANTES de correr)
DIAG_MAX_TURNS = 32
DIAG_CELLS: list[tuple[str, str]] = [("A2", "plugin-registry"),
                                     ("A5", "repo-cache-layer")]
DIAG_CANDIDATES_EXTRA: list[tuple[str, str]] = [("A5", "workflow-statemachine")]
DIAG_TECHO_TOKENS = 450_000
WS_DIAG = Path("/tmp/opencode/sd_pilot_diag")
STATE_DIAG = SD_ROOT / "_run_state_diag.json"
TRACES_DIAG = SD_ROOT / "traces_diag.sqlite"
RESULT_DIAG = REPO / "evals" / "results" / "result_sens_sd_diag.json"
RESULT_OFICIAL = REPO / "evals" / "results" / "result_sens_sd_pilot.json"

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
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    os.environ["LLM_PROVIDERS"] = "nvidia"
    os.environ["NVIDIA_MODEL"] = model
    os.environ["NVIDIA_FALLBACK_MODEL"] = model  # modelo fijo, sin mezcla (§1.5)


def _git_head() -> dict:
    def _sh(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(REPO), *args],
                                  capture_output=True, text=True, timeout=10,
                                  check=False).stdout.strip()
        except Exception:
            return ""
    return {"head": _sh("rev-parse", "HEAD"),
            "dirty": bool(_sh("status", "--porcelain"))}


def _make_llm():
    from bibliotecario.core import llm as BLLM

    def llm_fn(prompt: str, max_tokens: int) -> str:
        out = BLLM.generate(prompt, max_tokens=max_tokens, retries=2,
                            strict_fallback=True)
        if not out or not out.strip():
            raise RuntimeError("LLM devolvio vacio")
        return out
    return llm_fn


def _run_cell(vname: str, tid: str, tracing_db: Path,
              ws_root: Path | None = None,
              variant=None) -> dict:
    """Ejecuta UNA celda completa y devuelve su registro (score incluido).

    `ws_root` y `variant` solo los usa el diagnóstico HITO20 (§0.1): workspaces
    propios y, opcionalmente, la variante con `max_turns` ampliado.
    """
    from bibliotecario.core import llm as BLLM
    from evals.sd_pilot import verifier
    from evals.sd_pilot.harness import Cell
    from evals.sd_pilot.tasks import task_dir
    from evals.sd_pilot.variants import VARIANTS

    td = task_dir(tid)
    var = variant if variant is not None else VARIANTS[vname]
    ws = (ws_root or Path("/tmp/opencode/sd_pilot_runs")) / f"{vname}_{tid}"
    BLLM.reset_usage()
    t0 = time.time()

    import traceforge
    token = traceforge.set_metadata_context(
        variant=vname, task=tid, model=os.environ.get("NVIDIA_MODEL", ""),
        run_id=f"{vname}_{tid}")[1]
    try:
        cell = Cell(var, tid, td, ws, _make_llm(),
                    skills_dir=SD_ROOT / "skills_pack", tracing=True)
        res = cell.run()
    finally:
        traceforge.reset_metadata_context(token)

    usage = BLLM.usage_totals()
    score = verifier.hidden_score(ws, td)
    elapsed = round(time.time() - t0, 1)
    reg = {"score": score["score"], "hidden": {"passed": score["passed"],
           "total": score["total"]}, "turns": res.turns,
           "max_turns": var.max_turns,
           "llm_calls": res.llm_calls, "tool_calls": res.tool_calls,
           "invalid_actions": res.invalid_actions, "pf_fires": res.pf_fires,
           "regulation": res.regulation, "stopped_by": res.stopped_by,
           "llm_error": res.llm_error, "errors": res.errors[:8],
           "final": res.final[:300], "elapsed_s": elapsed,
           "usage": {k: usage.get(k) for k in
                     ("calls", "prompt_tokens", "completion_tokens", "total_tokens")}}
    log(f"{vname}/{tid}: score={reg['score']}% turns={res.turns} "
        f"llm={res.llm_calls} tools={res.tool_calls} paro={res.stopped_by} "
        f"tok={usage.get('total_tokens')} {elapsed}s"
        + (f" LLM_ERROR={res.llm_error}" if res.llm_error else ""))
    return reg


def _run_many(pairs: list[tuple[str, str]], tracing_db: Path,
              state_path: Path | None = None, resume: bool = False) -> dict:
    """Ejecuta pares (variante, tarea); con state_path reanuda y persiste."""
    import traceforge
    traceforge.configure(collector="sqlite", db_path=str(tracing_db))

    matrix: dict[str, dict[str, float]] = {}
    cells: dict[str, dict] = {}
    state: dict = {}
    if resume and state_path and state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        cells = state.get("cells", {})
        log(f"resume: {len(cells)} celdas ya puntuadas cargadas de {state_path.name}")

    for vname, tid in pairs:
        key = f"{vname}_{tid}"
        if key in cells and cells[key].get("score") is not None:
            log(f"{key}: ya puntuada ({cells[key]['score']}%), se omite")
        else:
            if tracing_db.exists() and not resume and state_path is None:
                pass  # G0/debug: trazas del intento anterior se conservan aparte
            cells[key] = _run_cell(vname, tid, tracing_db)
            if state_path:
                state["cells"] = cells
                state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        matrix.setdefault(vname, {})[tid] = float(cells[key]["score"])
    return {"matrix": matrix, "cells": cells}


def _coste(cells: dict[str, dict]) -> dict:
    tot = {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for c in cells.values():
        u = c.get("usage") or {}
        for k in tot:
            tot[k] += int(u.get(k) or 0)
    return tot


def _veredicto_g0(matrix: dict[str, dict[str, float]], cells: dict) -> dict:
    """§1.7: dictámen de arranque a partir de las 4 celdas de humo."""
    a1 = [matrix.get("A1", {}).get(t, 0.0) for t in G0_TASKS]
    a5 = [matrix.get("A5", {}).get(t, 0.0) for t in G0_TASKS]
    a1m = sum(a1) / len(a1)
    a5m = sum(a5) / len(a5)
    if a5m == 0.0:
        ventana = "ESCALAR_MODELO"   # techo: A5 no rinde nada -> probar ultra
    elif a1m == 100.0 and a5m == 100.0:
        ventana = "ENDURECER_TAREA"  # sin techo: ambas al 100
    elif a5m > a1m:
        ventana = "VENTANA_OK"       # el arnés aporta en la ventana medida
    else:
        ventana = "VENTANA_FALLA"    # A1 >= A5: el arnés no aporta

    coste = _coste(cells)
    por_celda = coste["total_tokens"] / max(len(cells), 1)
    proj60 = int(por_celda * 60)
    proj40 = int(por_celda * 40)  # N=8 tareas -> 40 celdas
    if proj60 <= TECHO_TOKENS:
        coste_verdict, n_final = "COSTE_OK", 12
    elif proj40 <= TECHO_TOKENS:
        coste_verdict, n_final = "REDUCIR_N_8", 8
    else:
        coste_verdict, n_final = "NO_ARRANCA", 0

    arranca = ventana in ("VENTANA_OK", "ENDURECER_TAREA") and coste_verdict != "NO_ARRANCA"
    return {"ventana": ventana, "a1_media": round(a1m, 2), "a5_media": round(a5m, 2),
            "coste": coste_verdict, "tokens_por_celda": int(por_celda),
            "proyeccion_60": proj60, "proyeccion_40": proj40,
            "techo_tokens": TECHO_TOKENS, "n_final": n_final,
            "arranca_oficial": arranca}


def modo_g0(model: str) -> int:
    _load_env(model)
    pairs = [(v, t) for t in G0_TASKS for v in ("A1", "A5")]
    log(f"G0 humo (§1.7): {pairs}")
    run = _run_many(pairs, TRACES_OTROS)
    ver = _veredicto_g0(run["matrix"], run["cells"])
    result = {"hito": 19, "modo": "g0", "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "modelo": model, "tareas": G0_TASKS, "matriz": run["matrix"],
              "dictamen": ver, "celdas": run["cells"], "commits": _git_head()}
    out = REPO / "evals" / "results" / "result_sens_sd_g0.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"DICTAMEN G0: ventana={ver['ventana']} coste={ver['coste']} "
        f"(proj60={ver['proyeccion_60']}, techo={TECHO_TOKENS}) "
        f"n_final={ver['n_final']} arranca={ver['arranca_oficial']}")
    log(f"evidencia: {out.relative_to(REPO)}")
    return 0 if ver["arranca_oficial"] else 2


def modo_oficial(model: str, resume: bool) -> int:
    _load_env(model)
    if resume:
        if not STATE_OFICIAL.is_file():
            log("ERROR: --resume sin estado previo; no hay corrida que reanudar")
            return 3
    elif STATE_OFICIAL.is_file():
        log(f"ERROR: ya existe {STATE_OFICIAL.name} de una corrida previa. "
            "Usa --resume (misma corrida) o archiva el estado documentándolo.")
        return 3
    else:
        STATE_OFICIAL.write_text(json.dumps({"cells": {}}, indent=1), encoding="utf-8")
        if TRACES_OFICIAL.exists():
            TRACES_OFICIAL.unlink()  # corrida fresca: trazas propias, sin mezcla

    from evals.sd_pilot.tasks import TASK_IDS, lint_tasks
    from evals.sd_pilot.variants import VARIANT_NAMES

    problems = lint_tasks()
    if problems:
        log(f"ABORTADO: lint de fixtures con problemas: {problems}")
        return 3

    pairs = [(v, t) for v in VARIANT_NAMES for t in TASK_IDS]
    log(f"corrida oficial HITO19: {len(pairs)} celdas, modelo={model}")
    run = _run_many(pairs, TRACES_OFICIAL, state_path=STATE_OFICIAL, resume=resume)

    matrix, cells = run["matrix"], run["cells"]
    _emit_resultado(model, matrix, cells)
    faltan = [f"{v}_{t}" for v in VARIANT_NAMES for t in TASK_IDS
              if matrix.get(v, {}).get(t) is None]
    if faltan:
        log(f"INCOMPLETO: faltan celdas {faltan}; reanuda con --resume")
        return 3
    return 0


def _emit_resultado(model: str, matrix: dict, cells: dict) -> None:
    from evals.sd_pilot import sens
    from evals.sd_pilot.tasks import TASK_IDS
    from evals.sd_pilot.variants import VARIANT_NAMES, VARIANTS

    r = sens.compute(matrix, TASK_IDS, VARIANT_NAMES)
    u1_ok = tuple(VARIANTS) == VARIANT_NAMES and len(VARIANTS) == 5
    gates = {"U1": {"ok": u1_ok, "valor": list(VARIANT_NAMES),
                    "umbral": "5 variantes congeladas A1-A5"}, **r["gates"]}
    coste = _coste(cells)
    llm_errors = [k for k, c in cells.items() if c.get("llm_error")]
    result = {
        "hito": 19, "modo": "oficial", "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "modelo": model, "variantes": {v: VARIANTS[v].subsystems for v in VARIANT_NAMES},
        "tareas": TASK_IDS, "matriz": matrix, "q_h": r["q_h"], "spread": r["spread"],
        "sens": r["sens"], "n_sens_finitos": r["n_finitos"],
        "n_sens_positivos": r["n_positivos"], "gates": gates,
        "cumple": all(g["ok"] for g in gates.values()),
        "celdas_llm_error": llm_errors, "coste": coste,
        "celdas": cells, "trazas": str(TRACES_OFICIAL.relative_to(REPO)),
        "commits": _git_head(),
    }
    out = REPO / "evals" / "results" / "result_sens_sd_pilot.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"resultado: {out.relative_to(REPO)}")
    log(f"Q_h={r['q_h']} spread={r['spread']}")
    log(f"Sens(x) finitos={r['n_finitos']}/12 positivos={r['n_positivos']}/12")
    for name, g in gates.items():
        log(f"  gate {name}: {'OK' if g['ok'] else 'FALLA'} valor={g['valor']}")
    log(f"CUMPLE={result['cumple']} coste_total={coste['total_tokens']} tokens "
        f"({len(llm_errors)} celdas con error de LLM)")


def modo_debug_celda(spec: str, model: str) -> int:
    _load_env(model)
    if ":" not in spec:
        log("ERROR: --debug-celda espera VARIANTE:tarea")
        return 3
    v, t = spec.split(":", 1)
    import traceforge
    traceforge.configure(collector="sqlite", db_path=str(TRACES_OTROS))
    reg = _run_cell(v, t, TRACES_OTROS)
    log(f"BUILD (no es evidencia): {json.dumps(reg, ensure_ascii=False)[:1500]}")
    return 0


def evaluar_diagnostico(pares: list[dict]) -> dict:
    """§0.1 HITO20: reglas D1 -> D2 -> D3, declaradas antes de correr.

    Cada par: {"celda", "score16", "score32", "a1"}.
    """
    detalles = [{"celda": p["celda"], "score16": round(p["score16"], 2),
                 "score32": round(p["score32"], 2),
                 "a1": round(p["a1"], 2),
                 "delta": round(p["score32"] - p["score16"], 2),
                 "ratio_vs_a1": round(p["score32"] / p["a1"], 4) if p["a1"] else None,
                 "cumple_09a1": bool(p["score32"] >= 0.9 * p["a1"])}
                for p in pares]
    base = {"n_celdas": len(pares), "celdas": detalles}
    if len(pares) >= 2:
        cumplen = [d for d in detalles if d["cumple_09a1"]]
        if len(cumplen) >= 2:
            return {**base, "regla": "D1_CLARO_C1",
                    "accion": "lanzar HITO20 = B+C1 (sin acelerador)"}
    if pares:
        media_delta = sum(d["delta"] for d in detalles) / len(detalles)
        base["media_delta"] = round(media_delta, 2)
        if media_delta < 10:
            return {**base, "regla": "D2_NO_CLARO",
                    "accion": "consultar al dueño (candidato a B+C1+C2)"}
    return {**base, "regla": "D3_AMBIGUO",
            "accion": "consultar al dueño con datos"}


def modo_diagnostico(model: str, resume: bool) -> int:
    """Diagnóstico HITO20 §0.1: celdas truncadas con max_turns=32."""
    _load_env(model)
    if resume and not STATE_DIAG.is_file():
        log("ERROR: --resume sin estado previo del diagnóstico")
        return 3
    if not resume and STATE_DIAG.is_file():
        log(f"ERROR: ya existe {STATE_DIAG.name}; usa --resume o archiva "
            "el estado documentándolo.")
        return 3
    if not RESULT_OFICIAL.is_file():
        log("ERROR: falta la evidencia oficial del H19 (comparación @16)")
        return 3
    of = json.loads(RESULT_OFICIAL.read_text(encoding="utf-8"))
    a1_scores = of["matriz"]["A1"]
    est16 = {k: int(v["usage"]["total_tokens"]) for k, v in of["celdas"].items()}

    import traceforge
    cells: dict[str, dict] = {}
    if resume:
        cells = json.loads(STATE_DIAG.read_text(encoding="utf-8")).get("cells", {})
        log(f"resume diagnóstico: {len(cells)} celdas cargadas")
        traceforge.configure(collector="sqlite", db_path=str(TRACES_DIAG))
    else:
        STATE_DIAG.write_text(json.dumps({"cells": {}}, indent=1), encoding="utf-8")
        if TRACES_DIAG.exists():
            TRACES_DIAG.unlink()
        traceforge.configure(collector="sqlite", db_path=str(TRACES_DIAG))

    orden = DIAG_CELLS + DIAG_CANDIDATES_EXTRA
    obligatorias = set(DIAG_CELLS)
    omitidas: list[str] = []
    from evals.sd_pilot.variants import VARIANTS
    log(f"diagnóstico HITO20 §0.1: max_turns={DIAG_MAX_TURNS} techo="
        f"{DIAG_TECHO_TOKENS} celdas={orden}")
    for vname, tid in orden:
        key = f"{vname}_{tid}"
        if key in cells and cells[key].get("score") is not None:
            log(f"{key}: ya puntuada ({cells[key]['score']}%), se omite")
            continue
        acumulado = _coste(cells)["total_tokens"]
        est_celda = 2 * est16.get(key, 0)
        if key not in obligatorias and (
                acumulado + est_celda > DIAG_TECHO_TOKENS):
            omitidas.append(key)
            log(f"{key}: NO_EJECUTADA_TECHO (acumulado={acumulado} + "
                f"est={est_celda} > {DIAG_TECHO_TOKENS})")
            continue
        var = replace(VARIANTS[vname], max_turns=DIAG_MAX_TURNS)
        cells[key] = _run_cell(vname, tid, TRACES_DIAG, ws_root=WS_DIAG,
                               variant=var)
        STATE_DIAG.write_text(json.dumps({"cells": cells}, ensure_ascii=False,
                                         indent=1), encoding="utf-8")
        acum = _coste(cells)["total_tokens"]
        if acum > DIAG_TECHO_TOKENS:
            log(f"TECHO EXCEDIDO tras {key}: {acum} > {DIAG_TECHO_TOKENS}; "
                "se detiene")
            break

    pares = []
    for vname, tid in orden:
        key = f"{vname}_{tid}"
        if key in cells and cells[key].get("score") is not None:
            pares.append({"celda": key,
                          "score16": of["celdas"][key]["score"],
                          "score32": cells[key]["score"],
                          "a1": a1_scores[tid]})
    ver = evaluar_diagnostico(pares)
    coste = _coste(cells)
    result = {"hito": 20, "modo": "diagnostico",
              "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "modelo": model,
              "max_turns": DIAG_MAX_TURNS, "techo_tokens": DIAG_TECHO_TOKENS,
              "pares": pares, "veredicto": ver, "coste": coste,
              "omitidas_techo": omitidas, "celdas": cells,
              "trazas": str(TRACES_DIAG.relative_to(REPO)),
              "commits": _git_head()}
    RESULT_DIAG.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                           encoding="utf-8")
    for p in pares:
        log(f"  {p['celda']}: @16={p['score16']:.2f} @32={p['score32']:.2f} "
            f"(A1={p['a1']:.2f}, delta={p['score32'] - p['score16']:+.2f})")
    log(f"VEREDICTO {ver['regla']}: {ver['accion']}")
    log(f"coste diagnóstico={coste['total_tokens']} tokens "
        f"(techo {DIAG_TECHO_TOKENS})")
    log(f"evidencia: {RESULT_DIAG.relative_to(REPO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Piloto Sens(x) HITO19 / HITO20")
    ap.add_argument("--g0", action="store_true", help="G0 humo (§1.7)")
    ap.add_argument("--oficial", action="store_true", help="corrida oficial única")
    ap.add_argument("--diagnostico", action="store_true",
                    help="diagnóstico HITO20 §0.1 (max_turns=32, techo 450k)")
    ap.add_argument("--debug-celda", metavar="V:tarea", default=None,
                    help="una celda, SOLO BUILD")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--resume", action="store_true",
                    help="reanudar la corrida (oficial o diagnóstico) desde "
                         "el estado por celda")
    args = ap.parse_args(argv)

    modos = [bool(args.g0), bool(args.oficial), bool(args.diagnostico),
             bool(args.debug_celda)]
    if sum(modos) != 1:
        ap.error("elige UN modo: --g0 | --oficial | --diagnostico | "
                 "--debug-celda V:tarea")

    if args.g0:
        return modo_g0(args.model)
    if args.oficial:
        return modo_oficial(args.model, args.resume)
    if args.diagnostico:
        return modo_diagnostico(args.model, args.resume)
    return modo_debug_celda(args.debug_celda, args.model)


if __name__ == "__main__":
    sys.exit(main())
