#!/usr/bin/env python3
"""HITO27 — H26-B Fase 2: transferencia de skills compiladas a B-1 v2.

Diseño y gates declarados en `evals/HITO27_PLAN.md` (2026-10-25, antes de
medir). Este runner es deliberadamente pequeño:

* 4 tareas fijas × 2 brazos (`control`, `skills`) = 8 celdas.
* 1 generación por celda, 0 reparaciones, 0 bucle de agente.
* Mismo `PROMPT_SERIE3`, mismo scaffold y mismo scorer B-1 v2.
* `skills` añade un briefing compacto de las 14 `tech_skill_*` compiladas.
* `--dry-run` (por defecto) no llama al LLM; `--run` gasta tokens.

Uso:
  python evals/preflight/run_transfer_h26b.py
  python evals/preflight/run_transfer_h26b.py --run
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path("/mnt/c/Bibliotecario")
PREFLIGHT = ROOT / "evals" / "preflight"
if str(PREFLIGHT) not in sys.path:
    sys.path.insert(0, str(PREFLIGHT))

# measure_b1 fija LLM_PROVIDERS/GROQ_MODEL al importarse. Guardamos y
# restauramos para que importar este runner desde pytest no contamine el resto
# de la suite; la corrida real los vuelve a fijar en `_run`.
_OLD_PROVIDERS = os.environ.get("LLM_PROVIDERS")
_OLD_GROQ_MODEL = os.environ.get("GROQ_MODEL")
import measure_b1 as b1

if _OLD_PROVIDERS is None:
    os.environ.pop("LLM_PROVIDERS", None)
else:
    os.environ["LLM_PROVIDERS"] = _OLD_PROVIDERS
if _OLD_GROQ_MODEL is None:
    os.environ.pop("GROQ_MODEL", None)
else:
    os.environ["GROQ_MODEL"] = _OLD_GROQ_MODEL

TASKS = (
    "card-memory-precision",
    "platformer-torre-rebote",
    "idle-clicker-fabrica",
    "visualnovel-mystery-accusation",
)
ARMS = ("control", "skills")
MAX_TOKENS = 6000
COOLDOWN_S = 70
TPM = 8000
BUDGET_TOKENS = 100_000
SKILL_PREFIX = "tech_skill_"
SKILL_CHARS = 320
BRIEF_MARK = "CONOCIMIENTO COMPILADO H26"
TASK_YAML = ROOT / "evals/game_tasks_expanded.yaml"
WS_BASE = Path("/tmp/opencode/transfer_h26b")
OUT_JSON = ROOT / "evals/results/result_transfer_h26b.json"


def load_task_texts(path: Path = TASK_YAML) -> dict[str, str]:
    import yaml

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    by_id = {t["id"]: t["task"] for t in data["suite"]}
    faltan = [t for t in TASKS if t not in by_id]
    if faltan:
        raise SystemExit(f"faltan tareas en {path}: {faltan}")
    return {t: by_id[t] for t in TASKS}


def load_skills() -> list[tuple[str, str]]:
    from bibliotecario.core import storage

    with storage.get_conn() as conn:
        rows = conn.execute(
            "SELECT name, skill_md FROM skills "
            "WHERE name GLOB 'tech_skill_*' ORDER BY name"
        ).fetchall()
    skills = [(str(r["name"]), str(r["skill_md"])) for r in rows]
    if len(skills) != 14:
        raise SystemExit(f"se esperaban 14 tech_skill_*, hay {len(skills)}")
    return skills


def compact(text: str, limit: int = SKILL_CHARS) -> str:
    limpio = " ".join(text.split())
    if len(limpio) <= limit:
        return limpio
    return limpio[: limit - 3].rstrip() + "..."


def build_briefing(skills: list[tuple[str, str]]) -> str:
    """Briefing determinista: nombre + hasta 320 chars por skill."""
    partes = [
        (
            f"{BRIEF_MARK}: aplica estos principios de diseño de arneses al juego "
            "que vas a generar."
        )
    ]
    for name, text in sorted(skills):
        partes.append(f"### {name}\n{compact(text)}")
    return "\n\n".join(partes) + "\n\n"


def build_prompt(task_text: str, arm: str, briefing: str) -> str:
    if arm == "control":
        return b1.PROMPT_SERIE3 + task_text
    if arm != "skills":
        raise ValueError(f"brazo desconocido: {arm}")
    prefix = b1.PROMPT_SERIE3.rsplit("INSTRUCCIÓN DE LA TAREA:", 1)[0]
    return prefix + briefing + "\nINSTRUCCIÓN DE LA TAREA:\n" + task_text


def estimate_tokens(text: str) -> int:
    """Estimación conservadora para el gate TPM (4 chars/token)."""
    return math.ceil(len(text) / 4)


def build_cells(task_texts: dict[str, str], briefing: str) -> list[dict]:
    cells = []
    for task in TASKS:
        for arm in ARMS:
            prompt = build_prompt(task_texts[task], arm, briefing)
            cells.append({
                "task": task,
                "arm": arm,
                "prompt": prompt,
                "prompt_chars": len(prompt),
                "prompt_tokens_est": estimate_tokens(prompt),
            })
    return cells


def validate_no_leak(briefing: str, cells: list[dict], task_texts: dict[str, str]) -> tuple[bool, str]:
    prohibidos = list(task_texts) + [
        "suite_runner", "suite_runner_v2", "_checks.json", "check_suite",
        "platformer-juego", "golden",
    ]
    fugas = [p for p in prohibidos if p in briefing]
    if fugas:
        return False, f"briefing contiene términos prohibidos: {fugas}"
    if BRIEF_MARK in b1.PROMPT_SERIE3:
        return False, "el prompt base ya contiene la marca de tratamiento"
    for c in cells:
        if c["arm"] == "control" and (BRIEF_MARK in c["prompt"] or "tech_skill_" in c["prompt"]):
            return False, f"control contaminado: {c['task']}"
        if c["arm"] == "skills" and BRIEF_MARK not in c["prompt"]:
            return False, f"skills sin briefing: {c['task']}"
        if task_texts[c["task"]] not in c["prompt"]:
            return False, f"texto de tarea alterado: {c['task']}"
    return True, "control limpio; skills con briefing; sin ids/suite en el briefing"


def check_tpm(cells: list[dict]) -> tuple[bool, str]:
    peor = max(c["prompt_tokens_est"] + MAX_TOKENS for c in cells)
    ok = peor < TPM
    return ok, f"peor request estimado={peor} < TPM {TPM} (max_tokens={MAX_TOKENS})"


def prepare_workspace(ws: Path) -> None:
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    for rel, contenido in b1.SCAFFOLD.items():
        destino = ws / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")


def run_cell(cell: dict, out_dir: Path) -> dict:
    from bibliotecario.core.llm import generate, reset_usage, usage_totals

    ws = out_dir / cell["task"] / cell["arm"]
    prepare_workspace(ws)
    error = ""
    respuesta = ""
    reset_usage()
    t0 = time.time()
    try:
        respuesta = generate(
            cell["prompt"], max_tokens=MAX_TOKENS, retries=0, strict_fallback=False
        )
    except Exception as e:
        error = f"{type(e).__name__}: {e}"[:300]
    finally:
        dt = time.time() - t0
        usage = usage_totals()
        time.sleep(COOLDOWN_S)

    ficheros = b1.extraer_ficheros(respuesta) if respuesta else {}
    main_gd = ficheros.get("main.gd", "")
    tiene_main = bool(main_gd.strip())
    if tiene_main:
        (ws / "main.gd").write_text(main_gd, encoding="utf-8")
    suite = b1.correr_suite(cell["task"], ws)
    registro = {
        "task": cell["task"],
        "arm": cell["arm"],
        "prompt_chars": cell["prompt_chars"],
        "prompt_tokens_est": cell["prompt_tokens_est"],
        "llm_s": round(dt, 1),
        "cooldown_s": COOLDOWN_S,
        "respuesta_chars": len(respuesta),
        "main_gd": tiene_main,
        "ficheros": sorted(ficheros),
        "error": error,
        "usage": usage,
        "suite": suite,
    }
    print(
        f"  {cell['task']:<30} {cell['arm']:<8} "
        f"{dt:>6.0f}s  main.gd={'sí' if tiene_main else 'no'}  "
        f"BUILD={'ok' if suite.get('build_ok') else '0'}  "
        f"M={suite.get('m')}  Score={suite.get('score')}  "
        f"tokens={usage.get('total_tokens', 0)}"
    )
    return registro


def summarize(cells: list[dict]) -> dict:
    por_brazo: dict[str, dict] = {}
    for arm in ARMS:
        filas = [c for c in cells if c["arm"] == arm]
        scores = [float(c["suite"].get("score") or 0.0) for c in filas]
        por_brazo[arm] = {
            "n": len(filas),
            "media": round(sum(scores) / len(scores), 4) if scores else None,
            "scores": scores,
            "build_ok": sum(1 for c in filas if c["suite"].get("build_ok")),
            "main_gd": sum(1 for c in filas if c["main_gd"]),
        }
    por_tarea: dict[str, dict] = {}
    deltas = []
    for task in TASKS:
        filas = {c["arm"]: c for c in cells if c["task"] == task}
        sc = {arm: float(filas[arm]["suite"].get("score") or 0.0) for arm in ARMS if arm in filas}
        delta = round(sc.get("skills", 0.0) - sc.get("control", 0.0), 4)
        if len(sc) == 2:
            deltas.append(delta)
        por_tarea[task] = {"scores": sc, "delta_skills_control": delta}
    media_delta = round(sum(deltas) / len(deltas), 4) if deltas else None
    return {
        "por_brazo": por_brazo,
        "por_tarea": por_tarea,
        "delta_global_skills_control": media_delta,
        "nota": "n=4; dato descriptivo, sin afirmación de significación",
    }


def evaluate_gates(
    cells: list[dict], attempts: int, usage_calls: int, usage_total: int,
    no_leak: tuple[bool, str], tpm: tuple[bool, str], resumen: dict,
) -> dict[str, dict]:
    t1 = attempts == 8 and usage_calls == 8 and usage_total <= BUDGET_TOKENS
    t2 = sum(1 for c in cells if c["main_gd"]) == 8
    t3 = len(cells) == 8 and sum(1 for c in cells if c["suite"].get("build_ok")) >= 6
    t4 = no_leak[0]
    t5 = tpm[0]
    t6 = (
        len(cells) == 8
        and all(resumen["por_brazo"].get(a, {}).get("n") == 4 for a in ARMS)
        and resumen.get("delta_global_skills_control") is not None
    )
    return {
        "T1": {"ok": t1, "detalle": f"intentos={attempts}/8 · calls_usage={usage_calls}/8 · tokens={usage_total} ≤ {BUDGET_TOKENS}"},
        "T2": {"ok": t2, "detalle": f"main.gd parseado={sum(1 for c in cells if c['main_gd'])}/8"},
        "T3": {"ok": t3, "detalle": f"suites={len(cells)}/8 · BUILD>0={sum(1 for c in cells if c['suite'].get('build_ok'))}/8 (≥6)"},
        "T4": {"ok": t4, "detalle": no_leak[1]},
        "T5": {"ok": t5, "detalle": tpm[1]},
        "T6": {"ok": t6, "detalle": f"media delta skills-control={resumen.get('delta_global_skills_control')}"},
    }


def dry_run() -> int:
    task_texts = load_task_texts()
    skills = load_skills()
    briefing = build_briefing(skills)
    cells = build_cells(task_texts, briefing)
    no_leak = validate_no_leak(briefing, cells, task_texts)
    tpm = check_tpm(cells)
    print("HITO27 · H26-B Fase 2 · DRY-RUN (sin LLM)")
    print(f"tareas: {', '.join(TASKS)}")
    print(f"skills: {len(skills)} · briefing={len(briefing)} chars")
    for c in cells:
        print(
            f"  {c['task']:<30} {c['arm']:<8} prompt={c['prompt_chars']:>5} chars "
            f"≈{c['prompt_tokens_est']:>4} tok · request≈{c['prompt_tokens_est'] + MAX_TOKENS}"
        )
    print(f"T4 no fuga: {'OK' if no_leak[0] else 'FALLA'} — {no_leak[1]}")
    print(f"T5 TPM:     {'OK' if tpm[0] else 'FALLA'} — {tpm[1]}")
    print(
        f"presupuesto: 8 llamadas × max_tokens={MAX_TOKENS} + prompts "
        f"≈{sum(c['prompt_tokens_est'] for c in cells)} → "
        f"techo {BUDGET_TOKENS} (cota superior ≈"
        f"{sum(c['prompt_tokens_est'] for c in cells) + 8 * MAX_TOKENS})"
    )
    print(f"salida prevista: {OUT_JSON}")
    return 0 if no_leak[0] and tpm[0] else 1


def _run(out: Path) -> int:
    os.environ["LLM_PROVIDERS"] = "groq"
    os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-120b")
    task_texts = load_task_texts()
    skills = load_skills()
    briefing = build_briefing(skills)
    cells = build_cells(task_texts, briefing)
    no_leak = validate_no_leak(briefing, cells, task_texts)
    tpm = check_tpm(cells)
    if not no_leak[0] or not tpm[0]:
        print(f"ABORTADO antes de gastar: T4={no_leak} T5={tpm}")
        return 1

    out_dir = WS_BASE
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"HITO27 · H26-B Fase 2 · RUN · {len(cells)} celdas · techo {BUDGET_TOKENS}")
    registros = []
    usage_total = 0
    usage_calls = 0
    for i, cell in enumerate(cells, 1):
        print(f"\n[{i}/{len(cells)}] {cell['task']} · {cell['arm']}", flush=True)
        reg = run_cell(cell, out_dir)
        registros.append(reg)
        usage_total += int(reg["usage"].get("total_tokens") or 0)
        usage_calls += int(reg["usage"].get("calls") or 0)
        if usage_total > BUDGET_TOKENS:
            print(f"STOP: tokens={usage_total} > techo {BUDGET_TOKENS}")
            break

    resumen = summarize(registros)
    gates = evaluate_gates(
        registros, len(registros), usage_calls, usage_total, no_leak, tpm, resumen
    )
    todos = all(g["ok"] for g in gates.values())
    salida = {
        "hito": 27,
        "fase": "H26-B Fase 2 — transferencia skills → B-1 v2",
        "fecha": datetime.now(UTC).isoformat(),
        "plan": str(ROOT / "evals/HITO27_PLAN.md"),
        "modelo": os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
        "max_tokens": MAX_TOKENS,
        "tareas": list(TASKS),
        "brazos": list(ARMS),
        "skills": [n for n, _ in skills],
        "briefing_chars": len(briefing),
        "techo_tokens": BUDGET_TOKENS,
        "usage_total": {
            "calls": usage_calls,
            "total_tokens": usage_total,
        },
        "gates": gates,
        "resumen": resumen,
        "celdas": registros,
        "veredicto": "CUMPLE" if todos else "NO CUMPLE",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n" + "=" * 72)
    for k in ("T1", "T2", "T3", "T4", "T5", "T6"):
        g = gates[k]
        print(f"  {k}  {'OK    ' if g['ok'] else 'FALLA '} {g['detalle']}")
    print(
        f"  control={resumen['por_brazo']['control']['media']} · "
        f"skills={resumen['por_brazo']['skills']['media']} · "
        f"delta={resumen['delta_global_skills_control']}"
    )
    print(f"  tokens={usage_total} · veredicto={salida['veredicto']} · {out}")
    print("=" * 72)
    return 0 if todos else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", action="store_true", help="gasta tokens (8 celdas)")
    ap.add_argument("--out", default=str(OUT_JSON), help="JSON de salida")
    args = ap.parse_args()
    return _run(Path(args.out)) if args.run else dry_run()


if __name__ == "__main__":
    sys.exit(main())
