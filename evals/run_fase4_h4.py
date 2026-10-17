"""Hito 3, Fase 4 — H4: evaluación de arneses como variable (A/B + placebo).

Declaración previa en `evals/HITO3_PLAN.md` (§ Fase 4, escrita ANTES que
este script y antes de medir):

- **Brazos:** A·FULL (`max_turns=4`), B·LOW (`max_turns=1`), A'·PLACEBO
  (copia de A). El presupuesto de turnos es la primera variable de arnés
  porque es real en despliegue y se espera diferencia a priori.
- **Mismo golden set** (`golden_qa.jsonl`, 6 preguntas estratificadas) y
  **mismo juez** pineado (`evals/judge.py`, familia distinta del agente).
- **Temperatura 0.0** en los tres brazos (varianza del proveedor, no del
  muestreo). Sin pinear proveedor: rotación por defecto idéntica.
- **Métrica:** juez 1-5; media e IC 95% (t de Student) por brazo; diferencia
  de brazos con IC de Welch.
- **Umbrales:** (1) 18 runs sin crash, >2/6 caídas de infra en un brazo =
  NO CUMPLE; (2) n, media, IC 95% por brazo; (3) placebo A vs A' con 0
  dentro del IC; (4) LOW vs FULL con 0 fuera del IC.

Reutiliza `run_one` de `eval_end2end.py`: el juez, la rúbrica, la exclusión
de infraestructura y el score 0-1 son los mismos que la eval end-to-end —
aquí solo cambia la configuración del arnés por brazo.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from evals.eval_end2end import run_one  # noqa: E402
from evals.judge import JUDGE_MODEL  # noqa: E402

ROOT = EVALS.parent
OUT = ROOT / "evals" / "result_fase4_h4.json"
GOLDEN = ROOT / "evals" / "golden_qa.jsonl"
ARM = "H4"
TEMP = 0.0

# (nombre, max_turns) — A y A' idénticas a propósito (placebo).
ARMS = (("A_full", 4), ("B_low", 1), ("A_placebo", 4))

# Regla determinista declarada: las primeras dos de cada dificultad en orden
# de archivo de golden_qa.jsonl.
IDS = ("pearl-1", "proc-1", "pearl-2", "proc-2", "pearl-3", "proc-3")

_T = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
      7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
      13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
      19: 2.093, 20: 2.086}


def _t(df: int) -> float:
    return _T.get(max(1, min(df, 20)), 1.96)


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def _var(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = sum(xs) / len(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _ic95(xs: list[float]) -> list[float] | None:
    """IC 95% de la media: media ± t(n-1)·s/√n."""
    if not xs:
        return None
    m = sum(xs) / len(xs)
    half = _t(len(xs) - 1) * math.sqrt(_var(xs) / len(xs))
    return [round(m - half, 3), round(m + half, 3)]


def _welch(a: list[float], b: list[float]) -> dict:
    """Diferencia de medias a−b con IC 95% de Welch."""
    if not a or not b:
        return {"diff": None, "ic95": None, "separa": None}
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    va, vb = _var(a), _var(b)
    na, nb = len(a), len(b)
    se2 = va / na + vb / nb
    if se2 == 0:
        # Varianza cero en ambos brazos: la diferencia es exacta.
        return {"diff": round(ma - mb, 3), "ic95": [round(ma - mb, 3)] * 2,
                "separa": ma != mb}
    df = se2 ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    half = _t(int(df)) * math.sqrt(se2)
    lo, hi = round(ma - mb - half, 3), round(ma - mb + half, 3)
    return {"diff": round(ma - mb, 3), "ic95": [lo, hi], "separa": not (lo <= 0 <= hi)}


def _scores(filas: list[dict]) -> list[float]:
    """Juez 1-5 de las filas no infra. Juez no parseable = 0 (misma regla
    que aggregate de eval_end2end: un fallo de juez no se descarta en
    silencio)."""
    out = []
    for f in filas:
        if f.get("infra_error"):
            continue
        out.append(float(f.get("judge") or 0))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    out = Path(args.out)

    golden = {json.loads(l)["id"]: json.loads(l)
              for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()}
    preguntas = [golden[i] for i in IDS]

    prev: list[dict] = []
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8")).get("filas", [])
    # Clave de reanudación: (config, id). "arm" es siempre "H4" (el nombre de
    # esta evaluación); la configuración del arnés es "config".
    hecho = {(f["config"], f["id"]) for f in prev if f.get("ok")}

    print("=" * 74)
    print(f"H4 — A/B de arneses + placebo · n={len(preguntas)} · juez {JUDGE_MODEL} · temp {TEMP}")
    print("=" * 74)

    filas = list(prev)
    for arm, turns in ARMS:
        for q in preguntas:
            if (arm, q["id"]) in hecho:
                print(f"  [{arm}] {q['id']:8} ... ya hecha, salto")
                continue
            t0 = time.time()
            print(f"  [{arm}] {q['id']:8} turns={turns} ...", end=" ", flush=True)
            try:
                r = run_one(q, turns=turns, temperature=TEMP)
                fila = {"arm": ARM, "config": arm, "max_turns": turns,
                        "id": q["id"], "difficulty": q["difficulty"],
                        "ok": True, "secs": round(time.time() - t0, 1),
                        "judge": r.get("judge"), "score01": None,
                        "infra_error": r.get("infra_error"),
                        "judge_error": r.get("judge_error"),
                        "answer_has_cite": r.get("answer_has_cite"),
                        "latency_s": r.get("latency_s"),
                        "answer": (r.get("answer") or "")[:600]}
                # score 0-1 del propio harness (run_score), para lectura.
                sc = r.get("judge")
                fila["score01"] = None if (r.get("infra_error") or sc is None) \
                    else round(min(1.0, max(0.0, (sc - 1) / 4)), 3)
            except Exception as e:  # noqa: BLE001 — bug nuestro: se ve y se para
                raise
            filas.append(fila)
            out.write_text(json.dumps({"arm": ARM, "filas": filas},
                                      ensure_ascii=False, indent=1), encoding="utf-8")
            if fila["infra_error"]:
                print(f"INFRA {fila['infra_error'][:60]}")
            else:
                print(f"juez={fila['judge']} {fila['secs']}s")

    # ---- agregados por brazo -------------------------------------------------
    brazos: dict[str, dict] = {}
    for arm, turns in ARMS:
        fs = [f for f in filas if f["config"] == arm]
        scores = _scores(fs)
        infra = sum(1 for f in fs if f.get("infra_error"))
        brazos[arm] = {"max_turns": turns, "n": len(fs),
                       "n_scored": len(scores), "n_infra": infra,
                       "juez_mean": _mean(scores), "juez_ic95": _ic95(scores),
                       "scores": scores}

    comparaciones = {
        "separacion_low_vs_full": _welch(brazos["B_low"]["scores"],
                                         brazos["A_full"]["scores"]),
        "placebo_full_vs_placebo": _welch(brazos["A_full"]["scores"],
                                          brazos["A_placebo"]["scores"]),
    }

    # ---- umbrales ------------------------------------------------------------
    print("-" * 74)
    for arm, b in brazos.items():
        print(f"  {arm:12} turns={b['max_turns']} n={b['n_scored']}/{b['n']} "
              f"juez={b['juez_mean']} IC95={b['juez_ic95']} infra={b['n_infra']}")
    sep = comparaciones["separacion_low_vs_full"]
    pla = comparaciones["placebo_full_vs_placebo"]
    pla_txt = "placebo OK (0 dentro)" if pla["separa"] is False else "placebo ROTO (0 fuera)"
    print("-" * 74)
    print(f"  LOW−FULL  diff={sep['diff']} IC95={sep['ic95']} -> "
          f"{'SEPARA' if sep['separa'] else 'NO SEPARA'}")
    print(f"  FULL−PLAC diff={pla['diff']} IC95={pla['ic95']} -> {pla_txt}")

    u1 = all(b["n"] == len(preguntas) for b in brazos.values())  # 18/18 sin crash
    u1b = all(b["n_infra"] <= 2 for b in brazos.values())        # >2/6 caídas = no
    u2 = all(b["juez_mean"] is not None for b in brazos.values())
    u3 = pla["separa"] is False
    u4 = sep["separa"] is True
    cerrada = u1 and u1b and u2 and u3 and u4
    print("-" * 74)
    print(f"  (1) 18 runs completas, <=2 infra/brazo : {'CUMPLE' if (u1 and u1b) else 'NO CUMPLE'}")
    print(f"  (2) n/media/IC95 por brazo             : {'CUMPLE' if u2 else 'NO CUMPLE'}")
    print(f"  (3) placebo: 0 dentro del IC            : {'CUMPLE' if u3 else 'NO CUMPLE'}")
    print(f"  (4) separacion: 0 fuera del IC          : {'CUMPLE' if u4 else 'NO CUMPLE'}")
    print(f"  H4: {'CUMPLE' if cerrada else 'NO CUMPLE'}")

    out.write_text(json.dumps(
        {"arm": ARM, "juez": JUDGE_MODEL, "temperature": TEMP,
         "ids": list(IDS), "umbrales": {"u1_runs": u1 and u1b, "u2_agregados": u2,
                                        "u3_placebo": u3, "u4_separacion": u4},
         "h4": cerrada, "brazos": brazos, "comparaciones": comparaciones,
         "filas": filas},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n  -> {out}")
    return 0 if cerrada else 1


if __name__ == "__main__":
    raise SystemExit(main())
