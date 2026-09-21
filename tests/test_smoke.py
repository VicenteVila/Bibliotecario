from bibliotecario.core import storage
from bibliotecario.core.embeddings import blob_to_vec, embed_blob, text_fingerprint


def test_init_db_creates_schema(tmp_path):
    db = tmp_path / "smoke.db"
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for expected in ("documents", "chunks", "nodes", "edges", "validation_tasks",
                     "task_outcomes", "lessons", "skills", "wiki_pages", "harness_runs"):
        assert expected in tables


def test_embedding_blob_roundtrip():
    import numpy as np
    vec = np.ones(8, dtype="float32") / 8
    assert (blob_to_vec(embed_blob(vec)) == vec).all()
    assert len(text_fingerprint("hola")) == 32
