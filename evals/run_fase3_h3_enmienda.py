"""Hito 3, Fase 3 — H3E: reactividad de los PFs (enmienda 1, parte B).

Enmienda 1 de H3 (2026-10-16, decisión del dueño), declarada en
`evals/HITO3_PLAN.md` ANTES de correr esto:

- **B · reactividad:** en runs donde el bucle entra en error real y el modelo
  reintenta con otra llamada de tool, ≥1 PF fire en el 100% de esas runs.
- Control: 5 runs limpias esperando **0 fires** (los PFs no son decorativos;
  la parte A de la enmienda ya lo midió en la ruta real, 10/10).

Medición **gratuita** (0 tokens): LLM guionizado, misma técnica que la
dimensión D y los tests del loop. Harness, PFs y estado son los reales del
producto; solo se controla la entrada del modelo. `apply_pfs` se invoca al
empezar una llamada válida, con el estado del recorrido anterior: un error
real en el turno N dispara los PFs en el turno N+1 si ese turno vuelve a ser
una llamada de tool.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_fase3_h3_enmienda.json"
ARM = "H3E"

_TOOL_OK = '```json\n{"tool": "get_status", "args": {}}\n```'
_TOOL_MALA = '```json\n{"tool": "no_existe", "args": {}}\n```'
_CIERRE = "Respuesta final [1:0]."

# 5 limpias: herramienta válida, prosa, cierre (la prosa pasa por el cierre
# forzado, que pide otra generación). 5 con error real y reintento válido.
SCRIPTS_LIMPIAS = [[_TOOL_OK, "Todo en orden.", _CIERRE]] * 5
SCRIPTS_ERROR = [[_TOOL_MALA, _TOOL_OK, _CIERRE]] * 5


def _run_scripted(script: list[str], question: str) -> dict:
    from bibliotecario.agent import loop as LOOP
    from bibliotecario.harness import runtime as RT
    import bibliotecario.harness.pfs as PFS

    RT.reset_harness()
    PFS._registry = None
    cola = list(script)
    original = LOOP.generate
    LOOP.generate = lambda *a, **k: cola.pop(0) if cola else "Fin."
    try:
        return LOOP.run(question, max_turns=4, isolated=True)
    finally:
        LOOP.generate = original


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    print("=" * 74)
    print("H3E — reactividad de los PFs (enmienda 1, parte B) · 0 tokens")
    print("=" * 74)

    filas: list[dict] = []
    for i, script in enumerate(SCRIPTS_LIMPIAS):
        r = _run_scripted(script, f"pregunta limpia {i}")
        fires = r.get("pf_fires") or []
        filas.append({"arm": ARM, "tipo": "limpia", "run": i, "ok": True,
                      "turns": r["turns"], "pf_n": len(fires),
                      "pf_fires": fires,
                      "esperado": 0, "cumple": len(fires) == 0})
        print(f"  limpia  [{i}] turns={r['turns']} fires={len(fires)}  "
              f"{'ok' if not fires else 'FALLO: fires en run limpia'}")

    for i, script in enumerate(SCRIPTS_ERROR):
        r = _run_scripted(script, f"pregunta con error {i}")
        fires = r.get("pf_fires") or []
        nombres = [f["pf"] for f in fires]
        filas.append({"arm": ARM, "tipo": "error_reintento", "run": i, "ok": True,
                      "turns": r["turns"], "pf_n": len(fires),
                      "pf_fires": fires, "pf_nombres": nombres,
                      "esperado": ">=1", "cumple": len(fires) >= 1})
        print(f"  error   [{i}] turns={r['turns']} fires={len(fires)}  {nombres}")

    limpias = [f for f in filas if f["tipo"] == "limpia"]
    errores = [f for f in filas if f["tipo"] == "error_reintento"]
    limpias_ok = sum(1 for f in limpias if f["cumple"])
    errores_ok = sum(1 for f in errores if f["cumple"])
    print("-" * 74)
    print(f"  limpias con 0 fires      : {limpias_ok}/{len(limpias)}")
    print(f"  error+reintento con >=1  : {errores_ok}/{len(errores)}")
    cerrada = limpias_ok == len(limpias) and errores_ok == len(errores)
    print("-" * 74)
    print(f"  H3E (parte B): {'CUMPLE' if cerrada else 'NO CUMPLE'}")

    Path(args.out).write_text(
        json.dumps({"criterio": "H3 enmienda 1, parte B (HITO3_PLAN § Fase 3)",
                    "umbral": ">=1 fire en 100% de runs error+reintento; 0 fires en limpias",
                    "n_limpia": len(limpias), "n_error": len(errores),
                    "limpias_ok": limpias_ok, "errores_ok": errores_ok,
                    "h3e": cerrada, "filas": filas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n  -> {args.out}")
    return 0 if cerrada else 1


if __name__ == "__main__":
    raise SystemExit(main())
