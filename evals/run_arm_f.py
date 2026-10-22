"""Brazo F — Decisión 11 (§6): anclar la paráfrasis a una cita literal.

Mismo camino de generación que C y E (`api.blueprint_loop`), con `_WRITING_RULES`
reescrito: R1 exige «<literal>» [doc:N:M] — <paráfrasis>, la cita va primero y
es verificable con regex.

Umbrales **fijados antes de la primera run** (§6 dec. 11):
- R4 cumple        >= 8/15        (sin tocar)
- B9' cumplimiento >= 1,00        (anclas / citas)  — nueva definición
- B8 resueltas     >= 2,00/run    (no se arregla R4 citando menos)
- B11 copiadas     == 0           (sin cambios; sigue cazando plagio)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_blueprint_ab import RUNS, _corpus, _techniques, score

from bibliotecario import api

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_arm_f.json"
ARM = "F"


def run_one(technique: str, goal: str, run: int) -> dict:
    t = time.time()
    try:
        r = api.blueprint_loop(technique, goal)
    except Exception as e:
        return {"arm": ARM, "technique": technique, "run": run, "ok": False,
                "error": f"{type(e).__name__}: {e}", "secs": round(time.time() - t, 1)}
    bp = r.get("blueprint") or ""
    return {"arm": ARM, "technique": technique, "run": run, "ok": bool(bp),
            "secs": round(time.time() - t, 1), "blueprint": bp,
            "checks": score(bp, _corpus()), "doc_id": r.get("doc_id")}


def main() -> None:
    goal = "validar mi agente antes de cada release"
    prev: list[dict] = []
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    hecho = {(r["technique"], r["run"]) for r in prev if r.get("ok")}
    for tech in _techniques():
        for i in range(RUNS):
            if (tech, i) in hecho:
                print(f"  [F] {tech} run {i} ... ya hecha, salto")
                continue
            print(f"  [F] {tech} run {i} ...", end=" ", flush=True)
            r = run_one(tech, goal, i)
            prev.append(r)
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            if r["ok"]:
                c = r["checks"]
                print(f"ok {r['secs']}s  citas={c['citas']} resueltas={c['citas_resueltas']} "
                      f"anclas={c['anclas']} en_fuente={c['anclas_en_fuente']} "
                      f"cumple={c['cumplimiento_b9']:.2f}")
            else:
                print(f"ERROR {r.get('error')}")
    _resumen(prev)


def _resumen(rs: list[dict]) -> None:
    ok = [r for r in rs if r.get("ok")]
    print("\n" + "=" * 70)
    print(f"Resumen brazo F — n={len(ok)}/{len(rs)}")
    print("=" * 70)
    if not ok:
        return
    k = len(ok)
    m = lambda f: sum(f(r["checks"]) for r in ok) / k
    print(f"  R1 citas/run                       {m(lambda c: c['citas']):.2f}")
    print(f"  B8 resueltas/run                   {m(lambda c: c['citas_resueltas']):.2f}   [umbral >= 2,00]")
    print(f"  B9' anclas/run                     {m(lambda c: c['anclas']):.2f}")
    print(f"  B9' de esas en la fuente/run       {m(lambda c: c['anclas_en_fuente']):.2f}")
    print(f"  B9' cumplimiento (anclas/citas)    {m(lambda c: c['cumplimiento_b9']):.2f}   [umbral >= 1,00]")
    print(f"  B9  comillados(def. antigua)/run   {m(lambda c: c['comillados_literales']):.2f}")
    print(f"  B11 frases copiadas/run            {m(lambda c: c['frases_largas_copiadas']):.2f}   [umbral == 0]")
    print(f"  blueprints sin NINGUNA cita        {sum(1 for r in ok if r['checks']['citas']==0)}")
    print("\n  R4 se puntúa aparte: eval_q1_r4r5.py --arm=F --file=evals/results/result_arm_f.json")


if __name__ == "__main__":
    main()
