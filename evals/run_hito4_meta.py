"""Hito 4 — medición oficial de la meta-evolución (H5-H8 + C1).

Umbrales declarados en `evals/HITO4_PLAN.md` ANTES de existir este script
(commit 05852c5): H5 la evolución dispara (auto_evolved y harness_edits >= 1),
H6 lo evolucionado se usa en proceso (auto_pf en pf_fires de R3 >= 1), H7 los
contadores muertos se llenan (skills y memory_items >= 1), H8 la evolución
sobrevive a reinicio de registro+harness (auto_pf rehidratado en R4 >= 1) y
C1 controles (run limpia con 0 fires de auto_pf; la suite se anota aparte).

Corre las mismas 5 runs guionizadas que tests/test_meta_evolution.py, pero
como medición: DB hermética en directorio temporal (no toca ni hereda
data/bibliotecario.db), 0 tokens, harness/PFs/estado/base reales.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "result_hito4_meta.json"
ARM = "HITO4"

_TOOL_OK = '```json\n{"tool": "get_status", "args": {}}\n```'
_TOOL_MALA = '```json\n{"tool": "no_existe", "args": {}}\n```'
_CIERRE = "Respuesta final [1:0]."
SCRIPT_ERROR = [_TOOL_MALA, _TOOL_OK, _CIERRE]
SCRIPT_LIMPIA = [_TOOL_OK, "Todo en orden.", _CIERRE]
_MENSAJE_ERROR = ('llamada inválida: emite EXACTAMENTE '
                  '{"tool": nombre, "args": {...}} con un tool del catálogo (no sueltes args sin "tool")')


def _run(script: list[str], question: str) -> dict:
    from bibliotecario.agent import loop as LOOP

    cola = list(script)
    original = LOOP.generate
    LOOP.generate = lambda *a, **k: cola.pop(0) if cola else "Fin."
    try:
        return LOOP.run(question, max_turns=4, isolated=True)
    finally:
        LOOP.generate = original


def _counter(db: Path) -> dict:
    from bibliotecario.core import storage

    with storage.get_conn(db) as conn:
        edits = [dict(r) for r in conn.execute(
            "SELECT signature, occurrences, evolved, pf_name FROM harness_edits ORDER BY id")]
        skills = conn.execute("SELECT COUNT(*) c FROM skills").fetchone()["c"]
        memory = conn.execute("SELECT COUNT(*) c FROM memory_items").fetchone()["c"]
    return {"harness_edits": edits, "skills": skills, "memory_items": memory}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--nota", default="", help="anotación externa p.ej. resultado de pytest")
    args = ap.parse_args()

    from bibliotecario.core import storage
    from bibliotecario.harness import pfs as PFS
    from bibliotecario.harness import runtime as RT
    from bibliotecario.harness.edits import normalize_signature

    firma = normalize_signature(_MENSAJE_ERROR)

    tmp = Path(tempfile.mkdtemp(prefix="hito4_"))
    db = tmp / "meta.db"
    storage.db_path = lambda: db  # DB hermética: la corrida no contamina producción
    storage.init_db(db)
    PFS._registry = None
    RT.reset_harness()

    print("=" * 74)
    print("HITO4 — meta-evolución · R1-R5 guionizadas · 0 tokens")
    print(f"firma: {firma[:70]}")
    print("=" * 74)

    filas: list[dict] = []

    def marca(run_id: str, r: dict) -> dict:
        nombres = [f["pf"] for f in r.get("pf_fires") or []]
        auto = [n for n in nombres if n.startswith("auto_pf_")]
        fila = {"arm": ARM, "run": run_id, "turns": r["turns"],
                "pf_nombres": nombres, "auto_pf": auto,
                "meta_evolved": r.get("meta_evolved") or []}
        filas.append(fila)
        print(f"  {run_id}: turns={r['turns']} fires={nombres} "
              f"evoluciones={len(fila['meta_evolved'])}")
        return fila

    # R1: primera aparición — cuenta, no evoluciona
    f1 = marca("R1", _run(SCRIPT_ERROR, "pregunta uno"))
    # R2: segunda — evoluciona (H5) y llena contadores (H7)
    f2 = marca("R2", _run(SCRIPT_ERROR, "pregunta dos"))
    # R3: mismo proceso — lo evolucionado se usa (H6)
    f3 = marca("R3", _run(SCRIPT_ERROR, "pregunta tres"))
    # R4: reinicio de registro+harness — rehidratación (H8)
    PFS._registry = None
    RT.reset_harness()
    f4 = marca("R4", _run(SCRIPT_ERROR, "pregunta cuatro"))
    # R5: limpia con registro rehidratado — 0 auto fires (C1)
    PFS._registry = None
    RT.reset_harness()
    f5 = marca("R5", _run(SCRIPT_LIMPIA, "pregunta limpia"))

    contadores = _counter(db)
    auto_evolved = PFS.get_pf_registry().stats()["auto_evolved"]
    edits_evolucionadas = [e for e in contadores["harness_edits"] if e["evolved"]]

    u5 = auto_evolved >= 1 and len(edits_evolucionadas) >= 1
    u6 = len(f3["auto_pf"]) >= 1
    u7 = contadores["skills"] >= 1 and contadores["memory_items"] >= 1
    u8 = len(f4["auto_pf"]) >= 1
    c1 = len(f5["auto_pf"]) == 0
    cerrado = u5 and u6 and u7 and u8 and c1

    print("-" * 74)
    print(f"  H5  evoluciona (auto_evolved={auto_evolved}, "
          f"harness_edits evolved={len(edits_evolucionadas)}) : {'CUMPLE' if u5 else 'NO CUMPLE'}")
    print(f"  H6  auto_pf usado en R3 ({f3['auto_pf']})             : {'CUMPLE' if u6 else 'NO CUMPLE'}")
    print(f"  H7  skills={contadores['skills']} memory={contadores['memory_items']}"
          f"                                 : {'CUMPLE' if u7 else 'NO CUMPLE'}")
    print(f"  H8  auto_pf rehidratado en R4 ({f4['auto_pf']})        : {'CUMPLE' if u8 else 'NO CUMPLE'}")
    print(f"  C1  run limpia R5 con 0 auto_pf ({len(f5['auto_pf'])})             : {'CUMPLE' if c1 else 'NO CUMPLE'}")
    print(f"  HITO4: {'CUMPLE' if cerrado else 'NO CUMPLE'}")
    print("-" * 74)

    resultado = {"criterio": "Hito 4 (HITO4_PLAN §2: H5-H8 + C1)",
                 "umbrales": {"H5": "auto_evolved>=1 y harness_edits evolved>=1",
                              "H6": "auto_pf en pf_fires de R3 >= 1",
                              "H7": "skills>=1 y memory_items>=1",
                              "H8": "auto_pf en pf_fires de R4 >= 1",
                              "C1": "run limpia R5 con 0 auto_pf"},
                 "firma": firma, "db_hermetica": str(db),
                 "h5": u5, "h6": u6, "h7": u7, "h8": u8, "c1_run": c1,
                 "hito4": cerrado,
                 "auto_evolved": auto_evolved,
                 "contadores": contadores,
                 "filas": filas, "nota": args.nota}
    Path(args.out).write_text(json.dumps(resultado, ensure_ascii=False, indent=2),
                              encoding="utf-8")
    print(f"\n  -> {args.out}")
    return 0 if cerrado else 1


if __name__ == "__main__":
    raise SystemExit(main())
