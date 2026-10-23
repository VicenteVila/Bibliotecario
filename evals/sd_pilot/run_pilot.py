#!/usr/bin/env python3
"""Corredor del piloto HITO19 (Sens(x)) y del diagnóstico HITO20 (§0.1).

Modos:
  --g0       G0 humo (§1.7 HITO19): 2 tareas x {A1,A5} -> dictámen de arranque.
  --oficial  Corrida oficial ÚNICA de HITO19: 5 variantes x 12 tareas -> gates.
  --diagnostico  Diagnóstico HITO20 §0.1: celdas truncadas con max_turns=32
             (techo 450k, salidas propias, NO toca nada del oficial).
  --diagnostico-b  Diagnóstico escalado-b HITO20 §0.3: canal b (lecturas
             completas + multi-acción + cap 18k), 17 turnos, 3 celdas,
             techo 1,5M, tope duro 450k/celda (RATIFICADO 2026-10-23).
  --corrida-b   §1 HITO20 (Enmiendas 1-2): matriz 17x12 canal b, orden
             estratificado semilla 20261023, checkpoint 2,65M con árbol
             pre-registrado, techo 7M, cap 450k/celda, más brazo
             forzado de saturación (3 celdas §0.3 a 17 turnos sin
             parada temprana). SOLO tras §1 definitivo ratificado.
  --presupuesto  Coste/turnos de antemano de una corrida (sin LLM); política
             de claves del dueño 2026-10-23: SIEMPRE presupuestar antes.
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

# Presupuesto de antemano (política del dueño 2026-10-23): media de tokens
# por celda @16 turnos de la corrida oficial H19, y exponente cúbico del
# historial compuesto (calibrado: A5_repo@16=114k -> @30=752k real; 6.59 =
# (30/16)^3).
PRESUPUESTO_BASE_16 = {"A1": 5_479, "A2": 105_545, "A3": 90_278,
                       "A4": 127_635, "A5": 97_983}
PRESUPUESTO_EXPONENTE = 3

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

# Diagnóstico escalado-b HITO20 §0.3 (DECLARADO y ratificado por el dueño
# 2026-10-23): canal b (lecturas completas + multi-acción + cap 18k),
# mismas 3 celdas del §0.1, max_turns=17, techo 1,5M, tope duro 450k/celda.
DIAGB_CELLS: list[tuple[str, str]] = DIAG_CELLS + DIAG_CANDIDATES_EXTRA
DIAGB_MAX_TURNS = 17
DIAGB_TECHO_TOKENS = 1_500_000
DIAGB_CELL_CAP = 450_000
WS_DIAGB = Path("/tmp/opencode/sd_pilot_diagb")
STATE_DIAGB = SD_ROOT / "_run_state_diagb.json"
TRACES_DIAGB = SD_ROOT / "traces_diagb.sqlite"
RESULT_DIAGB = REPO / "evals" / "results" / "result_sens_sd_diagb.json"
INFORMES_DIAGB = REPO / "evals" / "results" / "informes_diagb"
# Margen de recalibración: el dueño fija rango 25-30 %; se aplica 30 %
# (conservador).
MARGEN_RECALIBRACION = 0.30

# Corrida oficial §1 HITO20 (Enmiendas 1-2, RATIFICADAS 2026-10-23):
# matriz 17x12 canal b + brazo forzado de saturación. NO se lanza sin el
# visto bueno del dueño (§1.6).
CORR_B_MAX_TURNS = 17
CORR_B_CELL_CAP = 450_000
CORR_B_TECHO = 7_000_000
CORR_B_SEED = 20261023
CORR_B_SNAP_TURNS = (2, 4, 6, 8, 12)   # 12 primario; 2/4/6/8 descriptivos
CORR_B_SNAP_FORZADO = (12, 17)
CHECKPOINT_TOKENS = 2_654_737          # proyección 2.042.105 x 1,3
CHECKPOINT_MIN_COMPLETADAS = 0.70
CHECKPOINT_UMBRAL_ALTO = 8_500_000
UMBRAL_CONVERGENCIA_REAL = 0.80
UMBRAL_TRUNCAMIENTO_RESULTADO = 0.20
FACTORES_INYECTADOS = {"A1": 1.0, "A2": 0.2297, "A3": 0.3203,
                       "A4": 0.3203, "A5": 0.3203}
PROY_CELDA_BASE = 26_181       # 1.570.850 / 60 (§0.3 sin margen)
PROY_FORZADO_BASE = 130_000    # media extrapolada por celda (E1-Ajuste 3)
N_CELLS_PLAN = 63              # 60 matriz + 3 brazo forzado
WS_CORRB = Path("/tmp/opencode/sd_pilot_corrb")
STATE_CORRB = SD_ROOT / "_run_state_corrb.json"
TRACES_CORRB = SD_ROOT / "traces_corrb.sqlite"
RESULT_CORRB = REPO / "evals" / "results" / "result_sens_sd_corridab.json"
INFORMES_CORRB = REPO / "evals" / "results" / "informes_corridab"

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
    # Política de claves del dueño (2026-10-23): el piloto SIEMPRE su clave,
    # bibliotecario (app) la principal. Nunca se imprime ningún valor.
    if os.environ.get("NVIDIA_API_KEY_PILOTO"):
        os.environ["NVIDIA_API_KEY"] = os.environ["NVIDIA_API_KEY_PILOTO"]
        log("clave NVIDIA: PILOTO (separada de bibliotecario; valor no mostrado)")
    else:
        log("AVISO: falta NVIDIA_API_KEY_PILOTO en .env — este run usa la "
            "principal compartida con bibliotecario (RPM mezclados)")


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
              variant=None, canal: str = "oficial",
              cell_token_cap: int = 0, force_full_turns: bool = False,
              snap_turns: tuple[int, ...] | None = None,
              ceiling_watch: tuple[int, int, int] | None = None) -> dict:
    """Ejecuta UNA celda completa y devuelve su registro (score incluido).

    `ws_root` y `variant` los usa el diagnóstico (§0.1/§0.3/§1): workspaces
    propios y `max_turns` ampliado. `canal="b"` activa el canal declarado
    en §0.3 (lecturas completas, multi-acción, cap, snapshots); el default
    "oficial" deja el arnés de H19 intacto. `force_full_turns` es el brazo
    forzado §1 (ignora `final`, reprompt pre-registrado).
    """
    from bibliotecario.core import llm as BLLM
    from evals.sd_pilot import verifier
    from evals.sd_pilot.harness import CANAL_SNAP_TURNS, Cell
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
                    skills_dir=SD_ROOT / "skills_pack", tracing=True,
                    canal=canal, cell_token_cap=cell_token_cap,
                    force_full_turns=force_full_turns,
                    snap_turns=snap_turns or CANAL_SNAP_TURNS,
                    ceiling_watch=ceiling_watch)
        res = cell.run()
    finally:
        traceforge.reset_metadata_context(token)

    usage = BLLM.usage_totals()
    score = verifier.hidden_score(ws, td)
    elapsed = round(time.time() - t0, 1)
    reg = {"score": score["score"], "hidden": {"passed": score["passed"],
           "total": score["total"]}, "turns": res.turns,
           "max_turns": var.max_turns, "canal": canal,
           "llm_calls": res.llm_calls, "tool_calls": res.tool_calls,
           "invalid_actions": res.invalid_actions, "pf_fires": res.pf_fires,
           "regulation": res.regulation, "stopped_by": res.stopped_by,
           "llm_error": res.llm_error, "errors": res.errors[:8],
           "final": res.final[:300], "elapsed_s": elapsed,
           "writes": res.writes, "snapshots": res.snapshots,
           "tokens_por_turno": res.tokens_por_turno,
           "forced_turns": res.forced_turns, "forced_writes": res.forced_writes,
           "forced_sin_mejora": res.forced_sin_mejora,
           "convergencia_real": res.convergencia_real,
           "force_full_turns": force_full_turns,
           "usage": {k: usage.get(k) for k in
                      ("calls", "prompt_tokens", "completion_tokens", "total_tokens")}}
    log(f"{vname}/{tid}: score={reg['score']}% turns={res.turns} "
        f"llm={res.llm_calls} tools={res.tool_calls} writes={res.writes} "
        f"paro={res.stopped_by} tok={usage.get('total_tokens')} {elapsed}s"
        + (f" LLM_ERROR={reg['llm_error']}" if reg["llm_error"] else ""))
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


def estimar_tokens_celda(base16: int, max_turns: int) -> int:
    """Estimación de antemano de tokens por celda con el modelo cúbico.

    `base16 × (max_turns/16)^3` — el historial compuesto hace crecer el
    prompt de cada turno; calibrado con la corrida oficial H19: A5_repo
    114.467 tok @16 -> 752.118 tok @30 ((30/16)^3 = 6.59, real 6.57).
    """
    return round(base16 * (max_turns / 16) ** PRESUPUESTO_EXPONENTE)


def presupuesto_run(max_turns: int, n_tareas: int, techo: int) -> dict:
    """Coste y turnos de antemano de una corrida completa (5 variantes).

    Política del dueño 2026-10-23: TODA run nueva se presupuesta y declara
    su techo ANTES de lanzarla. A1 es one-shot: una sola llamada por tarea,
    no escala con `max_turns`.
    """
    por_variante: dict[str, int] = {}
    llamadas_por_tarea = 0
    for v, base in PRESUPUESTO_BASE_16.items():
        if v == "A1":
            por_variante[v] = base
            llamadas_por_tarea += 1
        else:
            por_variante[v] = estimar_tokens_celda(base, max_turns)
            llamadas_por_tarea += max_turns
    total = sum(por_variante.values()) * n_tareas
    return {"max_turns": max_turns, "n_tareas": n_tareas,
            "celdas": n_tareas * len(PRESUPUESTO_BASE_16),
            "por_variante": por_variante,
            "llamadas_max": llamadas_por_tarea * n_tareas,
            "total": total, "techo": techo, "cabe": total <= techo,
            "veredicto": "COSTE_OK" if total <= techo else "EXCEDE_TECHO"}


def modo_presupuesto(max_turns: int, n_tareas: int, techo: int) -> int:
    p = presupuesto_run(max_turns, n_tareas, techo)
    log(f"presupuesto de antemano: max_turns={max_turns} n_tareas={n_tareas} "
        f"({p['celdas']} celdas, {p['llamadas_max']} llamadas máx)")
    for v, tok in p["por_variante"].items():
        log(f"  {v}: {tok} tok/celda")
    log(f"  total estimado: {p['total']} tokens · techo {p['techo']} -> "
        f"{p['veredicto']}")
    log("modelo cúbico calibrado con H19 (A5@16=114k -> @30=752k); "
        "declarar este techo en el plan del hito antes de lanzar")
    return 0 if p["cabe"] else 2


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


def evaluar_diagnostico_b(pares: list[dict], informes_ok: bool = True) -> dict:
    """§0.3 HITO20: reglas E1/E2/E3 + infra_error, declaradas antes de correr.

    Cada par: {"celda", "score16", "score17", "writes", "tokens16",
    "tokens17", "tokens_por_turno", "cortada", "infra_error"}.
    `infra_error` = llm_error no vacío tras agotar reintentos: excluida de
    E1/E2; <2 válidas → E3 por infraestructura.
    """
    detalles = []
    for p in pares:
        tp = p.get("tokens_por_turno") or []
        if len(tp) >= 10:
            pendiente_ok = (sum(tp[-5:]) / 5.0) <= (sum(tp[:5]) / 5.0)
        else:
            pendiente_ok = True  # celda final corta: coste acotado
        detalles.append({
            "celda": p["celda"],
            "score16": round(p["score16"], 2),
            "score17": round(p["score17"], 2),
            "delta": round(p["score17"] - p["score16"], 2),
            "writes": int(p.get("writes") or 0),
            "cortada": bool(p.get("cortada")),
            "pendiente_ok": pendiente_ok,
            "tokens16": int(p.get("tokens16") or 0),
            "tokens17": int(p.get("tokens17") or 0),
            "factor": (round(p["tokens17"] / p["tokens16"], 4)
                       if p.get("tokens16") else None),
            "infra_error": bool(p.get("infra_error")),
        })
    validas = [d for d in detalles if not d["infra_error"]]
    base = {"n_celdas": len(pares), "n_validas": len(validas),
            "n_infra": len(pares) - len(validas), "celdas": detalles,
            "informes_ok": bool(informes_ok)}
    if len(validas) < 2:
        return {**base, "regla": "E3_INFRA",
                "accion": "consultar al dueño: <2 celdas válidas (infra_error)"}
    e1_delta = sum(1 for d in validas if d["delta"] >= 10) >= 2
    e1_writes = sum(1 for d in validas if d["writes"] >= 1) >= 2
    e1_coste = sum(1 for d in validas
                   if not d["cortada"] and d["pendiente_ok"]) >= 2
    base["e1"] = {"delta_ge10": e1_delta, "writes_ge1": e1_writes,
                  "coste_acotado": e1_coste, "informes": bool(informes_ok)}
    if e1_delta and e1_writes and e1_coste and informes_ok:
        return {**base, "regla": "E1_ACLARA",
                "accion": "redactar §1 (17x12, techo recalibrado) para ratificar"}
    max_delta = max((d["delta"] for d in validas), default=0.0)
    if max_delta <= 5 or all(d["writes"] == 0 for d in validas):
        return {**base, "regla": "E2_NO_ACLARA",
                "accion": ("c justificado con datos (canal+coste); "
                           "no corrida 17x12; proponer c al dueño")}
    return {**base, "regla": "E3_AMBIGUO",
            "accion": "consultar al dueño con los datos"}


def recalibrar_diagnostico_b(factores: dict[str, float]) -> dict:
    """§0.3: proyección 17x12 con los factores medidos + margen 30 %.

    A1 oficial fijo; A2×factor propio; A5×el peor de sus dos celdas; A3/A4
    con el máximo global (conservador: no se midieron). Si proyecta >7M →
    no se lanza y se consulta.
    """
    f2 = factores.get("A2_plugin-registry", 0.0)
    f5 = max(factores.get("A5_repo-cache-layer", 0.0),
             factores.get("A5_workflow-statemachine", 0.0))
    fmax = max(factores.values(), default=1.0)
    por_tarea = (PRESUPUESTO_BASE_16["A1"]
                 + PRESUPUESTO_BASE_16["A2"] * f2
                 + PRESUPUESTO_BASE_16["A3"] * fmax
                 + PRESUPUESTO_BASE_16["A4"] * fmax
                 + PRESUPUESTO_BASE_16["A5"] * f5)
    total = por_tarea * 12
    con_margen = round(total * (1 + MARGEN_RECALIBRACION))
    return {"factores": factores, "factor_max": fmax,
            "total_12t_sin_margen": round(total),
            "margen": MARGEN_RECALIBRACION, "proyeccion": con_margen,
            "techo": TECHO_TOKENS, "cabe": con_margen <= TECHO_TOKENS,
            "veredicto": "COSTE_OK" if con_margen <= TECHO_TOKENS
                         else "EXCEDE_CONSULTAR"}


# ------------------------- §1 HITO20 (Enmiendas 1-2, puras) -----------------

def orden_estratificado(seed: int = CORR_B_SEED) -> list[tuple[str, str]]:
    """E2-Crítico 2: 60 celdas, 4 de cada variante por tercio, semilla fija."""
    import random

    from evals.sd_pilot.tasks import TASK_IDS
    from evals.sd_pilot.variants import VARIANT_NAMES
    rng = random.Random(seed)
    orden: list[tuple[str, str]] = []
    for tercio in range(3):
        bloque: list[tuple[str, str]] = []
        for vname in VARIANT_NAMES:
            slice_t = TASK_IDS[tercio * 4:(tercio + 1) * 4]
            bloque.extend((vname, t) for t in slice_t)
        rng.shuffle(bloque)
        orden.extend(bloque)
    return orden


def proy_celda(vname: str) -> int:
    """E2-Crítico 2: base oficial H16 x factor inyectado (§0.3)."""
    return round(PRESUPUESTO_BASE_16[vname] * FACTORES_INYECTADOS[vname])


def decidir_truncamiento(tokens_celda: int, proyeccion: int) -> str:
    """Regla del 80 % (E2-Crítico 2): completar vs cortar mid-cell."""
    if proyeccion <= 0:
        return "completar"
    return "completar" if tokens_celda < 0.8 * proyeccion else "cortar"


def decidir_checkpoint(acumulado: int, pend_matrix: int,
                       pend_forzado: int) -> dict:
    """Árbol pre-registrado del dueño (E2-Importante 2), sin consulta en
    caliente: <=7M seguir; 7-8.5M truncar; >8.5M reducir matriz."""
    proy = (acumulado + pend_matrix * PROY_CELDA_BASE
            + pend_forzado * PROY_FORZADO_BASE)
    if proy <= CORR_B_TECHO:
        branch = "seguir"
    elif proy <= CHECKPOINT_UMBRAL_ALTO:
        branch = "truncar"
    else:
        branch = "reducir"
    return {"proyeccion": proy, "branch": branch}


def celdas_reducidas(of: dict) -> list[tuple[str, str]]:
    """E2-Importante 2: una celda por variante = mayor usage.total_tokens
    en H19 oficial (regla determinista, pre-registrada)."""
    from evals.sd_pilot.variants import VARIANT_NAMES
    out: list[tuple[str, str]] = []
    for vname in VARIANT_NAMES:
        celdas_v = {k: c for k, c in of["celdas"].items()
                    if k.startswith(vname + "_")}
        key = max(celdas_v,
                  key=lambda k: int(celdas_v[k]["usage"]["total_tokens"] or 0))
        v_part, tid = key.split("_", 1)
        out.append((v_part, tid))
    return out


def evaluar_saturacion_forzado(pares: list[dict], semilla: int = CORR_B_SEED,
                               n_boot: int = 10_000) -> dict:
    """§1 E1-Ajuste 1: Δ = score@17 − score@12 del brazo forzado,
    IC95 bootstrap (10k, semilla fija). n<3 → fallback (i)."""
    deltas = [round(float(p["score17"]) - float(p["score12"]), 4)
              for p in pares]
    base = {"n": len(deltas), "deltas": deltas,
            "celdas": [{"celda": p["celda"],
                        "score12": round(float(p["score12"]), 2),
                        "score17": round(float(p["score17"]), 2),
                        "convergencia_real": bool(p.get("convergencia_real"))}
                       for p in pares]}
    if len(deltas) < 3:
        return {**base, "regla": "INSUFICIENTE_FALLBACK_I",
                "accion": ("§1 mide convergencia, no saturación; (c) queda "
                           "pendiente para HITO21 (fallback i, E1-Ajuste 1)")}
    import random
    rng = random.Random(semilla)
    n = len(deltas)
    medias = sorted(sum(rng.choice(deltas) for _ in range(n)) / n
                    for _ in range(n_boot))
    ic_lo = medias[int(0.025 * n_boot)]
    ic_hi = medias[min(int(0.975 * n_boot), n_boot - 1)]
    if ic_lo > 0:
        return {**base, "ic95": [ic_lo, ic_hi], "regla": "NO_SATURA",
                "accion": "(c) justificado para HITO21 (turnos 12-17 aportan)"}
    return {**base, "ic95": [ic_lo, ic_hi], "regla": "SATURA",
            "accion": "(c) cancelado (turnos 12-17 no aportan ni forzados)"}


def _generar_informes_diagb() -> bool:
    """Informes del observador para E1.4 (legibilidad declarada)."""
    from evals.sd_pilot import observador
    spans = observador.cargar_spans(TRACES_DIAGB)
    celdas = observador.agrupar_por_celda(spans)
    INFORMES_DIAGB.mkdir(parents=True, exist_ok=True)
    ok = True
    for key, cs in sorted(celdas.items()):
        out = INFORMES_DIAGB / f"{key}.md"
        out.write_text(observador.informe_celda(key, cs), encoding="utf-8")
        log(f"informe: {out.relative_to(REPO)} ({len(cs)} spans)")
        if not out.read_text(encoding="utf-8").strip():
            ok = False
    return ok


def modo_diagnostico_b(model: str, resume: bool) -> int:
    """Diagnóstico escalado-b HITO20 §0.3: canal b, 17 turnos, 3 celdas."""
    _load_env(model)
    if resume and not STATE_DIAGB.is_file():
        log("ERROR: --resume sin estado previo del diagnóstico-b")
        return 3
    if not resume and STATE_DIAGB.is_file():
        log(f"ERROR: ya existe {STATE_DIAGB.name}; usa --resume o archiva "
            "el estado documentándolo.")
        return 3
    if not RESULT_OFICIAL.is_file():
        log("ERROR: falta la evidencia oficial del H19 (comparación @16)")
        return 3
    of = json.loads(RESULT_OFICIAL.read_text(encoding="utf-8"))
    a1_scores = of["matriz"]["A1"]

    import traceforge
    cells: dict[str, dict] = {}
    if resume:
        cells = json.loads(STATE_DIAGB.read_text(encoding="utf-8")).get("cells", {})
        log(f"resume diagnóstico-b: {len(cells)} celdas cargadas")
        traceforge.configure(collector="sqlite", db_path=str(TRACES_DIAGB))
    else:
        STATE_DIAGB.write_text(json.dumps({"cells": {}}, indent=1), encoding="utf-8")
        if TRACES_DIAGB.exists():
            TRACES_DIAGB.unlink()
        traceforge.configure(collector="sqlite", db_path=str(TRACES_DIAGB))

    from evals.sd_pilot.variants import VARIANTS
    log(f"diagnóstico-b §0.3: canal=b max_turns={DIAGB_MAX_TURNS} "
        f"cap_llamada={DIAGB_CELL_CAP} techo={DIAGB_TECHO_TOKENS} "
        f"celdas={DIAGB_CELLS}")
    for vname, tid in DIAGB_CELLS:
        key = f"{vname}_{tid}"
        if key in cells and cells[key].get("score") is not None:
            log(f"{key}: ya puntuada ({cells[key]['score']}%), se omite")
            continue
        acumulado = _coste(cells)["total_tokens"]
        if acumulado + DIAGB_CELL_CAP > DIAGB_TECHO_TOKENS:
            log(f"TECHO: {key} no ejecutada (acumulado={acumulado} + "
                f"{DIAGB_CELL_CAP} > {DIAGB_TECHO_TOKENS})")
            break
        var = replace(VARIANTS[vname], max_turns=DIAGB_MAX_TURNS)
        cells[key] = _run_cell(vname, tid, TRACES_DIAGB, ws_root=WS_DIAGB,
                               variant=var, canal="b",
                               cell_token_cap=DIAGB_CELL_CAP)
        STATE_DIAGB.write_text(json.dumps({"cells": cells}, ensure_ascii=False,
                                          indent=1), encoding="utf-8")
        acum = _coste(cells)["total_tokens"]
        if acum > DIAGB_TECHO_TOKENS:
            log(f"TECHO EXCEDIDO tras {key}: {acum} > {DIAGB_TECHO_TOKENS}; "
                "se detiene")
            break

    informes_ok = _generar_informes_diagb()
    pares = []
    factores: dict[str, float] = {}
    for vname, tid in DIAGB_CELLS:
        key = f"{vname}_{tid}"
        c = cells.get(key)
        if not c or c.get("score") is None:
            continue
        tok16 = int(of["celdas"][key]["usage"]["total_tokens"])
        tok17 = int(c["usage"]["total_tokens"] or 0)
        if tok16 and tok17:
            factores[key] = round(tok17 / tok16, 4)
        pares.append({"celda": key,
                      "score16": of["celdas"][key]["score"],
                      "score17": c["score"], "a1": a1_scores[tid],
                      "writes": c.get("writes", 0), "tokens16": tok16,
                      "tokens17": tok17,
                      "tokens_por_turno": c.get("tokens_por_turno") or [],
                      "cortada": c.get("stopped_by") == "presupuesto",
                      "infra_error": bool(c.get("llm_error"))})
    ver = evaluar_diagnostico_b(pares, informes_ok=informes_ok)
    recal = recalibrar_diagnostico_b(factores)
    coste = _coste(cells)
    result = {"hito": 20, "modo": "diagnostico-b",
              "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "modelo": model,
              "canal": "b", "max_turns": DIAGB_MAX_TURNS,
              "cap_llamada": DIAGB_CELL_CAP, "techo_tokens": DIAGB_TECHO_TOKENS,
              "pares": pares, "veredicto": ver, "recalibracion": recal,
              "coste": coste, "celdas": cells,
              "trazas": str(TRACES_DIAGB.relative_to(REPO)),
              "informes": str(INFORMES_DIAGB.relative_to(REPO)),
              "commits": _git_head()}
    RESULT_DIAGB.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    for p in pares:
        log(f"  {p['celda']}: @16={p['score16']:.2f} @17={p['score17']:.2f} "
            f"(delta={p['score17'] - p['score16']:+.2f} writes={p['writes']} "
            f"factor={factores.get(p['celda'])})")
    log(f"VEREDICTO {ver['regla']}: {ver['accion']}")
    log(f"recalibración: proyección 17x12 = {recal['proyeccion']} tokens "
        f"(margen {MARGEN_RECALIBRACION:.0%}) -> {recal['veredicto']}")
    log(f"coste diagnóstico-b={coste['total_tokens']} tokens "
        f"(techo {DIAGB_TECHO_TOKENS})")
    log(f"evidencia: {RESULT_DIAGB.relative_to(REPO)}")
    return 0


def _generar_informes_corridab() -> bool:
    """Informes del observador de la corrida-b (misma E1.4 declarada)."""
    from evals.sd_pilot import observador
    spans = observador.cargar_spans(TRACES_CORRB)
    celdas = observador.agrupar_por_celda(spans)
    INFORMES_CORRB.mkdir(parents=True, exist_ok=True)
    ok = True
    for key, cs in sorted(celdas.items()):
        out = INFORMES_CORRB / f"{key}.md"
        out.write_text(observador.informe_celda(key, cs), encoding="utf-8")
        log(f"informe: {out.relative_to(REPO)} ({len(cs)} spans)")
        if not out.read_text(encoding="utf-8").strip():
            ok = False
    return ok


def modo_corrida_b(model: str, resume: bool) -> int:
    """§1 HITO20: matriz 17x12 canal b (orden estratificado, checkpoint
    2.65M, techo 7M) + brazo forzado de saturación (Enmiendas 1-2).

    Solo para lanzar tras §1 definitivo ratificado (§1.6); este modo ya
    incorpora todos los números inyectados del pre-registro.
    """
    _load_env(model)
    if resume and not STATE_CORRB.is_file():
        log("ERROR: --resume sin estado previo de la corrida-b")
        return 3
    if not resume and STATE_CORRB.is_file():
        log(f"ERROR: ya existe {STATE_CORRB.name}; usa --resume o archiva "
            "el estado documentándolo.")
        return 3
    if not RESULT_OFICIAL.is_file():
        log("ERROR: falta la evidencia oficial del H19 (comparación @16)")
        return 3
    of = json.loads(RESULT_OFICIAL.read_text(encoding="utf-8"))

    import traceforge
    cells: dict[str, dict] = {}
    if resume:
        cells = json.loads(STATE_CORRB.read_text(encoding="utf-8")).get("cells", {})
        log(f"resume corrida-b: {len(cells)} celdas cargadas")
        traceforge.configure(collector="sqlite", db_path=str(TRACES_CORRB))
    else:
        STATE_CORRB.write_text(json.dumps({"cells": {}}, indent=1), encoding="utf-8")
        if TRACES_CORRB.exists():
            TRACES_CORRB.unlink()
        traceforge.configure(collector="sqlite", db_path=str(TRACES_CORRB))

    from dataclasses import replace as _replace

    from evals.sd_pilot.variants import VARIANTS
    orden = orden_estratificado()
    log(f"corrida-b §1: canal=b max_turns={CORR_B_MAX_TURNS} "
        f"cap_celda={CORR_B_CELL_CAP} techo={CORR_B_TECHO} "
        f"checkpoint={CHECKPOINT_TOKENS} celdas={len(orden)} "
        f"semilla={CORR_B_SEED}")

    reducidas: set[str] | None = None
    checkpoint: dict | None = None

    def _completas() -> int:
        return sum(1 for c in cells.values()
                   if c.get("score") is not None
                   and c.get("estado") not in ("truncated_by_ceiling",
                                               "no_ejecutada_por_techo"))

    # ---------------- matriz 60 celdas, orden estratificado ----------------
    for vname, tid in orden:
        key = f"{vname}_{tid}"
        if key in cells and (cells[key].get("score") is not None
                             or cells[key].get("estado")):
            log(f"{key}: ya registrada, se omite")
            continue
        if reducidas is not None and key not in reducidas:
            cells[key] = {"score": None, "estado": "no_ejecutada_por_techo"}
            log(f"{key}: NO_EJECUTADA_POR_TECHO (reducción de matriz)")
            continue
        acum = _coste(cells)["total_tokens"]
        proy = proy_celda(vname)
        if CORR_B_TECHO - acum < 0.8 * proy:
            cells[key] = {"score": None, "estado": "no_ejecutada_por_techo"}
            log(f"{key}: NO_EJECUTADA_POR_TECHO (restante {CORR_B_TECHO - acum} "
                f"< 80% de proy {proy})")
            continue
        var = _replace(VARIANTS[vname], max_turns=CORR_B_MAX_TURNS)
        cells[key] = _run_cell(vname, tid, TRACES_CORRB, ws_root=WS_CORRB,
                               variant=var, canal="b",
                               cell_token_cap=CORR_B_CELL_CAP,
                               snap_turns=CORR_B_SNAP_TURNS,
                               ceiling_watch=(acum, proy, CORR_B_TECHO))
        if cells[key]["stopped_by"] == "truncated_by_ceiling":
            cells[key]["estado"] = "truncated_by_ceiling"
        STATE_CORRB.write_text(json.dumps({"cells": cells}, ensure_ascii=False,
                                          indent=1), encoding="utf-8")
        acum = _coste(cells)["total_tokens"]
        # Checkpoint (E2-Importante 2): evaluación única, árbol pre-reg.
        if checkpoint is None and acum >= CHECKPOINT_TOKENS:
            pend_m = sum(1 for v, t in orden if f"{v}_{t}" not in cells)
            hechas = _completas()
            pct = hechas / N_CELLS_PLAN
            checkpoint = decidir_checkpoint(acum, max(pend_m, 0),
                                            len(DIAGB_CELLS))
            log(f"CHECKPOINT {acum} >= {CHECKPOINT_TOKENS}: completadas "
                f"{hechas}/{N_CELLS_PLAN} ({pct:.0%}) -> proy "
                f"{checkpoint['proyeccion']} -> branch {checkpoint['branch']}")
            if pct < CHECKPOINT_MIN_COMPLETADAS and checkpoint["branch"] == "reducir":
                reducidas = {f"{v}_{t}" for v, t in celdas_reducidas(of)}
                log(f"CHECKPOINT: reducir matriz a {sorted(reducidas)}")
        if acum >= CORR_B_TECHO:
            log(f"TECHO {CORR_B_TECHO} alcanzado tras {key}; resto sin ejecutar")
            break

    # ---------------- brazo forzado (test primario de saturación) ---------
    for vname, tid in DIAGB_CELLS:
        key = f"FORZ_{vname}_{tid}"
        if key in cells and cells[key].get("score") is not None:
            continue
        acum = _coste(cells)["total_tokens"]
        if CORR_B_TECHO - acum < 0.8 * PROY_FORZADO_BASE:
            cells[key] = {"score": None, "estado": "no_ejecutada_por_techo"}
            log(f"{key}: FALLBACK_I (sin presupuesto para el brazo forzado)")
            continue
        var = _replace(VARIANTS[vname], max_turns=CORR_B_MAX_TURNS)
        cells[key] = _run_cell(vname, tid, TRACES_CORRB, ws_root=WS_CORRB,
                               variant=var, canal="b",
                               cell_token_cap=CORR_B_CELL_CAP,
                               force_full_turns=True,
                               snap_turns=CORR_B_SNAP_FORZADO,
                               ceiling_watch=(acum, PROY_FORZADO_BASE,
                                              CORR_B_TECHO))
        if cells[key]["stopped_by"] == "truncated_by_ceiling":
            cells[key]["estado"] = "truncated_by_ceiling"
        STATE_CORRB.write_text(json.dumps({"cells": cells}, ensure_ascii=False,
                                          indent=1), encoding="utf-8")

    # ---------------- evaluación pre-registrada ---------------------------
    pares_forzado = []
    fallback_i = False
    for vname, tid in DIAGB_CELLS:
        key = f"FORZ_{vname}_{tid}"
        c = cells.get(key)
        if not c or c.get("score") is None or c.get("estado"):
            fallback_i = True
            continue
        snaps = c.get("snapshots") or {}
        if "score@12" not in snaps or "score@17" not in snaps:
            fallback_i = True
            continue
        pares_forzado.append({"celda": key, "score12": snaps["score@12"],
                              "score17": snaps["score@17"],
                              "convergencia_real": c.get("convergencia_real")})
    saturacion = evaluar_saturacion_forzado(pares_forzado)
    if fallback_i and saturacion["regla"] != "INSUFICIENTE_FALLBACK_I":
        saturacion["aviso"] = ("alguna celda forzada quedó incompleta o sin "
                               "snapshots; leer con fallback (i)")
    pares_matriz = []
    for vname, tid in orden:
        key = f"{vname}_{tid}"
        c = cells.get(key)
        if not c or c.get("score") is None:
            continue
        tok16 = int(of["celdas"][key]["usage"]["total_tokens"])
        tok17 = int((c.get("usage") or {}).get("total_tokens") or 0)
        pares_matriz.append({"celda": key,
                             "score16": of["celdas"][key]["score"],
                             "score17": c["score"],
                             "writes": c.get("writes", 0), "tokens16": tok16,
                             "tokens17": tok17,
                             "tokens_por_turno": c.get("tokens_por_turno") or [],
                             "cortada": bool(c.get("estado")),
                             "infra_error": bool(c.get("llm_error"))})
    comparativa = evaluar_diagnostico_b(pares_matriz, informes_ok=True)
    n_trunc = sum(1 for c in cells.values()
                  if c.get("estado") in ("truncated_by_ceiling",
                                         "no_ejecutada_por_techo"))
    tasa_trunc = n_trunc / N_CELLS_PLAN
    informes_ok = _generar_informes_corridab()
    coste = _coste(cells)
    result = {"hito": 20, "modo": "corrida-b",
              "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "modelo": model,
              "canal": "b", "max_turns": CORR_B_MAX_TURNS,
              "cap_celda": CORR_B_CELL_CAP, "techo_tokens": CORR_B_TECHO,
              "checkpoint": {"tokens": CHECKPOINT_TOKENS,
                             **(checkpoint or {"branch": "no_disparado"})},
              "orden_semilla": CORR_B_SEED,
              "saturacion": saturacion, "comparativa_canal_b": comparativa,
              "truncamiento": {"n": n_trunc, "tasa": round(tasa_trunc, 4),
                               "es_resultado": tasa_trunc > UMBRAL_TRUNCAMIENTO_RESULTADO},
              "fallback_i": fallback_i,
              "informes_ok": informes_ok,
              "coste": coste, "celdas": cells,
              "trazas": str(TRACES_CORRB.relative_to(REPO)),
              "informes": str(INFORMES_CORRB.relative_to(REPO)),
              "commits": _git_head()}
    RESULT_CORRB.write_text(json.dumps(result, ensure_ascii=False, indent=1),
                            encoding="utf-8")
    log(f"SATURACIÓN {saturacion['regla']}: {saturacion['accion']}")
    log(f"comparativa canal b vs H19: {comparativa['regla']}")
    log(f"truncamiento: {n_trunc}/{N_CELLS_PLAN} ({tasa_trunc:.0%})"
        + (" [RESULTADO justifica (c)]" if result["truncamiento"]["es_resultado"]
           else ""))
    log(f"coste corrida-b={coste['total_tokens']} tokens "
        f"(techo {CORR_B_TECHO}, checkpoint {CHECKPOINT_TOKENS})")
    log(f"evidencia: {RESULT_CORRB.relative_to(REPO)}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Piloto Sens(x) HITO19 / HITO20")
    ap.add_argument("--g0", action="store_true", help="G0 humo (§1.7)")
    ap.add_argument("--oficial", action="store_true", help="corrida oficial única")
    ap.add_argument("--diagnostico", action="store_true",
                    help="diagnóstico HITO20 §0.1 (max_turns=32, techo 450k)")
    ap.add_argument("--diagnostico-b", action="store_true",
                    help="diagnóstico escalado-b HITO20 §0.3 (canal b, 17 turnos)")
    ap.add_argument("--corrida-b", action="store_true",
                    help="§1 HITO20: matriz 17x12 canal b + brazo forzado "
                         "(solo tras §1 definitivo ratificado)")
    ap.add_argument("--presupuesto", action="store_true",
                    help="coste/turnos de antemano de una corrida (sin LLM)")
    ap.add_argument("--max-turns", type=int, default=32,
                    help="turnos previstos (solo con --presupuesto)")
    ap.add_argument("--n-tareas", type=int, default=12,
                    help="tareas previstas (solo con --presupuesto)")
    ap.add_argument("--techo", type=int, default=TECHO_TOKENS,
                    help="techo de tokens declarado (solo con --presupuesto)")
    ap.add_argument("--debug-celda", metavar="V:tarea", default=None,
                    help="una celda, SOLO BUILD")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--resume", action="store_true",
                    help="reanudar la corrida (oficial o diagnóstico) desde "
                         "el estado por celda")
    args = ap.parse_args(argv)

    modos = [bool(args.g0), bool(args.oficial), bool(args.diagnostico),
             bool(args.diagnostico_b), bool(args.corrida_b),
             bool(args.presupuesto), bool(args.debug_celda)]
    if sum(modos) != 1:
        ap.error("elige UN modo: --g0 | --oficial | --diagnostico | "
                 "--diagnostico-b | --corrida-b | --presupuesto | "
                 "--debug-celda V:tarea")

    if args.g0:
        return modo_g0(args.model)
    if args.oficial:
        return modo_oficial(args.model, args.resume)
    if args.diagnostico:
        return modo_diagnostico(args.model, args.resume)
    if args.diagnostico_b:
        return modo_diagnostico_b(args.model, args.resume)
    if args.corrida_b:
        return modo_corrida_b(args.model, args.resume)
    if args.presupuesto:
        return modo_presupuesto(args.max_turns, args.n_tareas, args.techo)
    return modo_debug_celda(args.debug_celda, args.model)


if __name__ == "__main__":
    sys.exit(main())
