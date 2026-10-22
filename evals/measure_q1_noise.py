"""Ruido del juez de R4/R5 — ¿el umbral de R5 se mide o se persigue?

R4 tiene pipeline calibrado (`rescore_r4.py`, dec. 10). **R5 no tiene ninguno**:
sus números salen del juez Q1 en crudo, a `temperature=0.2`. Y R5 está a un
blueprint de su umbral (G: 9/14, umbral >= 10/15).

Antes de gastar una run de generación en subir 9 -> 10, hay que saber si la
propia decisión del juez es estable. Se hace lo mismo que `measure_judge_noise.py`
hace para el juez del QA: **re-juzgar la MISMA respuesta varias veces**. Lo que
varíe entre repeticiones de un mismo blueprint es ruido del juez, por
construcción — el agente no ha vuelto a intervenir.

No se genera nada. Coste: 1 llamada al juez por (blueprint, repetición).

Salida:
    por blueprint:  r5_ok en cada repetición, y si hay flip
    por brazo:       R5 cumple bajo cada repetición — si el umbral se cruza
                     entre repeticiones, la distancia a 10/15 es ruido.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_q1_r4r5 import _source, q1

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_q1_noise.json"

BRAZOS = {
    "B": ROOT / "evals" / "results" / "result_blueprint_ab.json",
    "C": ROOT / "evals" / "results" / "result_blueprint_ab.json",
    "D": ROOT / "evals" / "results" / "result_blueprint_ab.json",
    "E": ROOT / "evals" / "results" / "result_blueprint_ab.json",
    "F": ROOT / "evals" / "results" / "result_arm_f.json",
    "G": ROOT / "evals" / "results" / "result_arm_g.json",
    "G2": ROOT / "evals" / "results" / "result_arm_g2.json",
    "H": ROOT / "evals" / "results" / "result_arm_h.json",
}
UMBRAL_R5 = 10
# se juzga sobre 14-15 blueprints; el umbral esta escrito para 15. Se reportan
# ambas lecturas para no comparar 9/14 con 10/15 como si fuera la misma escala.
N_REF = 15


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="G,H")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()

    filas: list[dict] = []
    out = Path(a.out)
    if out.exists():
        filas = json.loads(out.read_text(encoding="utf-8"))
    # Solo cuenta como hecho lo que devolvió un veredicto: un fallo (429,
    # JSON incomprensible) se reintenta en la siguiente corrida, o una run
    # arruinada por límite de tasa quedaría "completa" y vacía.
    hecho = {(f["arm"], f["technique"], f["run"], f["rep"])
             for f in filas if not f.get("error")}
    seguidos_429 = 0

    for arm in a.arms.split(","):
        src = BRAZOS.get(arm)
        if not src or not src.exists():
            print(f"  sin {arm}: {src}")
            continue
        rows = [r for r in json.loads(src.read_text(encoding="utf-8"))
                if r.get("arm") == arm and r.get("ok") and (r.get("blueprint") or "").strip()]
        for r in rows:
            src_txt = ""
            try:
                src_txt = _source(r["technique"])
            except Exception as e:
                print(f"  [{arm}] {r['technique']} r{r['run']} sin fuente: {e}")
                continue
            for rep in range(a.reps):
                if (arm, r["technique"], r["run"], rep) in hecho:
                    continue
                print(f"  [{arm}] {r['technique']} r{r['run']} rep{rep} ...", end=" ",
                      flush=True)
                res = q1(src_txt, r["blueprint"])
                if "error" in res:
                    # dec. 16.2: un fallo NO es un blueprint menos — se registra.
                    # Y se dice QUÉ falló: un 429 de tasa no es lo mismo que un
                    # JSON mal formado, y mezclarlos en un solo contador miente.
                    print(f"FALLO: {res['error'][:70]}")
                    filas.append({"arm": arm, "technique": r["technique"],
                                  "run": r["run"], "rep": rep,
                                  "r4_ok": None, "r5_ok": None, "error": True,
                                  "motivo": res["error"][:70]})
                    out.write_text(json.dumps(filas, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
                    # Corte de cuota: un 429 persistente es presupuesto diario
                    # agotado. Seguir probando no lo recupera, solo consume.
                    if "429" in res["error"]:
                        seguidos_429 += 1
                        if seguidos_429 >= 4:
                            print(f"\n  CUOTA AGOTADA ({seguidos_429} × 429 seguidos) "
                                  f"— se para aquí, lo hecho queda guardado.")
                            _resumen(filas, a.reps)
                            return
                    else:
                        seguidos_429 = 0
                    continue
                seguidos_429 = 0
                filas.append({"arm": arm, "technique": r["technique"], "run": r["run"],
                              "rep": rep, "r4_ok": res["r4_ok"], "r5_ok": res["r5_ok"],
                              "r5_rellenados": len(res.get("r5_rellenados") or []),
                              "r4_fab": len(res.get("r4_fabricaciones") or []),
                              "error": False})
                out.write_text(json.dumps(filas, ensure_ascii=False, indent=1),
                               encoding="utf-8")
                print(f"R4={'OK' if res['r4_ok'] else 'MAL'} "
                      f"R5={'OK' if res['r5_ok'] else 'MAL'}")

    _resumen(filas, a.reps)


def _resumen(filas: list[dict], reps: int) -> None:
    print("\n" + "=" * 74)
    print("RUIDO DEL JUEZ DE R4/R5")
    print("=" * 74)
    if not filas:
        print("  sin datos")
        return

    # dec. 16.2: los parseos fallidos se contabilizan aparte; no entran en el
    # denominador, pero tampoco desaparecen.
    errs = [f for f in filas if f.get("error")]
    ok = [f for f in filas if not f.get("error")]

    # flips por blueprint: ¿cambia r5_ok entre repeticiones?
    porbp: dict[tuple, list] = collections.defaultdict(list)
    for f in ok:
        porbp[(f["arm"], f["technique"], f["run"])].append(f)
    estables = {k: v for k, v in porbp.items() if len(v) >= 2}
    flips = {k: v for k, v in estables.items()
             if len({bool(x["r5_ok"]) for x in v}) > 1}
    flips4 = {k: v for k, v in estables.items()
              if len({bool(x["r4_ok"]) for x in v}) > 1}

    n_est = len(estables) or 1
    print(f"  juicios emitidos:               {len(filas)}")
    print(f"  juicio fallido:                 {len(errs)} "
          f"({100 * len(errs) / max(len(filas), 1):.0f}%)")
    if errs:
        import collections as _c
        motivos = _c.Counter(
            ("rate limit" if "429" in str(f.get("motivo")) else
             "parseo JSON" if "parseable" in str(f.get("motivo")) else
             str(f.get("motivo"))[:32]) for f in errs)
        for m, c in motivos.most_common():
            print(f"      ↳ {m}: {c}")
    print(f"  blueprints juzgados >= 2 veces: {len(estables)}")
    print(f"  R5 flips de veredicto:          {len(flips)} "
          f"({100 * len(flips) / n_est:.0f}%)")
    print(f"  R4 flips de veredicto:          {len(flips4)} "
          f"({100 * len(flips4) / n_est:.0f}%)")
    sin2 = [k for k, v in porbp.items() if len(v) < 2]
    print(f"  blueprints con <2 juicios válidos (errores de parseo): {len(sin2)}")

    # el conteo por brazo y por repetición: ¿se cruza el umbral?
    print()
    print(f"  R5 cumple por brazo y repetición  [umbral {UMBRAL_R5} sobre {N_REF}]")
    print("  " + "-" * 62)
    for arm in sorted({f["arm"] for f in ok}):
        porrep: dict[int, list] = collections.defaultdict(list)
        for f in ok:
            if f["arm"] != arm:
                continue
            porrep[f["rep"]].append(f)
        if len(porrep) < 2:
            continue
        vals = []
        for rep in sorted(porrep):
            fs = porrep[rep]
            n_ok = sum(1 for x in fs if x["r5_ok"])
            n = len(fs)
            vals.append(n_ok / n)
            print(f"    {arm} rep{rep}:  R5 {n_ok}/{n} = {100 * n_ok / n:.0f}%"
                  f"   (R4 {sum(1 for x in fs if x['r4_ok'])}/{n})")
        import statistics as st
        if len(vals) > 1:
            print(f"    -> {arm}: media {100 * st.mean(vals):.0f}%   "
                  f"rango {100 * (max(vals) - min(vals)):.0f} puntos   "
                  f"sd {100 * st.stdev(vals):.1f}")
        print()

    if flips:
        print("  Blueprints que cambian de veredicto en R5:")
        for k in list(flips)[:8]:
            vs = [bool(x["r5_ok"]) for x in porbp[k]]
            print(f"    {k[1]} r{k[2]}: {vs}")


if __name__ == "__main__":
    main()
