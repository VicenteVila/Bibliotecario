"""Analizador de rachas de trazas (HITO20 §0.1 Parte A, ahora reproducible).

Reglas declaradas en HITO20_PLAN §0.1 — idénticas a las de la evidencia
`result_sens_sd_diag_trazas.json` (que se generó con un snippet ad-hoc;
este módulo las fija como herramienta):

- PROGRESA = escrituras en >=1 de los últimos 3 turnos Y racha máxima de
  acciones idénticas (mismo tool + mismos args) <= 3.
- ATASCADO = racha de idénticas >= 4 O 0 escrituras en los últimos 5 turnos.
- INDETERMINADO = el resto.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

REGLA = ("PROGRESA=escrituras en >=1 de ultimos 3 turnos y racha<=3; "
         "ATASCADO=racha>=4 o 0 escrituras en ultimos 5 turnos")


def clasificar(escrituras_ult3: int, escrituras_ult5: int,
               racha_max_identica: int) -> str:
    if racha_max_identica >= 4 or escrituras_ult5 == 0:
        return "ATASCADO"
    if escrituras_ult3 >= 1 and racha_max_identica <= 3:
        return "PROGRESA"
    return "INDETERMINADO"


def _acciones_tool(db: Path) -> dict[str, list[dict]]:
    """Acciones tool por celda (key A2_tarea), en orden, con turno."""
    conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT metadata, input FROM spans WHERE agent='tool' "
            "ORDER BY rowid").fetchall()
    finally:
        conn.close()
    celdas: dict[str, list[dict]] = {}
    for meta, inp in rows:
        try:
            m = json.loads(meta) if meta else {}
        except (TypeError, ValueError):
            m = {}
        v, t = m.get("variant"), m.get("task")
        if not (v and t):
            continue
        celdas.setdefault(f"{v}_{t}", []).append(
            {"tool": m.get("tool_name", "?"), "args": inp or ""})
    return celdas


def analizar_celda(acciones: list[dict], turns: int) -> dict:
    lecturas = sum(1 for a in acciones if a["tool"] == "read_file")
    escrituras = sum(1 for a in acciones if a["tool"] == "write_file")
    run_tests = sum(1 for a in acciones if a["tool"] == "run_tests")
    ult3 = sum(1 for a in acciones[-3:] if a["tool"] == "write_file")
    ult5 = sum(1 for a in acciones[-5:] if a["tool"] == "write_file")
    racha = mejor = 1 if acciones else 0
    for prev, cur in itertools.pairwise(acciones):
        racha = racha + 1 if prev == cur else 1
        mejor = max(mejor, racha)
    return {"turns": turns, "tool_calls": len(acciones), "lecturas": lecturas,
            "escrituras": escrituras, "run_tests": run_tests,
            "escrituras_ult3": ult3, "escrituras_ult5": ult5,
            "racha_max_identica": mejor,
            "clasificacion": clasificar(ult3, ult5, mejor)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parte A reproducible (rachas)")
    ap.add_argument("db", type=Path, help="traces oficial sqlite")
    ap.add_argument("--result-oficial", type=Path,
                    default=REPO / "evals" / "results" / "result_sens_sd_pilot.json")
    ap.add_argument("--out", type=Path,
                    default=REPO / "evals" / "results" / "result_sens_sd_trazas_repro.json")
    args = ap.parse_args(argv)

    of = json.loads(args.result_oficial.read_text(encoding="utf-8"))
    celdas_out = {}
    for key, acciones in sorted(_acciones_tool(args.db).items()):
        cell = of["celdas"].get(key, {})
        info = analizar_celda(acciones, int(cell.get("turns") or len(acciones)))
        info["score_16"] = cell.get("score")
        celdas_out[key] = info
    out = {"fecha": time.strftime("%Y-%m-%dT%H:%M:%S"), "regla": REGLA,
           "celdas": celdas_out}
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    n_at = sum(1 for c in celdas_out.values() if c["clasificacion"] == "ATASCADO")
    print(f"analizador: {args.out.relative_to(REPO)} "
          f"({len(celdas_out)} celdas, {n_at} ATASCADO)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
