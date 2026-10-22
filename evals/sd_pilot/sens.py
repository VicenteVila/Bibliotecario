"""Sens(x) de Evo-Bench §4.2 + gates U2-U7 del piloto HITO19.

  Sens(x) = corr_pearson({m_h(x)}, {Q_h^(−x)})   sobre h ∈ H_aux (K=5)
  Q_h^(−x) = media de m_h(·) de h sobre TODAS las tareas salvo x

Umbrales congelados en §2 del plan (ratificación 2026-10-22): NO se tocan
tras medir. Varianza nula en cualquiera de las dos series -> Sens NO
DEFINIBLE (None), que nunca se cuenta como 0.
"""
from __future__ import annotations

import math

from evals.sd_pilot.variants import VARIANT_NAMES

THRESHOLDS = {
    "spread_min": 15.0,        # U3
    "sens_finite_min": 6,      # U4 (de 12 tareas)
    "sens_pos_min": 6,         # U5 (de 12 tareas)
    "mean_global_max": 60.0,   # U7
    "mean_a5_max": 80.0,       # U7
    "a5_below_100_min": 8,     # U7 (de 12 tareas)
}


def pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3 or n != len(ys):
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx <= 0 or dy <= 0:
        return None
    return round(num / math.sqrt(dx * dy), 6)


def leave_one_out(matrix: dict[str, dict[str, float]], task: str) -> dict[str, float]:
    """Q_h^(−x): media de cada arnés sobre las tareas salvo `task`."""
    out: dict[str, float] = {}
    for h, row in matrix.items():
        others = [v for t, v in row.items() if t != task]
        out[h] = sum(others) / len(others) if others else float("nan")
    return out


def completeness(matrix: dict[str, dict[str, float]],
                 variants: tuple[str, ...], tasks: list[str]) -> list[str]:
    """U2: celdas faltantes o no numéricas."""
    missing = []
    for h in variants:
        if h not in matrix:
            missing.append(f"{h}: variante ausente")
            continue
        for t in tasks:
            v = matrix[h].get(t)
            if not isinstance(v, (int, float)):
                missing.append(f"{h}/{t}")
    return missing


def compute(matrix: dict[str, dict[str, float]],
            tasks: list[str],
            variants: tuple[str, ...] = VARIANT_NAMES) -> dict:
    """Matriz -> Q_h, Sens(x) por tarea y veredicto de los gates U2-U7."""
    missing = completeness(matrix, variants, tasks)
    q_full: dict[str, float] = {}
    for h in variants:
        row = matrix.get(h) or {}
        vals = [row.get(t) for t in tasks if isinstance(row.get(t), (int, float))]
        q_full[h] = sum(vals) / len(vals) if vals else float("nan")

    sens: dict[str, float | None] = {}
    loo: dict[str, dict[str, float]] = {}
    for t in tasks:
        loo[t] = leave_one_out(matrix, t)
        m = [matrix.get(h, {}).get(t) for h in variants]
        q = [loo[t].get(h) for h in variants]
        if any(not isinstance(v, (int, float)) for v in m + q):
            sens[t] = None
        else:
            sens[t] = pearson([float(v) for v in m], [float(v) for v in q])

    finitos = [v for v in sens.values() if v is not None]
    positivos = [v for v in finitos if v > 0]
    qs = [v for v in q_full.values() if isinstance(v, (int, float)) and not math.isnan(v)]
    spread = round(max(qs) - min(qs), 4) if len(qs) >= 2 else float("nan")

    all_cells = [v for h in variants for v in matrix.get(h, {}).values()
                 if isinstance(v, (int, float))]
    a5 = [matrix.get("A5", {}).get(t) for t in tasks]
    a5_vals = [float(v) for v in a5 if isinstance(v, (int, float))]
    mean_global = sum(all_cells) / len(all_cells) if all_cells else float("nan")
    mean_a5 = sum(a5_vals) / len(a5_vals) if a5_vals else float("nan")
    a5_below = sum(1 for v in a5_vals if v < 100.0)

    gates = {
        "U2": {"ok": not missing, "valor": f"{len(variants) * len(tasks) - len(missing)}/{len(variants) * len(tasks)}",
               "umbral": "0 huecos", "faltan": missing[:20]},
        "U3": {"ok": bool(spread >= THRESHOLDS["spread_min"]), "valor": spread,
               "umbral": f">= {THRESHOLDS['spread_min']}"},
        "U4": {"ok": len(finitos) >= THRESHOLDS["sens_finite_min"],
               "valor": f"{len(finitos)}/{len(tasks)}", "umbral": f">= {THRESHOLDS['sens_finite_min']}"},
        "U5": {"ok": len(positivos) >= THRESHOLDS["sens_pos_min"],
               "valor": f"{len(positivos)}/{len(tasks)}", "umbral": f">= {THRESHOLDS['sens_pos_min']}"},
        "U7": {"ok": bool(mean_global <= THRESHOLDS["mean_global_max"]
                          and mean_a5 <= THRESHOLDS["mean_a5_max"]
                          and a5_below >= THRESHOLDS["a5_below_100_min"]),
               "valor": {"media_global": round(mean_global, 2) if all_cells else None,
                         "media_A5": round(mean_a5, 2) if a5_vals else None,
                         "A5_lt_100": a5_below},
               "umbral": (f"media_global<= {THRESHOLDS['mean_global_max']}, "
                          f"media_A5<= {THRESHOLDS['mean_a5_max']}, "
                          f"A5<100 en >= {THRESHOLDS['a5_below_100_min']}/12")},
    }
    return {
        "q_h": {h: (round(v, 4) if isinstance(v, float) and not math.isnan(v) else None)
                for h, v in q_full.items()},
        "spread": spread,
        "sens": sens,
        "gates": gates,
        "todos_ok": all(g["ok"] for g in gates.values()),
        "n_finitos": len(finitos),
        "n_positivos": len(positivos),
    }
