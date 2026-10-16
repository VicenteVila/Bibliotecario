"""Hito 3, Fase 1 — regenera los 5 arneses por la ruta verificada (H1).

Declaración previa en `evals/HITO3_PLAN.md` (2026-10-16, escrita ANTES de
generar nada):

- **Ruta:** `instantiate_agent_template` → `build_blueprint_p4`
  (loop P1' + reglas R1-R8 + `verify_and_mark`, sin reescritura). Es la
  composición del brazo E, la única candidata que verifica sin reescribir.
- **n = 5** — una instancia por cada técnica sembrada (el goal es el mismo
  del Hito 2: `GOAL` de run_dimension_d). `--runs` > 1 solo se usa con una
  serie nueva y declarada (para que la escala /15 del Hito 2 sea evaluable).
- **Sin pin de proveedor** — rotación por defecto (Groq → NVIDIA → Gemini),
  temperaturas por defecto, como en todos los brazos del Hito 2.

Escribe una fila `arm="H1"` por arnés en `result_fase1_h1.json` (mismo
esqueleto que las filas del A/B). El juicio R4/R5 va aparte, con el juez
reproducible del Hito 2:

    JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... Q1_API_KEY=... \
      python evals/eval_q1_r4r5.py --arm=H1 --file=evals/result_fase1_h1.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_blueprint_ab import _corpus, score
from run_dimension_d import GOAL, TECNICAS

from bibliotecario.agent.tools import instantiate_agent_template

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "result_fase1_h1.json"
ARM = "H1"


def run_one(technique: str, run: int, corpus: dict) -> dict:
    t = time.time()
    try:
        res = instantiate_agent_template(technique, GOAL)
    except Exception as e:
        return {"arm": ARM, "technique": technique, "run": run, "ok": False,
                "error": f"{type(e).__name__}: {e}", "secs": round(time.time() - t, 1)}
    bp = res.get("blueprint") or ""
    # Un blueprint del camino de emergencia no es un blueprint: si `generate`
    # devolvió vacío, build_blueprint escribe «(sin LLM…)» y juzgarlo daría
    # un falso NO de H1. Se registra como run fallida, no como arnés.
    ok = bool(bp.strip()) and not bp.lstrip().startswith("(")
    fila: dict = {"arm": ARM, "technique": technique, "run": run, "ok": ok,
                  "secs": round(time.time() - t, 1), "blueprint": bp,
                  "goal": GOAL, "ruta": "build_blueprint_p4",
                  "verificado": res.get("verificado"),
                  "violaciones": len(res.get("violaciones") or [])}
    if ok:
        fila["checks"] = score(bp, corpus)
        fila["dir"] = res.get("dir")
    else:
        fila["error"] = "blueprint vacio o de emergencia (sin LLM)"
    return fila


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=1,
                    help="instancias por técnica (Fase 1 declarada: 1 → 5 arneses)")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)

    prev: list[dict] = []
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8"))
    hecho = {(r["technique"], r["run"]) for r in prev if r.get("ok")}
    corpus = _corpus()

    print("=" * 70)
    print(f"Fase 1 (H1) — ruta build_blueprint_p4 · goal {GOAL!r} · n={len(TECNICAS)}x{args.runs}")
    print("=" * 70)
    fallos = 0
    for tech in TECNICAS:
        for i in range(args.runs):
            if (tech, i) in hecho:
                print(f"  [H1] {tech} run {i} ... ya hecha, salto")
                continue
            print(f"  [H1] {tech} run {i} ...", end=" ", flush=True)
            fila = run_one(tech, i, corpus)
            prev.append(fila)
            out.write_text(json.dumps(prev, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            if fila["ok"]:
                c = fila["checks"]
                print(f"ok {fila['secs']}s  verificado={fila['verificado']} "
                      f"violaciones={fila['violaciones']}  "
                      f"citas={c['citas']} resueltas={c['citas_resueltas']}")
            else:
                fallos += 1
                print(f"ERROR {fila.get('error')}")

    ok = [r for r in prev if r.get("arm") == ARM and r.get("ok")]
    todas = [r for r in prev if r.get("arm") == ARM]
    print("\n" + "=" * 70)
    print(f"Resumen Fase 1 — arneses H1 con blueprint ok: n={len(ok)}/{len(todas)}")
    print("=" * 70)
    if ok:
        k = len(ok)
        print(f"  citas/run        {sum(r['checks']['citas'] for r in ok) / k:.2f}")
        print(f"  resueltas/run    {sum(r['checks']['citas_resueltas'] for r in ok) / k:.2f}")
        print(f"  violaciones P3   {sum(r['violaciones'] for r in ok) / k:.2f} "
              f"(informativo: verify_and_mark no reescribe)")
    if fallos:
        print(f"\n  {fallos} runs fallidas en esta corrida — se reintentan "
              f"re-ejecutando el script (no se juzgan)")
        return 1
    print(f"\n  -> {out}")
    print("  Siguiente: juicio R4/R5 con eval_q1_r4r5.py --arm=H1 (ver cabecera)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
