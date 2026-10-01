"""¿El agente falla por el pajar o por no saber extraer?

Diagnostico previo (evals/diagnose_visibility.py, coste 0): el chunk gold SI
llega a las 3 preguntas que fallan de forma consistente (wiki-b1=2, wiki-b7=2,
tce-b7=4 en los tres runs). Asi que no es retrieval ni tuberia.

Quedan doshipotesis:
  A) volumen: recibe ~50k chars y no localiza la aguja
  B) extraccion: no extrae aunque la tenga delante

Se separan con el loop REAL, cambiando solo el volumen del barrido. Lo demas
(trajectoria de 4 turnos, retries, filtro _toolish, parche de cita, juez) queda
identico a produccion, asi que la comparacion contra las runs validadas es
directa.

La version anterior de esta sonda reconstruia el prompt de cierre a mano y fue
invalida por dos motivos, ambos instructive:
  - generate() hace round-robin de proveedores: sin LLM_PROVIDERS=nvidia una 504
    de NVIDIA lleva la respuesta a Gemini en silencio (notas 5,1,1 mezclando dos
    modelos). Por eso ahora se pinea y se graba el modelo de cada llamada.
  - el prompt real de cierre es _final_answer (filtra _toolish, parchea
    truncado, fuerza [doc:?] y exige 150 palabras). Mi reconstrucción puntuaba el
    volcado JSON de una llamada a tool como si fuera la respuesta: por eso todo
    salia 1. El prompt se delega, no se copia.

Uso: python evals/probe_extraction.py --mode loop --reps 1
"""
from __future__ import annotations

import argparse
import json
import os
import statistics as st
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))


# Pinear ANTES de tocar la red (ver docstring).
os.environ["LLM_PROVIDERS"] = os.environ.get("PROBE_PROVIDER", "nvidia")

from bibliotecario.agent import loop as LOOP
from bibliotecario.core import llm as LLM
from bibliotecario.core import storage
from evals.judge import judge

LOOP.STRICT_FALLBACK = True

OUT = EVALS / "result_probe_extraction.json"
DEFAULT_Q = ["wiki-b1", "wiki-b7", "tce-b7"]
# Scores del brazo ancho, medidos en las 3 runs ciegas validadas.
WIDE = {"wiki-b1": [2, 2, 2], "wiki-b7": [2, 2, 2], "tce-b7": [4, 4, 4]}


def chunk_text(doc_id: int, idx: int) -> str:
    with storage.get_conn() as c:
        r = c.execute("SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=?",
                      (doc_id, idx)).fetchone()
    return r["text"] if r else ""


def narrow(q: dict) -> str:
    """El pajar minimo posible: solo los chunks gold, texto integro."""
    parts = []
    for c in q["cite_chunks"]:
        d, i = c.split(":")
        parts.append(f"[{d}:{i}]\n{chunk_text(int(d), int(i))}")
    return "\n\n".join(parts)


def one(q: dict, rep: int, turns: int, patch: bool, brazo: str) -> dict:
    """Loop real completo. Solo cambia el barrido profundo si patch=True."""
    original = LOOP._deep_evidence
    if patch:
        gold = narrow(q)
        LOOP._deep_evidence = lambda question, per_doc=4, n_docs=2: gold  # type: ignore[assignment]
    try:
        t0 = time.time()
        LLM.reset_usage()
        res = LOOP.run(q["question"], max_turns=turns, isolated=True)
        used = LLM.usage_totals()
    finally:
        LOOP._deep_evidence = original  # type: ignore[assignment]
    j = judge(q["question"], q["reference"], res["answer"])
    return {"id": q["id"], "brazo": brazo, "rep": rep,
            "chars_evidencia": len(narrow(q)) if patch else None,
            "score": j["score"], "verdict": j["verdict"], "error": j["error"],
            "answer": res["answer"], "latency_s": round(time.time() - t0, 1),
            "modelos": used.get("models", []), "tokens": used.get("total_tokens", 0),
            "turns": len(res.get("trace", [])), "infra_error": res.get("error")}


def main() -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["loop"], default="loop")
    ap.add_argument("--anchor", action="store_true",
                    help="activa ANCHOR_GROUNDING: una pasada de localizacion verbatim "
                         "antes de redactar")
    ap.add_argument("--arm", choices=["produccion", "estrecho"], default="produccion",
                    help="produccion = barrido real n_docs=2 (compara con las runs ciegas); "
                         "estrecho = solo el chunk gold")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--reps", type=int, default=1)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--questions", default=",".join(DEFAULT_Q))
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    out_path = Path(args.out)
    provs = LLM._providers()
    if [p[0] for p in provs] != ["nvidia"]:
        raise SystemExit(f"aborta: proveedor esperado nvidia, obtuve {provs}")
    print(f"proveedor pineado: {provs[0]}")

    LOOP.ANCHOR_GROUNDING = args.anchor
    patch = args.arm == "estrecho"
    brazo = "estrecho" if patch else ("anclaje" if args.anchor else "ancho_control")
    print(f"brazo={brazo}  ANCHOR_GROUNDING={LOOP.ANCHOR_GROUNDING}  "
          f"barrido={'solo chunk gold' if patch else 'produccion (n_docs=2)'}")

    golden = {json.loads(l)["id"]: json.loads(l)
              for l in (EVALS / "golden_blind_qa.jsonl").read_text().splitlines() if l.strip()}
    qs = [golden[i] for i in args.questions.split(",") if i.strip()]

    obs: list[dict] = []
    if out_path.exists():
        obs = json.loads(out_path.read_text()).get("observaciones", [])
        print(f"reanudando con {len(obs)} observaciones previas")
    jobs = [(q, r) for q in qs for r in range(args.reps)
            if not any(o["id"] == q["id"] and o["brazo"] == brazo and o["rep"] == r for o in obs)]
    print(f"loops pendientes: {len(jobs)}")

    def guarded(job):
        q, rep = job
        try:
            return one(q, rep, args.turns, patch=patch, brazo=brazo)
        except Exception as e:
            return {"id": q["id"], "brazo": brazo, "rep": rep, "score": None,
                    "error": f"{type(e).__name__}: {e}"}

    if jobs:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            for k, o in enumerate(ex.map(guarded, jobs), 1):
                obs.append(o)
                out_path.write_text(json.dumps({"observaciones": obs}, indent=1, ensure_ascii=False))
                print(f"  {k}/{len(jobs)} {o['id']:9} score={o['score']} "
                      f"tokens={o.get('tokens', 0):7} {o.get('modelos')} "
                      f"({o.get('latency_s', 0)}s)", flush=True)

    print(f"\n=== {brazo} (anchor={LOOP.ANCHOR_GROUNDING}) vs ancho real ===")
    per_q: dict[str, list] = {}
    for o in obs:
        if o["brazo"] != brazo or o["score"] is None:
            continue
        per_q.setdefault(o["id"], []).append(o["score"])
    for qid, sc in per_q.items():
        w = WIDE.get(qid)
        delta = f"  (ancho={st.mean(w):.2f}, delta={st.mean(sc) - st.mean(w):+.2f})" if w else ""
        print(f"  {qid:9} {brazo}={sc} media={st.mean(sc):.2f}{delta}")
    vals = [s for v in per_q.values() for s in v]
    if vals and per_q:
        base = st.mean([s for v in per_q for s in WIDE.get(v, [0])])
        print(f"  TOTAL     media={st.mean(vals):.2f}  vs ancho {base:.2f}  "
              f"delta={st.mean(vals) - base:+.2f}")
    errores = [o for o in obs if o.get("error") and o["brazo"] == brazo]
    if errores:
        print(f"\n  ATENCION: {len(errores)} llamadas con error/infra_error")

    print(f"\n--- respuesta del agente en {brazo} (wiki-b1):")
    for o in obs:
        if o["brazo"] == brazo and o["id"] == "wiki-b1":
            print(o["answer"][:600])
            break

    out_path.write_text(json.dumps({"observaciones": obs}, indent=1, ensure_ascii=False))
    print(f"\n-> {out_path}")
    return {"observaciones": obs}


if __name__ == "__main__":
    main()