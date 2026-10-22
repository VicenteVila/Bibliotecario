"""Evaluación de ruta 5 (§8.4): C+P4 + crítico por afirmación + degradación.

Umbrales **fijados antes de la primera run** (§8.4, declaración del
2026-10-12):
- R4 cumple  >= 8/15   (se mantiene el de dec. 10, no se toca)
- B8 resueltas >= 2,00/run   (suelo: impide que «arreglar» R4 sea quitarlo todo)

Contra quién: **el brazo E (2/13)** — ruta 5 corre sobre `run_blueprint()` con
las reglas P4 vigentes, así que E+R5 vs E aísla ruta 5 y solo ruta 5.

`limit=None` es crítico completo (~10k tokens/blueprint, §5.10.1).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_blueprint_ab import RUNS, _corpus, _techniques, score  # reutiliza

from bibliotecario import api

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_route5.json"
ARM = "R5"


def run_one(technique: str, goal: str, run: int) -> dict:
    t = time.time()
    try:
        r = api.blueprint_route5(technique, goal)
    except Exception as e:
        return {"arm": ARM, "technique": technique, "run": run, "ok": False,
                "error": f"{type(e).__name__}: {e}", "secs": round(time.time() - t, 1)}
    bp = r.get("blueprint") or ""
    r5 = r.get("route5") or {}
    checks = score(bp, _corpus())
    return {"arm": ARM, "technique": technique, "run": run, "ok": bool(bp),
            "secs": round(time.time() - t, 1), "blueprint": bp, "checks": checks,
            "route5": {k: r5.get(k) for k in
                       ("violaciones", "fallos", "marcas", "reescrito", "degradadas")},
            "doc_id": r.get("doc_id")}


def main() -> None:
    goal = "validar mi agente antes de cada release"
    prev: list[dict] = []
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    hecho = {(r["technique"], r["run"]) for r in prev if r.get("ok")}
    for tech in _techniques():
        for i in range(RUNS):
            if (tech, i) in hecho:
                print(f"  [R5] {tech} run {i} ... ya hecha, salto")
                continue
            print(f"  [R5] {tech} run {i} ...", end=" ", flush=True)
            r = run_one(tech, goal, i)
            prev.append(r)
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            if r["ok"]:
                c, r5 = r["checks"], r["route5"]
                print(f"ok {r['secs']}s  citas={c['citas']} resueltas={c['citas_resueltas']} "
                      f"degradadas={r5.get('degradadas')} reescrito={r5.get('reescrito')}")
            else:
                print(f"ERROR {r.get('error')}")
    _resumen(prev)


def _resumen(rs: list[dict]) -> None:
    ok = [r for r in rs if r.get("ok")]
    print("\n" + "=" * 70)
    print(f"Resumen ruta 5 — n={len(ok)}/{len(rs)}")
    print("=" * 70)
    if not ok:
        print("  sin runs correctas")
        return
    import statistics as st
    cits = st.mean(r["checks"]["citas"] for r in ok)
    res = st.mean(r["checks"]["citas_resueltas"] for r in ok)
    deg = st.mean((r["route5"].get("degradadas") or 0) for r in ok)
    marc = sum((r["route5"].get("marcas") or {}).get("no_sostenida", 0) for r in ok)
    rotos = sum((r["route5"].get("marcas") or {}).get("puntero_roto", 0) for r in ok)
    fallos = sum(len(r["route5"].get("fallos") or []) for r in ok)
    reesc = sum(1 for r in ok if r["route5"].get("reescrito"))
    print(f"  citas/run                       {cits:.2f}")
    print(f"  B8 resueltas/run                {res:.2f}   [umbral >= 2,00]")
    print(f"  degradadas/run                  {deg:.2f}")
    print(f"  marcas: no_sostenida={marc}  puntero_roto={rotos}")
    print(f"  llamadas al juez ilegibles      {fallos}")
    print(f"  reescritos (tiene que ser 0)    {reesc}")
    print(f"\n  B8 umbral: {'CUMPLE' if res >= 2.0 else 'NO CUMPLE'}")
    print("  R4 se puntúa aparte: eval_q1_r4r5.py --arm=R5 + rescore_r4.py --arm=R5")


if __name__ == "__main__":
    main()
