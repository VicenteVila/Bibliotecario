"""Nivel 1: precisión de retrieval (mecánico, 0 llamadas LLM).

Por cada pregunta del golden set: retriever.search(q, top_k=10) y métricas
recall@1/3/5 + MRR contra el doc_id objetivo. Salida: tabla + evals/result_retrieval.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

from bibliotecario.memory import retriever  # noqa: E402

TOP_K = 10


def main() -> dict:
    rows = [json.loads(l) for l in (EVALS / "golden_qa.jsonl").read_text().splitlines() if l.strip()]
    out, rr_sum, r1 = [], 0.0, 0
    r3 = r5 = 0
    for q in rows:
        t0 = time.time()
        hits = retriever.search(q["question"], top_k=TOP_K)
        dt = time.time() - t0
        rank = next((i + 1 for i, h in enumerate(hits) if h["doc_id"] == q["doc_id"]), None)
        rr = 1.0 / rank if rank else 0.0
        rr_sum += rr
        r1 += rank == 1
        r3 += rank is not None and rank <= 3
        r5 += rank is not None and rank <= 5
        got = hits[0]["doc_id"] if hits else None
        out.append({"id": q["id"], "paper": q["paper"], "difficulty": q["difficulty"],
                    "rank": rank, "top1_doc": got, "latency_s": round(dt, 1)})
        print(f"{q['id']:8} [{q['difficulty']:7}] rank={str(rank):4} top1=doc{got} ({dt:.0f}s) {'OK' if rank == 1 else 'FALLO' if rank is None else 'parcial'}")
    n = len(rows)
    agg = {"n": n, "recall@1": round(r1 / n, 3), "recall@3": round(r3 / n, 3),
           "recall@5": round(r5 / n, 3), "MRR@10": round(rr_sum / n, 3)}
    print(f"\nrecall@1={agg['recall@1']} recall@3={agg['recall@3']} recall@5={agg['recall@5']} MRR@10={agg['MRR@10']}")
    (EVALS / "result_retrieval.json").write_text(json.dumps({"aggregate": agg, "rows": out}, indent=1))
    return agg


if __name__ == "__main__":
    main()
