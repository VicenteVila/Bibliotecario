"""Estimación full-set consciente del muestreo, Task-CoEvolve Fase 2-3 (ecs. 3-4).

- Hájek (ec. 3): Ŝ = Σ_{t∈S} x_t/π_t / Σ_{t∈S} 1/π_t — pools con tasas cerca de 0/1.
- Diferencia anclada (ec. 4): Ŝ = (1/N)Σ_T p̄_t + (1/N)Σ_S (x_t−p̄_t)/π_t — tasas al medio.
- Regla §3.3: Hájek si la media global está cerca de 0/1 (margen 0.15), si no anclada.
- Selección Ŝ-max con desempate a la iteración más temprana.
"""
from __future__ import annotations

EDGE_MARGIN = 0.15


def hajek(sampled: dict[int, float], pi: dict[int, float]) -> float:
    num = sum(x / pi[t] for t, x in sampled.items())
    den = sum(1.0 / pi[t] for t in sampled)
    return num / den if den else 0.0


def anchored_difference(sampled: dict[int, float], anchors: dict[int, float],
                        n_total: int, pi: dict[int, float]) -> float:
    base = sum(anchors.values()) / n_total if n_total else 0.0
    adj = sum((x - anchors.get(t, 0.5)) / pi[t] for t, x in sampled.items()) / n_total if n_total else 0.0
    return base + adj


def choose_estimator(stats: list[dict]) -> str:
    if not stats:
        return "hajek"
    mean = sum(s["pbar"] for s in stats) / len(stats)
    if mean < EDGE_MARGIN or mean > 1 - EDGE_MARGIN:
        return "hajek"
    return "anchored"


def estimate_full(sampled: dict[int, float], stats: list[dict], pi: dict[int, float]) -> tuple[float, str]:
    by_id = {s["id"]: s for s in stats}
    which = choose_estimator(stats)
    if which == "hajek":
        return hajek(sampled, pi), which
    anchors = {s["id"]: s["pbar"] for s in stats}
    return anchored_difference(sampled, anchors, len(by_id), pi), which


def select_best(scores: list[tuple[float, int]]) -> int:
    """scores: [(Ŝ, iter)]. Mayor Ŝ; empate exacto → iteración más temprana."""
    best_s, best_i = None, None
    for s, i in scores:
        if best_s is None or s > best_s or (s == best_s and i < best_i):
            best_s, best_i = s, i
    return best_i
