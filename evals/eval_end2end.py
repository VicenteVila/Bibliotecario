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
  (que mete decenas de miles de caracteres) sale rentable. Esto incluye los del
  AGENTE, no solo los del juez: sin coste del agente no se puede decidir nada.
- Las preguntas `unanswerable` no se puntúan con la rúbrica 1-5: se pide al juez
  que decida si el agente se abstuvo o inventó. Una abstención no es un "1".

Uso:
  python evals/eval_end2end.py --turns 5
  python evals/eval_end2end.py --ids wiki-2,tce-3 --turns 5
  python evals/eval_end2end.py --golden golden_blind_qa.jsonl --workers 4 \
      --out result_blind_r1.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

EVALS = Path(__file__).parent
sys.path.insert(0, str(EVALS.parent))

import bibliotecario.core.llm as LLM
from bibliotecario.agent import loop as LOOP
from bibliotecario.ingest import citations_format as CITE_FMT
from evals.judge import JUDGE_MODEL, judge, judge_abstention


def save(out, agg=None, path: Path | None = None, meta: dict | None = None):
    (path or (EVALS / "result_end2end.json")).write_text(
        json.dumps({"meta": meta or {}, "aggregate": agg or {}, "rows": out},
                   indent=1, ensure_ascii=False),
        encoding="utf-8")


def gold_docs(q: dict) -> list[int]:
    """Documentos que la pregunta necesita. Acepta doc_id o answerable_docs."""
    if q.get("answerable_docs"):
        return list(q["answerable_docs"])
    return [q["doc_id"]] if "doc_id" in q else []


# Lenguaje de abstención. Distingue "no está en el corpus" de "lo respondí".
# Hace falta en las DOS direcciones: si el agente se abstiene en una pregunta
# respondible porque no recuperó el chunk, el fallo es de retrieval y no debe
# mezclarse con la calidad de la respuesta. En la run 1 abstain_rate fue 1.0
# sobre las no respondibles y aun así 2 de 7 abstenciones eran falsas.
_ABSTAIN_WORDS = re.compile(
    r"(no se encontr[oó]|not found|no .{0,25}evidencia espec|"
    r"does not (explicitly )?(report|mention|state)|"
    r"no (encuentra|aparece|consta|se menciona|indica)|"
    r"La evidencia disponible no|insufficient evidence|could not find|"
    r"no (hay|hay datos|dice|consta) (evidencia|datos|informaci[oó]n))", re.IGNORECASE)


def looks_abstained(answer: str) -> bool:
    return bool(_ABSTAIN_WORDS.search(answer or ""))


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


def run_one(q: dict, turns: int) -> dict:
    """Ejecuta una pregunta y devuelve su fila. No lanza: todo error va a la fila."""
    LLM.reset_usage()
    t0 = time.time()
    try:
        r = LOOP.run(q["question"], max_turns=turns)
    except Exception as e:
        r = {"answer": "", "evidence": [], "turns": 0, "error": str(e)[:120]}
    usage = LLM.usage_totals()
    ans = r.get("answer", "")
    evidence = r.get("evidence", [])
    cm = citation_metrics(q, ans, evidence)
    fallback = ans.startswith(("(presupuesto agotado)", "(extractivo)"))
    unanswerable = bool(q.get("unanswerable"))

    if unanswerable:
        # Puntuarla de 1 a 5 no tiene sentido: lo que se mide es si se abstuvo.
        j = ({"abstained": False, "fabricated_value": None, "justification": "sin respuesta",
              "usage": {}, "error": "fallback sin LLM"}
             if (fallback or not ans)
             else judge_abstention(q["question"], ans))
    elif fallback or not ans:
        j = {"score": 0, "verdict": "omitido (fallback sin LLM)", "error": None,
             "model": JUDGE_MODEL, "usage": {}}
    else:
        j = judge(q["question"], q["reference"], ans)

    return {"id": q["id"], "doc_id": q.get("doc_id"), "difficulty": q.get("difficulty"),
            "unanswerable": unanswerable, "turns": r.get("turns"), **cm,
            "answer_has_cite": CITE_FMT.has_citation(ans),
            "truncated": ans.rstrip().endswith("[…truncado]"),
            "judge": j.get("score"), "judge_error": j.get("error"),
            "judge_model": j.get("model"), "judge_usage": j.get("usage"),
            "abstained": j.get("abstained"),
            "fabricated_value": j.get("fabricated_value"),
            "looks_abstained": looks_abstained(ans),
            "fallback": fallback, "latency_s": round(time.time() - t0),
            "agent_usage": usage,
            "answer": ans}  # respuesta completa: los 400 chars impedían auditar


def aggregate(out: list, turns: int, retries: int) -> dict:
    """Agregados. Las no respondibles NO entran en judge_mean.

    Meter abstenciones en la media de 1-5 baja la nota por comportarse bien, y
    es justo el error que este harness ya cometió una vez con los judges no
    parseables. Cada grupo se reporta por separado.
    """
    ans_rows = [r for r in out if not r.get("unanswerable")]
    un_rows = [r for r in out if r.get("unanswerable")]
    na, nu = len(ans_rows), len(un_rows)

    def mean(xs):
        return round(sum(xs) / len(xs), 3) if xs else None

    # Las claves existen siempre,(None si no aplica): que un consumidor lea
    # judge_mean y se KeyError porque no había respondibles es una forma
    # innecesaria de romperse.
    agg = {"n": len(out), "n_answerable": na, "n_unanswerable": nu,
           "judge_model": JUDGE_MODEL, "turns": turns, "retries": retries,
           "judge_mean": None, "n_scored": 0, "n_judge_errors": 0,
           "cite_precision_mean": None, "cite_coverage_mean": None,
           "answer_cite_rate": None, "by_difficulty": None,
           "abstain_rate": None, "n_abstain_decided": 0, "n_abstain_errors": 0,
           "n_fabricated": 0, "latency_median_s": None,
           "false_abstention_rate": None, "n_false_abstention": 0,
           "answer_rate_on_answerable": None, "false_abstention_ids": []}

    if na:
        scores = [0 if r["judge"] is None else r["judge"] for r in ans_rows]
        errs = sum(1 for r in ans_rows if r["judge"] is None)
        agg.update({
            "judge_mean": mean(scores),               # judge no parseable = 0
            "n_scored": na - errs, "n_judge_errors": errs,
            "cite_precision_mean": mean([r["cite_precision"] for r in ans_rows]),
            "cite_coverage_mean": mean([r["cite_coverage"] for r in ans_rows]),
            "answer_cite_rate": mean([1.0 if r["answer_has_cite"] else 0.0 for r in ans_rows]),
            "by_difficulty": {d: mean([0 if r["judge"] is None else r["judge"]
                                       for r in ans_rows if r["difficulty"] == d])
                              for d in ("facil", "media", "dificil")},
        })
    if nu:
        decided = [r for r in un_rows if r["abstained"] is not None]
        agg.update({
            "abstain_rate": mean([1.0 if r["abstained"] else 0.0 for r in decided]),
            "n_abstain_decided": len(decided), "n_abstain_errors": nu - len(decided),
            "n_fabricated": sum(1 for r in un_rows if r.get("fabricated_value")),
        })
    if na:
        # Abstención sobre preguntas respondibles: no es una virtud, es retrieval
        # fallido. Se mide aparte para no leer el abstain_rate como una skill.
        fa = [r for r in ans_rows if r.get("looks_abstained")]
        agg.update({
            "false_abstention_rate": round(len(fa) / na, 3),
            "n_false_abstention": len(fa),
            "answer_rate_on_answerable": round(1 - len(fa) / na, 3),
            "false_abstention_ids": [r["id"] for r in fa],
        })
    if out:
        # Si solo hay no respondibles, la mediana sale de esas filas y no de None.
        src = ans_rows or out
        agg["latency_median_s"] = sorted(r["latency_s"] for r in src)[len(src) // 2]
    agg.update({
        "truncated": sum(1 for r in out if r["truncated"]),
        "fallbacks": sum(1 for r in out if r["fallback"]),
        "agent_tokens_total": sum(r["agent_usage"].get("total_tokens", 0) for r in out),
        "agent_calls_total": sum(r["agent_usage"].get("calls", 0) for r in out),
        "agent_calls_tokens_unknown": sum(r["agent_usage"].get("calls_tokens_unknown", 0)
                                          for r in out),
        # Qué modelos respondieron de verdad. Si esto mezcla dos modelos, la run
        # está contaminada aunque la media parezca bien.
        "agent_models": sorted({m for r in out for m in r["agent_usage"].get("models", [])}),
        "judge_tokens_total": sum((r.get("judge_usage") or {}).get("total_tokens", 0) or 0
                                  for r in out),
    })
    return agg


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--turns", type=int, default=4)
    ap.add_argument("--retries", type=int, default=1)
    ap.add_argument("--ids", default="", help="coma-separados, ej. wiki-1,tce-3 (para lotes)")
    ap.add_argument("--out", default="result_end2end.json")
    ap.add_argument("--golden", default="golden_qa.jsonl")
    ap.add_argument("--workers", type=int, default=1,
                    help="preguntas en paralelo (el sink de tokens es thread-local)")
    ap.add_argument("--run", default="", help="etiqueta de la run, va en el JSON")
    ap.add_argument("--provider", default="",
                    help="fija proveedores (p.ej. nvidia). Sin esto el round-robin "
                         "reparte la run entre Nemotron y Gemini y se mezclan dos agentes")
    args = ap.parse_args()

    if args.provider:
        os.environ["LLM_PROVIDERS"] = args.provider

    # Un 504 transitorio en la NVIDIA no debe hacer que el resto de la run
    # conteste con Gemini: la media mezclaría dos modelos y seguiría pareciendo
    # válida. Con strict_fallback la pregunta queda como fallida y se ve.
    LOOP.STRICT_FALLBACK = True
    _gen = LOOP.generate  # conserva strict_fallback del wrapper
    LOOP.generate = lambda p, max_tokens=512, retries=None: _gen(
        p, max_tokens, args.retries if retries is None else retries)

    rows = [json.loads(l) for l in (EVALS / args.golden).read_text().splitlines() if l.strip()]
    if args.ids:
        want = set(args.ids.split(","))
        rows = [q for q in rows if q["id"] in want]
    if args.limit:
        rows = rows[:args.limit]

    rp = EVALS / args.out
    out, done = [], set()
    if rp.exists():
        try:
            prev = json.loads(rp.read_text(encoding="utf-8"))
            out, done = prev.get("rows", []), {r["id"] for r in prev.get("rows", [])}
        except ValueError:
            pass
    meta = {"golden": args.golden, "run": args.run, "judge_model": JUDGE_MODEL,
            "workers": args.workers, "providers": LLM._providers()}

    todo = [q for q in rows if q["id"] not in done]
    results: dict[str, dict] = {}

    def emit(row):
        results[row["id"]] = row
        # Se persiste en orden del golden para que los ficheros sean comparables.
        # Las filas ya guardadas se conservan y las nuevas pisan por id: sin este
        # merge, reanudar una run interrumpida descarte las filas anteriores sin
        # avisar. Pasó de verdad: se perdieron 4 preguntas de la primera run.
        merged_map = {r["id"]: r for r in out}
        merged_map.update(results)
        merged = [merged_map[q["id"]] for q in rows if q["id"] in merged_map]
        save(merged, aggregate(merged, args.turns, args.retries), rp, meta)
        flag = ("abst=" + str(row["abstained"])) if row["unanswerable"] else f"judge={row['judge']}"
        print(f"{row['id']:8} prec={row['cite_precision']:.2f} {flag} "
              f"tok={row['agent_usage'].get('total_tokens', 0):6} "
              f"fb={row['fallback']} {row['latency_s']}s", flush=True)

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(run_one, q, args.turns): q for q in todo}
            for f in as_completed(futs):
                emit(f.result())
    else:
        for q in todo:
            emit(run_one(q, args.turns))

    merged_map = {r["id"]: r for r in out}
    merged_map.update(results)
    merged = [merged_map[q["id"]] for q in rows if q["id"] in merged_map]
    agg = aggregate(merged, args.turns, args.retries)
    save(merged, agg, rp, meta)
    print(f"\nn={agg['n']} (respondibles={agg['n_answerable']}, "
          f"no respondibles={agg['n_unanswerable']}) modelo_juez={JUDGE_MODEL}")
    if agg["n_answerable"]:
        print(f"judge={agg['judge_mean']} (n={agg['n_scored']}/{agg['n_answerable']}, "
              f"{agg['n_judge_errors']} errores)  por dificultad={agg['by_difficulty']}")
        print(f"cite_precision={agg['cite_precision_mean']} "
              f"cite_coverage={agg['cite_coverage_mean']} con_cita={agg['answer_cite_rate']}")
    if agg["n_answerable"]:
        print(f"abstencion_falsa={agg['false_abstention_rate']} "
              f"{agg['false_abstention_ids']} (respondidas={agg['answer_rate_on_answerable']})")
    if agg["n_unanswerable"]:
        print(f"abstain_rate={agg['abstain_rate']} "
              f"(decididas={agg['n_abstain_decided']}/{agg['n_unanswerable']}, "
              f"{agg['n_abstain_errors']} errores) inventadas={agg['n_fabricated']}")
    print(f"tokens_agente={agg['agent_tokens_total']} en {agg['agent_calls_total']} llamadas | "
          f"tokens_juez={agg['judge_tokens_total']} | latencia_mediana={agg['latency_median_s']}s")
    print(f"truncadas={agg['truncated']} fallbacks={agg['fallbacks']} -> {args.out}")


if __name__ == "__main__":
    main()