"""Sonda offline del cierre: mide el techo de las dos direcciones que quedan.

Por que offline y no una eval completa: el contexto del cierre se reconstruye
determinista con `_deep_evidence`, asi que se puede repetir el cierre exacto sin
pagar retrieval ni bucles. Y la metrica no necesita juez: cobertura de los
`keywords` gold en la respuesta, que es lo que el juez acaba premiando.

Condiciones:
  base  prompt de produccion, T=0.2 (el default real del backend), 1 muestra.
        Reproduce lo que ya mide r5/r6.
  hot   mismo prompt a T=0.8, N muestras. Es el techo de la direccion 1
        (diversidad de muestreo): si a 0.8 el modelo sigue omitiendo lo mismo,
        el fallo es un modo estable y muestrear no lo arregla.
  enum  prompt con el paso de desglose previo (direccion 2), T=0.2, 2 muestras.

Uso:  python evals/probe_close_diversity.py --n 4
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bibliotecario.agent import loop as LOOP
from bibliotecario.core.llm import generate as llm_generate
from bibliotecario.ingest import citations_format as CITE_FMT

RESIDUAL = ["pg-b5", "tce-b7", "wiki-b1", "wiki-b6", "wiki-b2"]
CONTROLS = ["pearl-b2", "pg-b3", "tce-b5", "reas-b6", "wiki-b5"]


def cobertura(answer: str, keywords: list[str]) -> tuple[int, list[str]]:
    a = (answer or "").lower()
    faltan = [k for k in keywords if k.lower() not in a]
    return len(keywords) - len(faltan), faltan


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4, help="muestras por condicion caliente")
    args = ap.parse_args()

    LOOP.STRICT_FALLBACK = True
    with open("evals/golden_blind_qa.jsonl", encoding="utf-8") as fh:
        rows = [json.loads(l) for l in fh if l.strip()]
    G = {r["id"]: r for r in rows}
    ids = [i for i in RESIDUAL + CONTROLS if i in G]

    ctx_cache: dict[str, str] = {}
    out: dict[str, dict] = {}

    for qid in ids:
        g = G[qid]
        kws = g.get("keywords") or []
        deep = ctx_cache.setdefault(qid, LOOP._deep_evidence(g["question"]))
        ctx = deep
        base_prompt = LOOP._close_prompt(g["question"], ctx, "", "", 0)
        enum_prompt = LOOP._close_prompt(g["question"], ctx, "", "", 0, enumerate_slots=True)
        res: dict[str, list] = {"base": [], "hot": [], "enum": []}

        def ask(prompt: str, temp: float) -> str:
            raw = llm_generate(prompt, 900, 2, strict_fallback=True,
                               temperature=temp).strip()
            if LOOP._toolish(raw):
                return ""
            return CITE_FMT.normalize_citations(LOOP._fix_truncation(raw))

        res["base"].append(ask(base_prompt, 0.2))
        for _ in range(args.n):
            res["hot"].append(ask(base_prompt, 0.8))
        for _ in range(2):
            res["enum"].append(ask(enum_prompt, 0.2))

        out[qid] = {"keywords": kws, "grupo": "residuo" if qid in RESIDUAL else "control",
                    "answers": {k: v for k, v in res.items()}}
        print(f"\n=== {qid} ({out[qid]['grupo']}) keywords={kws}", flush=True)
        for cond in ("base", "hot", "enum"):
            covs = [cobertura(a, kws)[0] for a in res[cond]]
            faltan = cobertura(res[cond][0], kws)[1]
            print(f"  {cond:5} cobertura {covs} de {len(kws)}   faltan(base)={faltan}",
                  flush=True)

    Path("evals/result_close_diversity.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 68)
    print(f"{'condicion':10} {'residuo':>18} {'controles':>18}")
    for cond in ("base", "hot", "enum"):
        fila = {}
        for grupo in ("residuo", "control"):
            vals = [cobertura(a, G[q]["keywords"])[0] / max(1, len(G[q]["keywords"]))
                    for q, d in out.items() if d["grupo"] == grupo
                    for a in d["answers"][cond]]
            fila[grupo] = st.mean(vals)
        print(f"{cond:10} {fila['residuo']:>17.1%} {fila['control']:>17.1%}")
    print("guardado evals/result_close_diversity.json")


if __name__ == "__main__":
    main()
