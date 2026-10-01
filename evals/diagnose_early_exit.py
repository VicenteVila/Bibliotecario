"""Por que el agente responde en prosa antes de buscar evidencia.

En las 4 runs, las respuestas que salen por la via rapida (el modelo contesta en
prosa en algun turno y el loop hace break sin llamar a _final_answer) puntuan
2.273 de media frente a 4.551 de las que llegan al cierre forzado. Este script
captura que ve y que responde el modelo en cada turno para comparar una
respuesta rapida con una que si cierra.

No cambia nada: solo envuelve generate() y guarda la traza.

Uso: python evals/diagnose_early_exit.py --ids reas-b2,reas-b6,tce-b4
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from bibliotecario.agent import loop as LOOP
from bibliotecario.core import llm as LLM

os.environ.setdefault("LLM_PROVIDERS", "nvidia")
LOOP.STRICT_FALLBACK = True

OUT = EVALS / "result_early_exit.json"
DEFAULT_IDS = ["reas-b2", "reas-b6", "tce-b4"]


def traza(question: str, turns: int) -> dict:
    """Ejecuta el loop real guardando prompt y salida cruda de cada turno."""
    calls: list[dict] = []
    real = LOOP.generate

    def espia(prompt, max_tokens=512, retries=None):
        out = real(prompt, max_tokens, retries)
        calls.append({"n": len(calls), "prompt": prompt, "out": out})
        return out

    LOOP.generate = espia
    try:
        res = LOOP.run(question, max_turns=turns, isolated=True)
    finally:
        LOOP.generate = real
    return {"question": question, "turns": res["turns"], "answer": res["answer"],
            "n_calls": len(calls), "calls": calls}


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default=",".join(DEFAULT_IDS))
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    provs = LLM._providers()
    if [p[0] for p in provs] != ["nvidia"]:
        raise SystemExit(f"aborta: proveedor esperado nvidia, obtuve {provs}")
    print(f"proveedor pineado: {provs[0]}")

    golden = {json.loads(l)["id"]: json.loads(l)
              for l in (EVALS / "golden_blind_qa.jsonl").read_text().splitlines() if l.strip()}

    obs = []
    for qid in args.ids.split(","):
        qid = qid.strip()
        if not qid:
            continue
        q = golden[qid]
        t = traza(q["question"], args.turns)
        t["id"] = qid
        # Solo se guarda el prompt del ultimo turno: el del turno 0 es siempre
        # identico y solo infla el fichero.
        for c in t["calls"]:
            c["prompt"] = c["prompt"][-1400:]
        obs.append(t)
        print(f"\n{'=' * 74}\n{qid}: {t['turns']} turnos, {t['n_calls']} llamadas al modelo")
        for c in t["calls"]:
            primera = (c["out"] or "").strip().replace("\n", " ")[:230]
            print(f"  turno {c['n']}: {primera}")

    Path(args.out).write_text(json.dumps({"observaciones": obs}, indent=1, ensure_ascii=False))
    print(f"\n-> {args.out}")
    return {"observaciones": obs}


if __name__ == "__main__":
    main()