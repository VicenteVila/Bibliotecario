"""Eval end-to-end: loop completo + juez pineado.

Métricas corregidas (F0 del plan de evaluación):

- El juez NO es el mismo modelo que el agente (ver evals/judge.py): usa
  gpt-oss-20b, familia distinta. Antes ambos usaban la misma generate(), así que
  el juez se auto-favorecía.
- Una pregunta cuyo juez no parsea cuenta como 0, NO se descarta de la media.
  Antes `scored = [r for r in rows if r["judge"]]` las eliminaba en silencio: el
  juez falla justo con respuestas largas (las difíciles), así que la media salía
  inflada. Ahora se reporta n_total, n_scored y n_errors por separado.
- La provenance se mide contra `answerable_docs` (lista), no contra un único
  doc_id: una pregunta multi-paper no puede dar 1.0 con un solo campo.
  Se separan precisión de cita y cobertura del gold.
- Se guardan los tokens usados, para poder decidir si el barrido profundo
  (que mete decenas de miles de caracteres) sale rentable.

Uso:
  python evals/eval_end2end.py --turns 5
  python evals/eval_end2end.py --ids wiki-2,tce-3 --turns 5
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from bibliotecario.agent import loop as LOOP
from bibliotecario.ingest import citations_format as CITE_FMT
from evals.judge import JUDGE_MODEL, judge


def save(out, agg=None, path: Path | None = None):
    (path or (EVALS / "result_end2end.json")).write_text(
        json.dumps({"aggregate": agg or {}, "rows": out}, indent=1, ensure_ascii=False),
        encoding="utf-8")


def gold_docs(q: dict) -> list[int]:
    """Documentos que la pregunta necesita. Acepta doc_id o answerable_docs."""
    if q.get("answerable_docs"):
        return list(q["answerable_docs"])
    return [q["doc_id"]] if "doc_id" in q else []


def citation_metrics(q: dict, answer: str, evidence: list) -> dict:
    """Precisión y cobertura de citas contra los documentos que la pregunta pide.

    Antes esto era una sola cifra contra un doc_id, lo que punishaba a las
    preguntas multi-paper por construcción (techo de 0.5).
    """
    gold = set(gold_docs(q))
    cites = CITE_FMT.parse_citations(answer)
    cited_docs = {d for d, _ in cites}
    ev_docs = {e.get("doc_id") for e in evidence if isinstance(e, dict)}
    all_docs = cited_docs | ev_docs
    precision = len(cited_docs & gold) / len(cited_docs) if cited_docs else 0.0
    coverage = len(cited_docs & gold) / len(gold) if gold else 0.0
    stray = len(all_docs - gold)
    return {"cite_precision": round(precision, 3), "cite_coverage": round(coverage, 3),
            "stray_docs": stray, "answer_cites": len(cites), "n_evid": len(evidence)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--ids", default="", help="coma-separados, ej. wiki-1,tce-3 (para lotes)")
    ap.add_argument("--out", default="result_end2end.json")
    args = ap.parse_args()

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
    rp = EVALS / args.out
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
        ans = r.get("answer", "")
        evidence = r.get("evidence", [])
        cm = citation_metrics(q, ans, evidence)
        fallback = ans.startswith(("(presupuesto agotado)", "(extractivo)"))
        if fallback or not ans:
            j = {"score": 0, "verdict": "omitido (fallback sin LLM)", "error": None,
                 "model": JUDGE_MODEL, "usage": {}}
        else:
            j = judge(q["question"], q["reference"], ans)
        row = {"id": q["id"], "doc_id": q.get("doc_id"), "difficulty": q.get("difficulty"),
               "turns": r.get("turns"), **cm,
               "answer_has_cite": CITE_FMT.has_citation(ans),
               "truncated": ans.rstrip().endswith("[…truncado]"),
               "judge": j["score"], "judge_error": j.get("error"),
               "judge_model": j.get("model"), "judge_usage": j.get("usage"),
               "fallback": fallback, "latency_s": round(time.time() - t0),
               "answer": ans}  # respuesta completa: los 400 chars impedían auditar
        out.append(row)
        save(out, {"judge_model": JUDGE_MODEL}, rp)  # resumible: persiste cada pregunta
        print(f"{q['id']:8} prec={cm['cite_precision']:.2f} judge={j['score']} "
              f"fb={fallback} {str(j['verdict'])[:60]}", flush=True)

    # Agregado: judge=None se cuenta como 0 (no se descarta) para no inflar la media.
    n = len(out)
    scores = [0 if r["judge"] is None else r["judge"] for r in out]
    errors = sum(1 for r in out if r["judge"] is None)
    tok = sum((r.get("judge_usage") or {}).get("total_tokens", 0) or 0 for r in out)
    agg = {"n": n,
           "n_scored": n - errors, "n_judge_errors": errors,
           "judge_mean": round(sum(scores) / n, 3) if n else None,
           "judge_mean_ignoring_errors": round(
               sum(s for s in scores if s) / max(1, n - errors), 2) if n else None,
           "judge_model": JUDGE_MODEL,
           "cite_precision_mean": round(sum(r["cite_precision"] for r in out) / n, 3) if n else 0,
           "cite_coverage_mean": round(sum(r["cite_coverage"] for r in out) / n, 3) if n else 0,
           "answer_cite_rate": round(sum(1 for r in out if r["answer_has_cite"]) / n, 3) if n else 0,
           "truncated": sum(1 for r in out if r["truncated"]),
           "fallbacks": sum(1 for r in out if r["fallback"]),
           "judge_tokens_total": tok, "turns": args.turns, "retries": args.retries}
    print(f"\njudge={agg['judge_mean']} (n={agg['n_scored']}/{agg['n']}, "
          f"{errors} errores) modelo={JUDGE_MODEL}")
    print(f"cite_precision={agg['cite_precision_mean']} "
          f"cite_coverage={agg['cite_coverage_mean']} "
          f"con_cita={agg['answer_cite_rate']} truncadas={agg['truncated']} "
          f"fallbacks={agg['fallbacks']} tokens_judge={tok}")
    save(out, agg, rp)


if __name__ == "__main__":
    main()