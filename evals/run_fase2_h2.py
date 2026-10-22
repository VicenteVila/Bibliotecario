"""Hito 3, Fase 2 — H2: el `run()` generado ejecuta la técnica, no solo retrieval.

Declaración previa en `evals/HITO3_PLAN.md` (§5 H2, escrita ANTES de medir):

- **criterio:** el `run()` generado hace algo que **no** sea llamar `deep_sweep`
  una vez por paso.
- **umbral intacto:** ≥ 3 pasos por arnés que usen herramientas del loop o
  validen contra el blueprint; y ≥ 1 paso que no dependa de `deep_sweep`.
- **medición gratuita** (0 tokens): los pasos de la plantilla son tools
  locales del loop; `run()` no contiene LLM.

`--regen` reconstruye las 5 plantillas **sin LLM** con
`instantiate_agent_template(technique, GOAL, bp=...)`:

- `procedures` del grafo (`P.list_procedures`, determinista, misma fuente que
  `build_blueprint`);
- texto del blueprint de la Fase 1, tal cual se juzgó: el reparado de
  `result_fase1_h1r.json` si existe, si no el original de
  `result_fase1_h1.json` (Task-CoEvolve no se reparó: pasó R4 y R5 a la
  primera).

Nota (comportamiento preexistente de D, declarado aquí): medir D re-genera
los arneses con `generate` estancado, y eso **reescribe `BLUEPRINT.md` con el
texto de rescate**. Los textos juzgados viven en los JSON de Fase 1; el regen
de este script los restaura en disco desde ahí.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_dimension_d import GOAL, TECNICAS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "results" / "result_fase2_h2.json"
ARM = "H2"
HERRAMIENTAS_LOOP = ("deep_sweep", "search_papers", "retrieve_evidence", "get_subgraph")


def _blueprint_juzgado(technique: str) -> str:
    """Texto del blueprint de Fase 1: el reparado si existe, si no el original."""
    reparados = json.loads((ROOT / "evals" / "results" / "result_fase1_h1r.json").read_text(encoding="utf-8"))
    for fila in reparados:
        if fila.get("technique") == technique and fila.get("ok"):
            return fila["blueprint"]
    originales = json.loads((ROOT / "evals" / "results" / "result_fase1_h1.json").read_text(encoding="utf-8"))
    for fila in originales:
        if fila.get("technique") == technique and fila.get("ok"):
            return fila["blueprint"]
    raise RuntimeError(f"sin blueprint juzgado para {technique}")


def regenerar() -> None:
    from bibliotecario.agent.tools import instantiate_agent_template
    from bibliotecario.knowledge import procedural as P

    for tech in TECNICAS:
        procs = [p.label for p in P.list_procedures(technique=tech)[:20]]
        bp = {"procedures": procs, "blueprint": _blueprint_juzgado(tech),
              "violaciones": [], "verificado": True}
        res = instantiate_agent_template(tech, GOAL, bp=bp)
        print(f"  [regen] {tech:20} -> {res['dir']}  ({len(procs)} procedimientos)")


def _cargar(path: Path):
    spec = importlib.util.spec_from_file_location(f"agente_h2_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def medir(technique: str) -> dict:
    from bibliotecario.agent.tools import data_dir

    slug = "".join(c if c.isalnum() else "-" for c in technique.lower())[:40].strip("-")
    src = data_dir() / "agents" / slug / "agent_template.py"
    mod = _cargar(src)
    out = mod.run({"objetivo": GOAL})
    trace = out.get("trace") or []

    herramienta = [s for s in trace if s.get("tool") in HERRAMIENTAS_LOOP]
    validacion = [s for s in trace if s.get("step") == "validacion_blueprint"]
    con_acento = herramienta + validacion
    sin_deep = [s for s in con_acento if s.get("tool") != "deep_sweep"]
    errores = [s for s in trace if s.get("status") == "error"]

    cumple = len(con_acento) >= 3 and len(sin_deep) >= 1
    return {"arm": ARM, "technique": technique, "ok": True,
            "archivo": str(src), "pasos_trace": len(trace),
            "pasos_herramienta_o_validacion": len(con_acento),
            "pasos_sin_deep_sweep": len(sin_deep),
            "errores": len(errores),
            "tools": [s.get("tool") for s in herramienta],
            "validacion": validacion[0] if validacion else None,
            "umbral": ">=3 herramienta/validacion y >=1 sin deep_sweep",
            "cumple": cumple}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--regen", action="store_true",
                    help="regenera las 5 plantillas desde el bp de Fase 1, sin LLM")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    if args.regen:
        print("Regenerando plantillas (sin LLM)...")
        regenerar()

    print()
    print("=" * 74)
    print(f"H2 — el arnes ejecuta la tecnica (goal {GOAL!r}, n={len(TECNICAS)})")
    print("=" * 74)
    filas: list[dict] = []
    for tech in TECNICAS:
        fila = medir(tech)
        filas.append(fila)
        print(f"  {tech:20} pasos herramienta/validacion="
              f"{fila['pasos_herramienta_o_validacion']}  "
              f"sin deep_sweep={fila['pasos_sin_deep_sweep']}  "
              f"errores={fila['errores']}  -> "
              f"{'CUMPLE' if fila['cumple'] else 'NO CUMPLE'}")
        print(f"  {'':20} tools={fila['tools']}")

    n_ok = sum(1 for f in filas if f["cumple"])
    print("-" * 74)
    print(f"  >=3 pasos herramienta/validacion : {n_ok}/{len(filas)} arneses  "
          f"(umbral >=3 por arnes)")
    print(f"  >=1 paso sin deep_sweep          : "
          f"{sum(1 for f in filas if f['pasos_sin_deep_sweep'] >= 1)}/{len(filas)}")
    cerrada = n_ok == len(filas)
    print("-" * 74)
    print(f"  H2: {'CUMPLE' if cerrada else 'NO CUMPLE'} "
          f"(todos los arneses tienen que cumplir)")

    Path(args.out).write_text(
        json.dumps({"criterio": "H2 (HITO3_PLAN §5)", "goal": GOAL,
                    "umbral": ">=3 pasos herramienta/validacion y >=1 sin deep_sweep",
                    "n": len(filas), "cumple_n": n_ok, "h2": cerrada,
                    "filas": filas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n  -> {args.out}")
    return 0 if cerrada else 1


if __name__ == "__main__":
    raise SystemExit(main())
