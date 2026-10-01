import json
import sqlite3
from collections import Counter

import pytest

from bibliotecario.config import data_dir

BLIND = "evals/golden_blind_qa.jsonl"
DOCS = (1, 2, 3, 4, 5)
PER_DOC = 8
MIN_UNANSWERABLE = 5


def _rows():
    with open(BLIND, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


@pytest.fixture(scope="module")
def rows():
    return _rows()


@pytest.fixture(scope="module")
def corpus():
    conn = sqlite3.connect(f"file:{data_dir() / 'bibliotecario.db'}?mode=ro", uri=True)
    try:
        return {
            (r[0], r[1]): " ".join(r[2].split()).lower()
            for r in conn.execute("SELECT doc_id, chunk_idx, text FROM chunks")
        }
    finally:
        conn.close()


def test_forty_unique_ids(rows):
    assert len(rows) == 40
    assert len({r["id"] for r in rows}) == 40


def test_balanced_across_papers(rows):
    assert Counter(r["doc_id"] for r in rows) == Counter({d: PER_DOC for d in DOCS})


def test_difficulty_spread(rows):
    counts = Counter(r["difficulty"] for r in rows)
    assert set(counts) == {"facil", "media", "dificil"}
    assert counts["facil"] >= 12
    assert counts["media"] >= 12
    assert counts["dificil"] >= 12


def test_unanswerable_flag_is_consistent(rows):
    for r in rows:
        assert r.get("unanswerable", False) is (r["answerable_docs"] == []), r["id"]
    unanswerable = [r for r in rows if r.get("unanswerable")]
    assert len(unanswerable) >= MIN_UNANSWERABLE
    assert Counter(r["doc_id"] for r in unanswerable) == Counter({d: 1 for d in DOCS})
    for r in unanswerable:
        assert r["reference"].startswith("UNANSWERABLE"), r["id"]


def test_required_fields(rows):
    for r in rows:
        for key in ("id", "paper", "doc_id", "difficulty", "question", "reference", "keywords"):
            assert r.get(key), f"{r.get('id')} sin {key}"
        assert isinstance(r["keywords"], list) and r["keywords"]
        assert r["cite_chunks"]


def test_cited_chunks_exist(rows, corpus):
    for r in rows:
        for cite in r["cite_chunks"]:
            doc, idx = (int(x) for x in cite.split(":"))
            assert (doc, idx) in corpus, f"{r['id']} cita inexistente {cite}"
            assert doc == r["doc_id"], f"{r['id']} cita de otro paper: {cite}"


def test_answerable_keywords_are_grounded(rows, corpus):
    """Cada keyword debe aparecer literalmente en el texto citado.

    Es la defensa contra referencias decoradas: si alguien reescribe una
    referencia sin volver a mirar el chunk, esta test falla.
    """
    for r in rows:
        if r.get("unanswerable"):
            continue
        blob = " ".join(corpus[tuple(int(x) for x in c.split(":"))] for c in r["cite_chunks"])
        missing = [k for k in r["keywords"] if k.lower().strip("[]") not in blob]
        assert not missing, f"{r['id']} keywords sin respaldo en el chunk: {missing}"


def test_reference_does_not_leak_unanswerable_marker_into_answerables(rows):
    for r in rows:
        if r.get("unanswerable"):
            continue
        assert "UNANSWERABLE" not in r["reference"], r["id"]