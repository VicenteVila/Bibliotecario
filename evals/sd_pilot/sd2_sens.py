"""Gates, bootstrap y varianza de SD-2 (HITO22).

No modifica `sens.py` (H19): SD-2 tiene split, familias y gates propios.
"""
from __future__ import annotations

import math
import random
from statistics import mean

from evals.sd_pilot import sens as sens_h19
from evals.sd_pilot.sd2_tasks import (
    SD2_DEV_TASK_IDS,
    SD2_TEST_TASK_IDS,
)
from evals.sd_pilot.variants import VARIANT_NAMES

MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
MAX_TURNS = 12
CAL_VARIANTS = ("A1", "A5")
OFFICIAL_VARIANTS = VARIANT_NAMES
CAL_TASKS = SD2_DEV_TASK_IDS
OFFICIAL_TASKS = SD2_TEST_TASK_IDS
CAL_TECHO = 700_000
OFICIAL_TECHO = 2_800_000
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20261024


def _num(value) -> float | None:
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and not math.isnan(float(value))
    ):
        return float(value)
    return None


def _values(matrix: dict, variant: str, tasks: list[str]) -> list[float]:
    row = matrix.get(variant, {})
    return [
        float(row[t])
        for t in tasks
        if _num(row.get(t)) is not None
    ]


def _count_below(values: list[float], limit: float = 100.0) -> int:
    return sum(1 for value in values if value < limit)


def _mean(values: list[float]) -> float | None:
    return round(mean(values), 4) if values else None


def _valid_cell(cell: dict | None) -> bool:
    if not cell:
        return False
    if cell.get("infra_error") or cell.get("llm_error"):
        return False
    return _num(cell.get("score")) is not None


def _cost_total(cells: dict) -> dict:
    total = {
        "calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    for cell in cells.values():
        usage = cell.get("usage") or {}
        for key in total:
            total[key] += int(usage.get(key) or 0)
    return total


def calibration_gates(
    matrix: dict[str, dict[str, float]],
    cells: dict[str, dict],
    tasks: list[str] | None = None,
) -> dict:
    """C1-C4 de H22 §4; devuelve gates y métricas, sin LLM."""
    task_list = tasks or CAL_TASKS
    cost = _cost_total(cells)
    valid_tasks = 0
    for task in task_list:
        if all(
            _valid_cell(cells.get(f"{variant}_{task}"))
            for variant in CAL_VARIANTS
        ):
            valid_tasks += 1

    a1 = _values(matrix, "A1", task_list)
    a5 = _values(matrix, "A5", task_list)
    a1_mean = _mean(a1)
    a5_mean = _mean(a5)
    a1_below = _count_below(a1)
    a5_below = _count_below(a5)
    diferencia = (
        round(a1_mean - a5_mean, 4)
        if a1_mean is not None and a5_mean is not None
        else None
    )
    gates = {
        "C1": {
            "ok": valid_tasks == len(task_list),
            "valor": f"{valid_tasks}/{len(task_list)}",
            "umbral": "12/12 tareas con A1 y A5 válidas, sin infra_error",
        },
        "C2": {
            "ok": (
                a1_mean is not None
                and a1_mean <= 85
                and a1_below >= 8
            ),
            "valor": {"media_A1": a1_mean, "A1_lt_100": a1_below},
            "umbral": "media_A1<=85 y A1<100 en >=8/12",
        },
        "C3": {
            "ok": (
                a5_mean is not None
                and a5_mean <= 85
                and a5_below >= 8
                and diferencia is not None
                and diferencia >= 10
            ),
            "valor": {
                "media_A5": a5_mean,
                "A5_lt_100": a5_below,
                "A1_menos_A5": diferencia,
            },
            "umbral": "media_A5<=85, A5<100 en >=8/12 y A1-A5>=10",
        },
        "C4": {
            "ok": cost["total_tokens"] <= CAL_TECHO,
            "valor": cost["total_tokens"],
            "umbral": f"<= {CAL_TECHO}",
        },
    }
    return {
        "gates": gates,
        "cumple": all(g["ok"] for g in gates.values()),
        "coste": cost,
        "valid_tasks": valid_tasks,
        "n_tareas": len(task_list),
        "medias": {"A1": a1_mean, "A5": a5_mean},
        "diferencia_A1_A5": diferencia,
    }


def official_gates(
    matrix: dict[str, dict[str, float]],
    cells: dict[str, dict],
    *,
    lock_ok: bool,
    harness_card_ok: bool,
    model: str = MODEL,
) -> dict:
    """U1-U10 de H22 §5; U3-U7 se delegan en `sens.py`."""
    task_list = OFFICIAL_TASKS
    cost = _cost_total(cells)
    missing = [
        f"{variant}_{task}"
        for variant in OFFICIAL_VARIANTS
        for task in task_list
        if _num(matrix.get(variant, {}).get(task)) is None
    ]
    infra = [
        key
        for key, cell in cells.items()
        if cell.get("infra_error") or cell.get("llm_error")
    ]
    turns_ok = all(
        cell.get("max_turns") == MAX_TURNS for cell in cells.values()
    )
    model_ok = all(cell.get("model") == model for cell in cells.values())
    variants_ok = tuple(OFFICIAL_VARIANTS) == VARIANT_NAMES
    a1 = _values(matrix, "A1", task_list)
    a5 = _values(matrix, "A5", task_list)
    a1_mean = _mean(a1)
    a5_mean = _mean(a5)
    a1_below = _count_below(a1)
    a5_below = _count_below(a5)
    base = sens_h19.compute(matrix, task_list, OFFICIAL_VARIANTS)
    base_gates = base["gates"]
    leak = bool(set(task_list) & set(SD2_DEV_TASK_IDS))
    gates = {
        "U1": {
            "ok": bool(
                variants_ok and turns_ok and model_ok and not infra
            ),
            "valor": {
                "variantes": list(OFFICIAL_VARIANTS),
                "max_turns": MAX_TURNS,
                "modelo": model,
                "infra_error": infra,
            },
            "umbral": "A1-A5, modelo y 12 turnos congelados; sin infra_error",
        },
        "U2": {
            "ok": not missing,
            "valor": f"{len(cells) - len(missing)}/60",
            "umbral": "60/60 celdas sin huecos",
            "faltan": missing,
        },
        "U3": base_gates["U3"],
        "U4": base_gates["U4"],
        "U5": base_gates["U5"],
        "U7": base_gates["U7"],
        "U8": {
            "ok": (
                a1_mean is not None
                and a1_mean <= 80
                and a1_below >= 8
            ),
            "valor": {"media_A1": a1_mean, "A1_lt_100": a1_below},
            "umbral": "media_A1<=80 y A1<100 en >=8/12",
        },
        "U9": {
            "ok": cost["total_tokens"] <= OFICIAL_TECHO,
            "valor": cost["total_tokens"],
            "umbral": f"<= {OFICIAL_TECHO}",
        },
        "U10": {
            "ok": bool(lock_ok and harness_card_ok and not leak),
            "valor": {
                "lock_ok": lock_ok,
                "harness_card_ok": harness_card_ok,
                "fuga_dev_test": leak,
            },
            "umbral": "lock intacto, Harness Card y sin fuga dev->test",
        },
    }
    return {
        "gates": gates,
        "cumple": all(g["ok"] for g in gates.values()),
        "coste": cost,
        "q_h": base["q_h"],
        "spread": base["spread"],
        "sens": base["sens"],
        "n_sens_finitos": base["n_finitos"],
        "n_sens_positivos": base["n_positivos"],
        "medias": {"A1": a1_mean, "A5": a5_mean},
        "A1_lt_100": a1_below,
        "A5_lt_100": a5_below,
        "infra_error": infra,
        "missing": missing,
        "varianza": variance_decomposition(
            matrix, task_list, OFFICIAL_VARIANTS
        ),
        "ic95": bootstrap_summary(matrix, task_list),
    }


def bootstrap_mean_ci(
    values: list[float],
    *,
    n: int = BOOTSTRAP_N,
    seed: int = BOOTSTRAP_SEED,
) -> list[float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    medias = [
        sum(rng.choices(values, k=len(values))) / len(values)
        for _ in range(n)
    ]
    medias.sort()
    lo = medias[int(0.025 * (n - 1))]
    hi = medias[int(0.975 * (n - 1))]
    return [round(lo, 4), round(hi, 4)]


def bootstrap_summary(
    matrix: dict[str, dict[str, float]],
    tasks: list[str],
    variants: tuple[str, ...] = OFFICIAL_VARIANTS,
) -> dict:
    all_values = [
        float(matrix[v][t])
        for v in variants
        for t in tasks
        if _num(matrix.get(v, {}).get(t)) is not None
    ]
    a1 = _values(matrix, "A1", tasks)
    a5 = _values(matrix, "A5", tasks)
    sens_vals = [
        value
        for value in _sens_series(matrix, tasks, variants).values()
        if value is not None
    ]
    return {
        "media_global": bootstrap_mean_ci(all_values),
        "media_A1": bootstrap_mean_ci(a1),
        "media_A5": bootstrap_mean_ci(a5),
        "media_Sens": bootstrap_mean_ci(sens_vals),
        "n": BOOTSTRAP_N,
        "seed": BOOTSTRAP_SEED,
    }


def _sens_series(
    matrix: dict[str, dict[str, float]],
    tasks: list[str],
    variants: tuple[str, ...],
) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for task in tasks:
        loo = sens_h19.leave_one_out(matrix, task)
        xs = [matrix.get(v, {}).get(task) for v in variants]
        ys = [loo.get(v) for v in variants]
        if any(_num(v) is None for v in xs + ys):
            out[task] = None
        else:
            out[task] = sens_h19.pearson(
                [float(v) for v in xs],
                [float(v) for v in ys],
            )
    return out


def variance_decomposition(
    matrix: dict[str, dict[str, float]],
    tasks: list[str],
    variants: tuple[str, ...] = OFFICIAL_VARIANTS,
) -> dict:
    """Descomposición descriptiva tarea/arnés/residual (no es gate)."""
    rows = {
        v: [float(matrix[v][t]) for t in tasks]
        for v in variants
        if all(_num(matrix.get(v, {}).get(t)) is not None for t in tasks)
    }
    if not rows:
        return {"n": 0}
    h = len(rows)
    t = len(tasks)
    flat = [x for row in rows.values() for x in row]
    grand = sum(flat) / len(flat)
    task_means = [
        sum(rows[v][i] for v in rows) / h for i in range(t)
    ]
    harness_means = [sum(row) / t for row in rows.values()]
    ss_task = h * sum((m - grand) ** 2 for m in task_means)
    ss_harness = t * sum((m - grand) ** 2 for m in harness_means)
    ss_total = sum((x - grand) ** 2 for x in flat)
    ss_resid = max(0.0, ss_total - ss_task - ss_harness)
    return {
        "n": len(flat),
        "ss_total": round(ss_total, 4),
        "ss_tarea": round(ss_task, 4),
        "ss_arnes": round(ss_harness, 4),
        "ss_residual": round(ss_resid, 4),
        "pct_tarea": round(100 * ss_task / ss_total, 4) if ss_total else 0.0,
        "pct_arnes": round(100 * ss_harness / ss_total, 4) if ss_total else 0.0,
        "pct_residual": round(100 * ss_resid / ss_total, 4) if ss_total else 0.0,
    }
