"""Gates del probe SD-4 (HITO24), sin LLM.

R1-R6 se ratifican en `HITO24_PLAN.md` §5 y no se tocan tras medir.
"""
from __future__ import annotations

from statistics import mean

PROBE_TECHO = 250_000
PROBE_MAX_TURNS = 16
A1_LT_100_MIN = 3
A5_LT_100_MIN = 1
A5_WRITES_MIN = 2
A5_NOT_STUCK_MIN = 2
A5_GE_80_MIN = 2


def _media(valores: list[float]) -> float:
    return round(mean(valores), 4) if valores else 0.0


def _coste(cells: dict) -> dict:
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


def probe_gates(
    matrix: dict[str, dict[str, float]],
    cells: dict,
    tasks: list[str],
    *,
    techo: int = PROBE_TECHO,
    max_turns: int = PROBE_MAX_TURNS,
) -> dict:
    valid: list[str] = []
    for tid in tasks:
        a1 = cells.get(f"A1_{tid}")
        a5 = cells.get(f"A5_{tid}")
        if (
            a1
            and a5
            and a1.get("score") is not None
            and a5.get("score") is not None
            and not a1.get("infra_error")
            and not a5.get("infra_error")
        ):
            valid.append(tid)

    a1_scores = [float(matrix["A1"][t]) for t in valid]
    a5_scores = [float(matrix["A5"][t]) for t in valid]
    a1_media = _media(a1_scores)
    a5_media = _media(a5_scores)
    a1_lt_100 = sum(1 for score in a1_scores if score < 100)
    a5_lt_100 = sum(1 for score in a5_scores if score < 100)
    a5_ge_80 = sum(1 for score in a5_scores if score >= 80)

    a5_cells = [cells[f"A5_{t}"] for t in valid]
    a5_writes = sum(1 for cell in a5_cells if int(cell.get("writes") or 0) > 0)
    a5_not_stuck = sum(
        1
        for cell in a5_cells
        if not (
            int(cell.get("turns") or 0) >= max_turns
            and int(cell.get("writes") or 0) == 0
        )
    )

    coste = _coste(cells)
    gates = {
        "R1": {
            "ok": len(valid) == len(tasks),
            "valor": f"{len(valid)}/{len(tasks)}",
            "detalle": "3/3 tareas con A1 y A5 válidas, sin infra_error",
        },
        "R2": {
            "ok": a1_media <= 10 and a1_lt_100 >= A1_LT_100_MIN,
            "valor": {
                "media_A1": a1_media,
                "A1_lt_100": a1_lt_100,
                "min": A1_LT_100_MIN,
            },
            "detalle": "media A1 <= 10 y 3/3 A1 < 100",
        },
        "R3": {
            "ok": (
                a5_media >= 60
                and a5_media >= a1_media + 10
                and a5_lt_100 >= A5_LT_100_MIN
            ),
            "valor": {
                "media_A1": a1_media,
                "media_A5": a5_media,
                "diferencia": round(a5_media - a1_media, 4),
                "A5_lt_100": a5_lt_100,
                "min": A5_LT_100_MIN,
            },
            "detalle": "media A5 >= 60, A5 >= A1+10 y >=1/3 A5 < 100",
        },
        "R4": {
            "ok": a5_writes >= A5_WRITES_MIN and a5_not_stuck >= A5_NOT_STUCK_MIN,
            "valor": {
                "A5_con_escritura": a5_writes,
                "A5_no_atascada": a5_not_stuck,
                "min": A5_WRITES_MIN,
            },
            "detalle": "A5 escribe en >=2/3 y no agota 16 turnos sin escribir",
        },
        "R5": {
            "ok": coste["total_tokens"] <= techo,
            "valor": coste["total_tokens"],
            "detalle": f"coste <= {techo}",
        },
        "R6": {
            "ok": a5_ge_80 >= A5_GE_80_MIN,
            "valor": {
                "A5_ge_80": a5_ge_80,
                "min": A5_GE_80_MIN,
            },
            "detalle": "A5 >= 80 en >=2/3 tareas",
        },
    }
    return {
        "gates": gates,
        "cumple": all(gate["ok"] for gate in gates.values()),
        "valid_tasks": valid,
        "medias": {"A1": a1_media, "A5": a5_media},
        "diferencia_A1_A5": round(a5_media - a1_media, 4),
        "A1_lt_100": a1_lt_100,
        "A5_lt_100": a5_lt_100,
        "A5_ge_80": a5_ge_80,
        "A5_writes": a5_writes,
        "A5_not_stuck": a5_not_stuck,
        "coste": coste,
    }
