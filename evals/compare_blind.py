"""Compara runs del blind de forma pareada por pregunta.

Uso:
    python evals/compare_blind.py a.json b.json [c.json ...]

Lo que hace, y por que existe:

- Reproduce los agregados con el MISMO `aggregate()` que genera cada run, para
  que la tabla no pueda divergir del numero impreso por la propia run.
- El test es PAREADO POR PREGUNTA sobre las preguntas contestadas por las dos
  runs. Con la misma pregunta y dos sistemas, la varianza entre preguntas (que
  es enorme: sd intra-item 0,709) se cancela. Sin parear, el MDE sube de 0,112
  a 0,194 y la mitad de las mejoras reales no se ven.
- Wilcoxon por ser la prueba por pares por defecto (no asume normalidad de la
  diferencia) y el t pareado como referencia, que es con el que se calcularon
  los umbrales del Hito 1.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from scipy import stats

from evals.eval_end2end import aggregate

EVALS = Path(__file__).resolve().parent


def load(nombre: str) -> tuple[dict, dict]:
    """(rows, aggregate) — el aggregate del propio fichero si existe, si no se recalcula."""
    p = EVALS / nombre if not Path(nombre).is_absolute() else Path(nombre)
    d = json.loads(p.read_text())
    rows, agg = d["rows"], d.get("aggregate") or {}
    if not agg.get("judge_mean"):
        agg = aggregate(rows, agg.get("turns", 4), agg.get("retries", 1))
    return rows, agg


def juez_por_pregunta(rows: list) -> dict[str, float]:
    """{id: juez} SOLO de respondibles sin infra y con juez parseable."""
    out = {}
    for r in rows:
        if r.get("unanswerable") or r.get("infra_error") or r.get("judge") is None:
            continue
        out[r["id"]] = float(r["judge"])
    return out


def tabla(nombres: list[str]) -> None:
    print(f"{'fichero':34} {'juez':>6} {'n':>4} {'fab':>6} {'abst':>6} {'cite_p':>6} {'tokens':>9}")
    print("-" * 78)
    for n in nombres:
        _, a = load(n)
        fab = a.get("n_fabricated", 0)
        nu = a.get("n_unanswerable", 0) or 0
        print(f"{n:34} {a.get('judge_mean') or 0:6.3f} {a.get('n_scored') or 0:4d} "
              f"{(fab / nu if nu else 0):6.3f} {a.get('abstain_rate') or 0:6.3f} "
              f"{a.get('cite_precision_mean') or 0:6.3f} {a.get('n') or 0:9d}")
    print()


def pareado(a: str, b: str) -> None:
    ra, _ = load(a)
    rb, _ = load(b)
    ja, jb = juez_por_pregunta(ra), juez_por_pregunta(rb)
    ids = sorted(set(ja) & set(jb))
    if len(ids) < 3:
        print(f"{a} vs {b}: solo {len(ids)} preguntas en comun, sin test\n")
        return

    da = np.array([ja[i] for i in ids])
    db = np.array([jb[i] for i in ids])
    diff = da - db
    t, p_t = stats.ttest_rel(da, db)
    try:
        w, p_w = stats.wilcoxon(da, db)
    except ValueError:
        w, p_w = float("nan"), float("nan")

    # MDE al 95% con n pareado y la sd de las diferencias observadas aqui.
    n = len(ids)
    sd = float(np.std(diff, ddof=1)) if n > 1 else float("nan")
    mde = 1.96 * sd / np.sqrt(n) if n > 1 else float("nan")

    print(f"{Path(a).name}  vs  {Path(b).name}")
    print(f"  n pareado        = {n}")
    print(f"  media {Path(a).name[:20]:20} = {da.mean():.3f}")
    print(f"  media {Path(b).name[:20]:20} = {db.mean():.3f}")
    print(f"  delta            = {diff.mean():+.3f}")
    print(f"  sd diferencias   = {sd:.3f}   MDE95 = {mde:.3f}")
    print(f"  t pareado        = {t:+.3f}  p = {p_t:.4f}")
    print(f"  wilcoxon         = {w:+.1f}  p = {p_w:.4f}")
    print()


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        return
    tabla(args)
    for i in range(1, len(args)):
        pareado(args[0], args[i])


if __name__ == "__main__":
    main()
