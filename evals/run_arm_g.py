"""Brazo G — Decisión 14 (§6): R8, cita dentro de cada módulo.

Mismo camino de generación que F (`api.blueprint_loop`), mismas reglas de
dec. 11. **La única diferencia entre G y F es R8**, así que G vs F aísla R8.

Umbral **fijado antes de medir** (§6 dec. 14, y §3.1 de donde sale):
- B5 = 100%  («cada módulo»)

Se reportan las dos cifras de B5: con y sin los puntos marcados
`(propuesta del blueprint)`, que por definición no pueden llevar puntero.

**B5 se mide con la comprobación corregida** (errata sexta): secciones de
módulos/dependencias, items con viñeta o numeración + negrita.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_blueprint_ab import RUNS, _corpus, _techniques, score

from bibliotecario import api

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "result_arm_g.json"
ARM = "G"


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
    global OUT, ARM
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="G")
    ap.add_argument("--out", default="evals/result_arm_g.json")
    a = ap.parse_args()
    ARM = a.arm
    OUT = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    goal = "validar mi agente antes de cada release"
    prev: list[dict] = []
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    hecho = {(r["technique"], r["run"]) for r in prev if r.get("ok")}
    for tech in _techniques():
        for i in range(RUNS):
            if (tech, i) in hecho:
                print(f"  [G] {tech} run {i} ... ya hecha, salto")
                continue
            print(f"  [G] {tech} run {i} ...", end=" ", flush=True)
            r = run_one(tech, goal, i)
            prev.append(r)
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1),
                           encoding="utf-8")
            if r["ok"]:
                c = r["checks"]
                print(f"ok {r['secs']}s  B5={c['b5_con_cita']}/{c['b5_total']} "
                      f"(exentas={c['b5_exentas']})  citas={c['citas']}")
            else:
                print(f"ERROR {r.get('error')}")
    _resumen(prev)


def _b5(rs: list[dict]) -> tuple[int, int, int]:
    ok = [r for r in rs if r.get("ok") and r["checks"]["b5_total"]]
    con = sum(r["checks"]["b5_con_cita"] for r in ok)
    tot = sum(r["checks"]["b5_total"] for r in ok)
    ex = sum(r["checks"]["b5_exentas"] for r in ok)
    return con, tot, ex


def _resumen(rs: list[dict]) -> None:
    ok = [r for r in rs if r.get("ok")]
    print("\n" + "=" * 70)
    print(f"Resumen brazo G (R8) — n={len(ok)}/{len(rs)}")
    print("=" * 70)
    if not ok:
        return
    con, tot, ex = _b5(ok)
    sin_ex = tot - ex
    print(f"  B5 estricto   {con}/{tot} = {100 * con / tot:.1f}%   [umbral 100%]"
          if tot else "  B5 sin items medibles")
    print(f"  B5 sin propias {con}/{sin_ex} = {100 * con / sin_ex:.1f}%"
          if sin_ex > 0 else "  B5 sin propias: n/a")
    print(f"  puntos marcados (propuesta del blueprint): {ex}")
    print(f"  B6 completo   {sum(1 for r in ok if r['checks']['b6_completo'])}/{len(ok)}")
    print("\n  Comparar con F (sin R8) y con G (R8 antes de la enmienda).")


if __name__ == "__main__":
    main()
