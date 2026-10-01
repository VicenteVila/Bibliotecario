"""Replay offline del paso A del plan: ancla numerica.

Toda cifra de la respuesta final deberia aparecer literalmente en el chunk que
cita. `pg-b5` se invento el 4,003.24 mientras citaba [2:82] de verdad.

Este script NO toca produccion: replaya las runs ya grabadas (r1-r6) y mide
cuantas cifras quedan sin respaldo, con y sin el filtro de contiguidad, para
decidir si el paso merece la pena. La puerta del plan es <5%.

El detalle que hace el trabajo de verdad es no contar como violaciones:
  - los numeros de los propios marcadores de cita ([2:85] -> 2 y 85)
  - los enteros <= 10, que casi siempre son estructurales ("Mode 5", "seccion 3")

Uso: python evals/replay_numeric_anchor.py
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

EVALS = Path(__file__).parent
ROOT = EVALS.parent
sys.path.insert(0, str(ROOT))

from bibliotecario.core import storage

RUNS = ("r1", "r2", "r3", "r4", "r5", "r6")
GATE = 0.05

CITE = re.compile(r"\[(\d+):(\d+)\]")
# La coma solo cuenta como separador de miles si le sigue un digito: sin esto
# "k = 4, retained paths" captura "4," y parece una cifra sin respaldo.
NUM = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")


def cited_chunks(answer: str) -> list[tuple[int, int]]:
    return [(int(d), int(c)) for d, c in CITE.findall(answer or "")]


def strip_citations(answer: str) -> str:
    """Quita los marcadores para no contar doc_id ni chunk_idx como cifras."""
    return CITE.sub(" ", answer or "")


def numbers_in(answer: str, small_ok: bool) -> list[str]:
    out = []
    for n in NUM.findall(strip_citations(answer)):
        if small_ok and "." not in n and "," not in n and int(n) <= 10:
            continue
        out.append(n.rstrip("."))
    return out


def load_chunks() -> dict[tuple[int, int], str]:
    with storage.get_conn() as c:
        return {(r["doc_id"], r["chunk_idx"]): (r["text"] or "")
                for r in c.execute("SELECT doc_id, chunk_idx, text FROM chunks")}


def neighbours(chunks: dict, doc: int, idx: int, window: int) -> str:
    return " ".join(chunks.get((doc, idx + d), "") for d in range(-window, window + 1))


def analyse(rows, chunks, window: int, small_ok: bool) -> tuple[int, int, Counter]:
    """Devuelve (violaciones, cifras, contra que preguntas)."""
    viol, tot, donde = 0, 0, Counter()
    for x in rows:
        if x.get("unanswerable") or x.get("infra_error") or x["judge"] is None:
            continue
        ans = x["answer"] or ""
        cit = cited_chunks(ans)
        if not cit:
            continue
        # pool: los chunks citados, y ademas sus vecinos contiguos del mismo paper
        pool = " ".join(chunks.get(c, "") for c in cit)
        if window:
            pool += " " + " ".join(
                neighbours(chunks, d, c, window) for d, c in cit)
        pool_sin_espacios = pool.replace(" ", "")
        for n in numbers_in(ans, small_ok):
            tot += 1
            if n not in pool and n not in pool_sin_espacios:
                viol += 1
                donde[x["id"]] += 1
    return viol, tot, donde


def main() -> dict:
    chunks = load_chunks()
    allrows = []
    for run in RUNS:
        f = EVALS / f"result_blind_{run}.json"
        if f.exists():
            allrows.extend(json.loads(f.read_text())["rows"])

    print(f"replay de {len(allrows)} filas (r1-r6)\n")
    print(f"{'configuracion':<44} {'cifras':>7} {'viol':>6} {'%':>7}")
    print("-" * 68)
    configs = [
        ("todo cuenta (lo mas ruidoso)", 0, False),
        ("+ ventana de 1 chunk", 1, False),
        ("+ enteros <=10 son estructurales", 1, True),
        ("ventana 2 + enteros <=10", 2, True),
    ]
    mejor = None
    for nombre, w, s in configs:
        viol, tot, donde = analyse(allrows, chunks, w, s)
        pct = viol / tot if tot else 0.0
        print(f"{nombre:<44} {tot:>7} {viol:>6} {pct:>6.1%}")
        if mejor is None or pct < mejor[0]:
            mejor = (pct, nombre, dict(donde))
    print("-" * 68)
    pct, nombre, donde = mejor
    print(f"mejor configuracion: {nombre}  ->  {pct:.1%}")
    print(f"puerta del plan: <{GATE:.0%}   ->  {'PASA' if pct < GATE else 'NO PASA'}")
    print()
    print("violaciones que quedan, por pregunta:")
    for qid, n in sorted(donde.items(), key=lambda kv: -kv[1]):
        print(f"   {qid:10} {n}")
    out = {"violation_rate": pct, "config": nombre, "por_pregunta": donde}
    (EVALS / "result_numeric_anchor.json").write_text(json.dumps(out, indent=1))
    print(f"\n-> {EVALS / 'result_numeric_anchor.json'}")
    return out


if __name__ == "__main__":
    main()