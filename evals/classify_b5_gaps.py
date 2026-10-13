"""B5 — clasificación mecánica de los módulos que NO llevan puntero.

§8.9 necesita distinguir, sin tocar un LLM, **qué es** un punto sin cita. Las
tres categorías son deterministas sobre el texto del módulo:

    1. `exenta dec.14`        marcada `(propuesta del blueprint)` — sin fuente
                              por definición (dec. 14).
    2. `nota equivocada`      atribuye, pero con `§` / `ecuación` / `figura` /
                              `tabla N` en vez de `[doc:N:M]`. **Fallo de
                              formato**, no de respaldo: se arregla apuntando.
    3. `sin atribucion`       no dice de dónde sale. Infraestructura de
                              despliegue que el paper no describe.

Solo corre sobre blueprints **ya generados**: 0 llamadas de generación, 0
tokens. Es la prueba de que la clasificación de §8.9 no es una lectura.

Uso:  python evals/classify_b5_gaps.py --arm=H --file=evals/result_arm_h.json
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_blueprint_ab import _b5_cita_por_modulo, _bloques_modulos, normalize_pointers

ROOT = Path(__file__).resolve().parents[1]

# Notación que SÍ atribuye pero no con el puntero que pide la regla. Se
# incluye `tabla N` porque el modelo la usa como si fuera una referencia
# estable al paper.
_NOTA = re.compile(
    r"§|\becuaci[oó]n\s*\d|\bec\.\s*\d|\bfigura\s*\d|\bfig\.\s*\d"
    r"|\btabla\s+\d|\bap[eé]ndice\s+\w|\balgoritmo\s+\d|\bcap[ií]tulo\s+\d",
    re.IGNORECASE,
)
_PROPUESTA = re.compile(r"\(propuesta del blueprint\)", re.IGNORECASE)

CATEGORIAS = ("exenta dec.14", "nota equivocada", "sin atribucion")


def clasificar(bloque: str) -> str:
    """Categoría determinista de un módulo sin puntero."""
    if _PROPUESTA.search(bloque):
        return "exenta dec.14"
    if _NOTA.search(bloque):
        return "nota equivocada"
    return "sin atribucion"


def clasificar_arm(
    rows: list[dict],
) -> tuple[dict, list[tuple[str, int, str, str]]]:
    """Devuelve (resumen, fallos). `fallos` = (técnica, run, categoría, texto)."""
    res: dict = {
        "modulos": 0, "con_cita": 0, "sin_cita": 0, "b5": 0.0,
        **{c: 0 for c in CATEGORIAS},
    }
    fallos: list[tuple[str, int, str, str]] = []
    for r in rows:
        texto, _ = normalize_pointers(r["blueprint"])
        bloques = _bloques_modulos(texto)
        con, tot, sin, _ = _b5_cita_por_modulo(r["blueprint"])
        res["modulos"] += tot
        res["con_cita"] += con
        res["sin_cita"] += len(sin)
        for i in sin:
            cat = clasificar(bloques[i - 1])
            res[cat] += 1
            fallos.append((r["technique"], r["run"], cat,
                           " ".join(bloques[i - 1].split())[:200]))
    if res["modulos"]:
        res["b5"] = 100 * res["con_cita"] / res["modulos"]
    return res, fallos


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="H")
    ap.add_argument("--file", default="")
    ap.add_argument("--all", action="store_true", help="resumen por brazo de todos los result_arm_*.json")
    a = ap.parse_args()

    armen = a.arm
    path = Path(a.file) if a.file else ROOT / "evals" / f"result_arm_{armen.lower()}.json"

    if a.all:
        print(f"  {'brazo':6} {'mód':>4} {'cita':>5} {'B5':>7}  "
              f"{'exentas':>7} {'notación':>8} {'sin atrib':>9}")
        print("  " + "-" * 56)
        for p in sorted((ROOT / "evals").glob("result_arm_*.json")):
            rows = [r for r in json.loads(p.read_text(encoding="utf-8"))
                    if r.get("ok") and (r.get("blueprint") or "").strip()]
            if not rows:
                continue
            arm = rows[0].get("arm", p.stem[-1].upper())
            res, _ = clasificar_arm(rows)
            if not res["modulos"]:
                continue
            print(f"  {arm:6} {res['modulos']:>4} {res['con_cita']:>5} "
                  f"{res['b5']:>6.1f}%  {res['exenta dec.14']:>7} "
                  f"{res['nota equivocada']:>8} {res['sin atribucion']:>9}")
        return

    if not path.exists():
        print(f"  sin {path}")
        return

    rows = [r for r in json.loads(path.read_text(encoding="utf-8"))
            if r.get("arm") == a.arm and r.get("ok") and (r.get("blueprint") or "").strip()]
    res, fallos = clasificar_arm(rows)

    print(f"\nB5 — brazo {a.arm}  ({len(rows)} blueprints)")
    print("=" * 70)
    print(f"  módulos totales   {res['modulos']}")
    print(f"  con puntero       {res['con_cita']}")
    print(f"  sin puntero       {res['sin_cita']}")
    print(f"  B5                {res['b5']:.1f}%")
    print()
    c = collections.Counter(f[2] for f in fallos)
    for cat in CATEGORIAS:
        print(f"  {cat:18} {c.get(cat, 0)}")

    if fallos:
        print("\n  Detalle:")
        for tec, run, cat, txt in fallos:
            print(f"    [{cat}] {tec} r{run}")
            print(f"      {txt}")

    print("\n  Categorías: 'nota equivocada' ES atribución y se arregla apuntando;")
    print("  'sin atribucion' es lo que el paper no describe. Ninguna absuelve.")


if __name__ == "__main__":
    main()
