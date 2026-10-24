"""HITO21 Fase A: replay offline del parser tolerante sobre las trazas b2.

No llama a ningún LLM (0 tokens). Genera la evidencia
`evals/results/result_hito21_fase_a.json` con los gates G0-A (idempotencia)
y G0-B (recuperación de los `write_file` inválidos almacenados).
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from evals.sd_pilot.harness import parse_actions
from evals.sd_pilot.io_atomico import escribir_texto_atomico
from evals.sd_pilot.parse_tolerante import parse_actions_tolerante

DB = REPO / "evals" / "sd_pilot" / "traces_corrb.sqlite"
OUT = REPO / "evals" / "results" / "result_hito21_fase_a.json"
RESIDUALES = ("A2_checkout-rounding", "A3_checkout-rounding",
              "A4_dsl-parser", "A5_plugin-registry")
RUTA_ESPERADA = {"A4_dsl-parser": "mini_dsl/tokens.py",
                 "A2_checkout-rounding": "checkout/redondeo.py"}


def _decode(value: str) -> str:
    try:
        decoded = json.loads(value)
    except (TypeError, ValueError):
        return value or ""
    return decoded if isinstance(decoded, str) else str(decoded)


def _run_ids(conn: sqlite3.Connection) -> dict[str, str]:
    out = {}
    for row in conn.execute("SELECT trace_id, metadata FROM spans WHERE agent='sens_pilot'"):
        meta = json.loads(row["metadata"] or "{}")
        if meta.get("run_id"):
            out[meta["run_id"]] = row["trace_id"]
    return out


def main() -> int:
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    runs = _run_ids(conn)
    total = base_nonempty = diferencias = recuperadas = 0
    por_celda: dict[str, dict] = {}
    for run, trace_id in runs.items():
        stats = {"turnos": 0, "base_vacia": 0, "recuperadas": 0,
                 "rutas": [], "diffs": 0}
        for row in conn.execute(
                "SELECT output FROM spans WHERE trace_id=? AND agent='turn' "
                "ORDER BY started_at", (trace_id,)):
            raw = _decode(row["output"])
            base = parse_actions(raw)
            tolerante = parse_actions_tolerante(raw)
            total += 1
            stats["turnos"] += 1
            if base:
                base_nonempty += 1
                if tolerante != base:
                    diferencias += 1
                    stats["diffs"] += 1
            else:
                stats["base_vacia"] += 1
                if tolerante:
                    recuperadas += 1
                    stats["recuperadas"] += 1
                    stats["rutas"].append(
                        tolerante[0].get("args", {}).get("path"))
        if run in RESIDUALES:
            stats["ruta_esperada"] = RUTA_ESPERADA.get(run)
            stats["rutas_ok"] = bool(stats["rutas"]) and all(
                r == RUTA_ESPERADA.get(run) for r in stats["rutas"])
            por_celda[run] = stats

    g0a = diferencias == 0
    a4 = por_celda.get("A4_dsl-parser", {})
    a2 = por_celda.get("A2_checkout-rounding", {})
    g0b = (a4.get("recuperadas") == 15 and a4.get("rutas_ok")
           and a2.get("recuperadas", 0) >= 1 and a2.get("rutas_ok"))
    result = {
        "hito": 21, "fase": "A_offline", "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "tokens": 0, "trazas": str(DB.relative_to(REPO)),
        "turnos": total, "turnos_con_base": base_nonempty,
        "recuperadas": recuperadas,
        "g0a_idempotencia": {"diferencias": diferencias, "pasa": g0a},
        "g0b_recuperacion": {"pasa": g0b, "celdas": por_celda},
        "pasa": bool(g0a and g0b),
    }
    escribir_texto_atomico(OUT, json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "g0b_recuperacion"},
                     indent=1, ensure_ascii=False))
    print(json.dumps(por_celda, indent=1, ensure_ascii=False))
    return 0 if result["pasa"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
