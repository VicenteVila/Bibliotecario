"""Niveles 2+3: loop completo por pregunta + proveniencia de citas + judge automático.

Uso: ./.venv/bin/python evals/eval_end2end.py [--limit N]
Salida: tabla + evals/result_end2end.json. Consume cuota LLM (pacing round-robin activo).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from bibliotecario.agent import loop as LOOP  # noqa: E402
from bibliotecario.core.llm import generate  # noqa: E402

CITE = re.compile(r"\[(\d+):(\d+)\]")

JUDGE_PROMPT = """Puntúa del 1 al 5 si la RESPUESTA responde correctamente la PREGUNTA según la REFERENCIA.
5 = correcta y completa; 3 = parcial; 1 = incorrecta o vacía. Responde SOLO JSON {{"score": N, "verdict": "..."}}.

PREGUNTA: {q}
REFERENCIA: {ref}
RESPUESTA: {ans}"""


def judge(q: dict, answer: str) -> dict:
    raw = generate(JUDGE_PROMPT.format(q=q["question"], ref=q["reference"], ans=answer[:1500]),
                   max_tokens=256, retries=1)
    clean = re.sub(r"```(?:json)?", "", raw or "")
    ms = re.search(r'"score"\s*:\s*(\d)', clean)
    mv = re.search(r'"verdict"\s*:\s*"([^"]*)', clean)
    if not ms:
        return {"score": None, "verdict": "judge sin score, raw=" + clean[:80]}
    return {"score": int(ms.group(1)) or None, "verdict": (mv.group(1) if mv else "")[:200]}


def save(out, agg=None):
    (EVALS / "result_end2end.json").write_text(
        json.dumps({"aggregate": agg or {}, "rows": out}, indent=1, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--ids", default="", help="coma-separados, ej. wiki-1,tce-3 (para lotes)")
    args = ap.parse_args()
    # Abarata cada llamada LLM en la eval (menos backoffs); se documenta en el JSON.
    import bibliotecario.core.llm as _LLM
    _orig = _LLM.generate
    LOOP.generate = lambda p, max_tokens=512, retries=None: _orig(
        p, max_tokens, args.retries if retries is None else retries)
    rows = [json.loads(l) for l in (EVALS / "golden_qa.jsonl").read_text().splitlines() if l.strip()]
    if args.ids:
        want = set(args.ids.split(","))
        rows = [q for q in rows if q["id"] in want]
    if args.limit:
        rows = rows[:args.limit]
    out, done = [], set()
    rp = EVALS / "result_end2end.json"
    if rp.exists():
        try:
            prev = json.loads(rp.read_text(encoding="utf-8"))
            out = prev.get("rows", [])
            done = {r["id"] for r in out}
        except ValueError:
            pass
    for q in [q for q in rows if q["id"] not in done]:
        t0 = time.time()
        try:
            r = LOOP.run(q["question"], max_turns=args.turns)
        except Exception as e:
            r = {"answer": "", "evidence": [], "turns": 0, "error": str(e)[:120]}
        cites = CITE.findall(r.get("answer", ""))
        ev_docs = [e.get("doc_id") for e in r.get("evidence", []) if isinstance(e, dict)]
        all_docs = [int(d) for d, _ in cites] + ev_docs
        hit = sum(1 for d in all_docs if d == q["doc_id"])
        prov = round(hit / len(all_docs), 3) if all_docs else 0.0
        ans = r.get("answer", "")
        fallback = ans.startswith("(presupuesto agotado)") or ans.startswith("(extractivo)")
        j = {"score": None, "verdict": "omitido (fallback sin LLM)"} if fallback or not ans else judge(q, ans)
        row = {"id": q["id"], "doc_id": q["doc_id"], "turns": r.get("turns"),
               "citation_precision": prov, "n_cites": len(all_docs),
               "judge": j["score"], "verdict": j["verdict"],
               "fallback": fallback, "latency_s": round(time.time() - t0),
               "answer": ans[:400]}
        out.append(row)
        save(out)  # resumible: persiste cada pregunta
        print(f"{q['id']:8} citas={prov:.2f} judge={j['score']} fb={fallback} {str(j['verdict'])[:60]}", flush=True)
    scored = [r["judge"] for r in out if r["judge"]]
    provs = [r["citation_precision"] for r in out]
    agg = {"n": len(out),
           "citation_precision_mean": round(sum(provs) / len(provs), 3) if provs else 0,
           "judge_mean": round(sum(scored) / len(scored), 2) if scored else None,
           "judge_n": len(scored), "fallbacks": sum(1 for r in out if r["fallback"]),
           "turns": args.turns, "retries": args.retries}
    print(f"\nprovenienca_citas={agg['citation_precision_mean']} judge_mean={agg['judge_mean']} "
          f"(n={agg['judge_n']}) fallbacks={agg['fallbacks']}")
    save(out, agg)


if __name__ == "__main__":
    main()
