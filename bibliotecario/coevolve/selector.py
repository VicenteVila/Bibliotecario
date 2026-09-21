"""Selección por varianza ponderada, Task-CoEvolve Fase 1 (ec. 2).

w_t = max(p̄_t(1−p̄_t), ℓ_t) + λ/√n_t
- Bernoulli variance: máxima en p̄=0.5, cero si siempre acierto/fallo.
- ℓ_t = ℓ>0 si la tarea nunca se resolvió (puede volverse resoluble), 0 en otro caso.
- λ/√n_t: exploración de tareas subobservadas.
"""
from __future__ import annotations

import math
import random

FLOOR_UNSOLVED = 0.05
LAMBDA = 0.5


def weights(stats: list[dict], floor: float = FLOOR_UNSOLVED, lam: float = LAMBDA) -> dict[int, float]:
    out = {}
    for s in stats:
        p, n = s["pbar"], s["n"]
        ell = floor if (n > 0 and p == 0.0) else 0.0
        out[s["id"]] = max(p * (1 - p), ell) + lam / math.sqrt(max(1, n))
    return out


def sample_subset(stats: list[dict], rho: float, seed: int = 0) -> list[int]:
    """Subconjunto de tamaño m=⌈ρN⌉ por muestreo ponderado sin reemplazo."""
    import math as _m
    n = len(stats)
    if n == 0:
        return []
    m = min(n, max(1, _m.ceil(rho * n)))
    w = weights(stats)
    rng = random.Random(seed)
    pool = [s["id"] for s in stats]
    chosen = []
    for _ in range(m):
        total = sum(w[i] for i in pool)
        r = rng.random() * total
        acc = 0.0
        for i in pool:
            acc += w[i]
            if acc >= r:
                chosen.append(i)
                pool.remove(i)
                break
    return chosen


def inclusion_probabilities(stats: list[dict], rho: float, sims: int = 2000, seed: int = 0) -> dict[int, float]:
    """π_t = Pr[t ∈ S] por Monte Carlo (Horvitz-Thompson)."""
    counts = {s["id"]: 0 for s in stats}
    for k in range(sims):
        for i in sample_subset(stats, rho, seed=seed + k):
            counts[i] += 1
    return {i: max(c / sims, 1e-6) for i, c in counts.items()}
