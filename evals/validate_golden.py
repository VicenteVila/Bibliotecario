"""Valida estructuralmente un golden set ciego contra el corpus.

No judgea respuestas: comprueba que cada pregunta sea localizable, que sus
keywords existan literalmente en los chunks que cita y que la marcacion de
no respondibles sea coherente. Ejecutar tras anadir preguntas.

    python evals/validate_golden.py evals/golden_blind_qa_ext.jsonl
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bibliotecario.core import storage

REQUIRED = ["id", "paper", "doc_id", "difficulty", "question", "reference",
            "keywords", "answerable_docs", "cite_chunks"]
DIFFICULTIES = {"facil", "media", "dificil"}


def norm(text):
    """Colapsa espacios y guiones de corte de linea para comparar literales."""
    text = text.replace("\u2011", "-").replace("\u00ad", "")
    # Une palabras partidas por guion a final de linea ("iter- ation" -> "iteration").
    text = re.sub(r"-\s+", "", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def load_chunks():
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT doc_id, chunk_idx, text FROM chunks").fetchall()
    return {(r["doc_id"], r["chunk_idx"]): norm(r["text"] or "") for r in rows}


def validate(path, chunks):
    errors, warnings, ids, questions = [], [], set(), []
    by_doc = Counter()
    difficulty = Counter()

    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        qid = f"linea {lineno}"
        try:
            q = json.loads(raw)
        except json.JSONDecodeError as exc:
            errors.append(f"{qid}: JSON invalido ({exc})")
            continue

        missing = [f for f in REQUIRED if f not in q]
        if missing:
            errors.append(f"{q.get('id', qid)}: faltan campos {missing}")
            continue

        qid = q["id"]
        if qid in ids:
            errors.append(f"{qid}: id duplicado")
        ids.add(qid)
        questions.append(norm(q["question"]))

        if q["difficulty"] not in DIFFICULTIES:
            errors.append(f"{qid}: dificultad invalida {q['difficulty']!r}")
        by_doc[q["doc_id"]] += 1
        difficulty[q["difficulty"]] += 1

        unanswerable = bool(q.get("unanswerable"))
        if unanswerable:
            if q["answerable_docs"]:
                errors.append(f"{qid}: unanswerable con answerable_docs {q['answerable_docs']}")
            if not q["reference"].upper().startswith("UNANSWERABLE"):
                errors.append(f"{qid}: unanswerable sin prefijo UNANSWERABLE en la referencia")
        elif not q["answerable_docs"]:
            errors.append(f"{qid}: respondible sin answerable_docs")
        elif not set(q["answerable_docs"]) <= set([q["doc_id"]]):
            warnings.append(f"{qid}: answerable_docs {q['answerable_docs']} no incluye doc_id {q['doc_id']}")

        if not q["cite_chunks"]:
            errors.append(f"{qid}: sin cite_chunks")
            continue

        pool = []
        for ref in q["cite_chunks"]:
            try:
                doc, idx = ref.split(":")
                key = (int(doc), int(idx))
            except ValueError:
                errors.append(f"{qid}: cite_chunk mal formado {ref!r}")
                continue
            if key not in chunks:
                errors.append(f"{qid}: chunk inexistente {ref}")
                continue
            if key[0] != q["doc_id"]:
                errors.append(f"{qid}: chunk {ref} de otro documento (doc_id {q['doc_id']})")
            pool.append(chunks[key])

        haystack = " ".join(pool)
        if not unanswerable:
            absent = [k for k in q["keywords"] if norm(k) not in haystack]
            if absent:
                errors.append(f"{qid}: keywords ausentes de los chunks citados {absent}")

    for i, a in enumerate(questions):
        for b in questions[i + 1:]:
            if a == b:
                errors.append(f"pregunta duplicada: {a[:70]}")

    return errors, warnings, by_doc, difficulty, sum(by_doc.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("golden", nargs="+",
                    help="uno o varios golden .jsonl a validar")
    args = ap.parse_args()

    chunks = load_chunks()
    failed = False
    for name in args.golden:
        path = Path(name)
        errors, warnings, by_doc, difficulty, total = validate(path, chunks)
        unanswerable = 0
        for raw in path.read_text(encoding="utf-8").splitlines():
            if raw.strip() and json.loads(raw).get("unanswerable"):
                unanswerable += 1

        print(f"== {path.name}: {total} preguntas "
              f"({total - unanswerable} respondibles, {unanswerable} no respondibles)")
        print(f"   por documento: {dict(sorted(by_doc.items()))}")
        print(f"   dificultad:    {dict(sorted(difficulty.items()))}")
        for w in warnings:
            print(f"   aviso:  {w}")
        for e in errors:
            print(f"   ERROR:  {e}")
        if errors:
            failed = True
            print(f"   -> {len(errors)} problemas")
        else:
            print("   -> ok")
        print()

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()