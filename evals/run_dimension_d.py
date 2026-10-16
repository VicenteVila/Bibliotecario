"""Mide la dimensión D (§2.D) con el criterio fijado en §6 dec. 13.

Tres comprobaciones, las tres gratuitas (0 tokens): compilar, leer el fuente
y ejecutar `run()`.

    D1  compila y run() no lanza excepción          -> 100% de los agentes
    D2  el literal "todo" no está escrito en el fuente -> 0 agentes
    D3  el trace devuelve >= 1 paso en estado "done"    -> >= 1 paso
        ("done" exige mejor_score >= 0.30 — 2ª enmienda de dec. 13: deep_sweep
         devuelve docs para cualquier cadena, asi que "hay docs" no distingue)

La fila D cierra solo si las tres pasan.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import py_compile
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TECNICAS = ["PEARL", "Procedural Graphs", "ReASearch", "Task-CoEvolve", "WikiSkill"]
GOAL = "validar mi agente antes de cada release"


def _cargar(path: Path):
    spec = importlib.util.spec_from_file_location(f"agente_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _instancia(technique: str) -> dict:
    """Llama a la ruta real `instantiate_agent_template`, con el LLM estancado.

    Hito 3, Fase 1: `instantiate` ya no entra por `build_blueprint` directo,
    sino por `build_blueprint_p4` → `loop.run_blueprint` (4 turnos de loop +
    blueprint). Para que D siga costando 0 tokens se estanca la **entrada**
    del loop; dentro, `build_blueprint` se ejecuta de verdad con `generate`
    estancado.

    `build_blueprint` llama a `generate()` para escribir el **blueprint**, que va
    a `BLUEPRINT.md`. El `agent_template.py` que D mide se construye solo con
    `bp["procedures"]`, `technique` y `goal` — todos salidos de
    `P.list_procedures()` **antes** de esa llamada. El archivo que se mide es
    por tanto **byte-idéntico con o sin LLM**, así que se estanca para no gastar
    lo que no aporta nada al resultado.
    """
    from bibliotecario.agent import loop as LOOP
    from bibliotecario.agent import tools as T
    from bibliotecario.knowledge import pearl

    # `generate` escribe el blueprint (va a BLUEPRINT.md) y
    # `PEARL.retrieve_evidence` solo rellena `chain`, el texto del prompt.
    # Ninguno de los dos toca `bp["procedures"]`, de donde sale el archivo.
    original_g = T.generate
    original_r = pearl.retrieve_evidence
    original_rb = LOOP.run_blueprint
    T.generate = lambda *a, **k: "(sin LLM: D no mide el texto del blueprint)"
    pearl.retrieve_evidence = lambda *a, **k: []
    LOOP.run_blueprint = lambda t, g, **k: T.build_blueprint(t, g)
    try:
        return T.instantiate_agent_template(technique, GOAL)
    finally:
        T.generate = original_g
        pearl.retrieve_evidence = original_r
        LOOP.run_blueprint = original_rb


def medir(technique: str) -> dict:
    res = _instancia(technique)
    src = Path(res["dir"]) / "agent_template.py"

    r: dict = {"technique": technique, "archivo": str(src)}

    # D1 — compila y ejecuta sin excepcion, con dos contextos distintos.
    try:
        py_compile.compile(str(src), doraise=True)
        mod = _cargar(src)
        t1 = mod.run({"objetivo": GOAL})
        t2 = mod.run({"objetivo": "otro objetivo distinto", "n": 42})
        r["d1"] = True
        r["d1_error"] = ""
    except Exception as e:
        r["d1"] = False
        r["d1_error"] = f"{type(e).__name__}: {e}"
        r["d2"] = False
        r["d3"] = 0
        return r

    # D2 — el estado NO esta escrito en el fuente.
    texto = src.read_text(encoding="utf-8")
    # solo el cuerpo de run(), no el docstring ni el listado de pasos
    cuerpo = texto.split("def run(", 1)[-1] if "def run(" in texto else texto
    r["d2"] = '"todo"' not in cuerpo and "'todo'" not in cuerpo
    r["d2_literal"] = cuerpo.count('"todo"') + cuerpo.count("'todo'")

    # D3 — al menos un paso sale de "todo".
    trace = (t1 or {}).get("trace") or []
    hechos = [s for s in trace if s.get("status") == "done"]
    r["d3"] = len(hechos)
    r["pasos"] = len(trace)
    # el agente ignora su contexto si da exactamente lo mismo siempre
    r["responde_al_contexto"] = t1 != t2
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evals/result_dimension_d.json")
    args = ap.parse_args()

    filas = [medir(t) for t in TECNICAS]

    d1 = sum(1 for f in filas if f["d1"])
    d2 = sum(1 for f in filas if f["d2"])
    d3 = sum(1 for f in filas if f["d3"] >= 1)
    n = len(filas)

    print("=" * 74)
    print(f"DIMENSION D — dec. 13  (n={n} agentes, {GOAL!r})")
    print("=" * 74)
    for f in filas:
        print(f"  {f['technique']:20} D1={'si' if f['d1'] else 'NO':2}  "
              f"D2={'si' if f['d2'] else 'NO':2}  "
              f"D3={f['d3']}/{f.get('pasos', '?')} pasos hechos  "
              f"ctx={'si' if f.get('responde_al_contexto') else 'NO'}"
              + (f"  [{f['d1_error']}]" if not f["d1"] else ""))
    print("-" * 74)
    print(f"  D1 ejecuta sin excepcion : {d1}/{n}   umbral 100%  -> "
          f"{'CUMPLE' if d1 == n else 'NO CUMPLE'}")
    print(f"  D2 sin literal 'todo'    : {d2}/{n}   umbral 0 con literal -> "
          f"{'CUMPLE' if d2 == n else 'NO CUMPLE'}")
    print(f"  D3 >=1 paso 'done'       : {d3}/{n}   umbral >=1  -> "
          f"{'CUMPLE' if d3 == n else 'NO CUMPLE'}")
    cerrada = d1 == n and d2 == n and d3 == n
    print("-" * 74)
    print(f"  FILA D: {'CIERRA' if cerrada else 'NO CIERRA'} "
          f"(las tres tienen que cumplir)")

    Path(args.out).write_text(
        json.dumps({"criterio": "dec.13", "goal": GOAL, "n": n,
                    "d1": d1, "d2": d2, "d3": d3, "cierra": cerrada,
                    "filas": filas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n  -> {args.out}")


if __name__ == "__main__":
    main()
