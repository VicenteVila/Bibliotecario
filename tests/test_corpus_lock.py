"""CORPUS_LOCK: congelación del corpus de evaluación y detección de cambios."""
from __future__ import annotations

import json
import os
import sys

import pytest

from bibliotecario.core import storage
from evals import corpus_lock as CL
from evals import eval_end2end as H


def _mkdb(tmp_path, monkeypatch, docs):
    """BD con `docs` = [(title, capa|None)] y un fichero real por documento.

    Un fichero real hace falta: el lock guarda el sha256 del PDF, que es la
    parte que detecta "alguien sobreescribió el paper en Documentos/".
    """
    db = tmp_path / "lock.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    files = {}
    with storage.get_conn() as conn:
        for i, (title, capa) in enumerate(docs, start=1):
            f = tmp_path / f"doc{i}.pdf"
            f.write_text(f"texto del paper {i}")
            files[i] = f
            conn.execute("INSERT INTO documents (path, title, paper_hash, corpus_capa) VALUES (?,?,?,?)",
                         (str(f), title, f"hash{i}", capa))
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text) VALUES (?,?,?)",
                         (i, 0, "chunk"))
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text) VALUES (?,?,?)",
                         (i, 1, "chunk2"))
    monkeypatch.setattr(CL, "LOCK", tmp_path / "CORPUS_LOCK.json")
    return db, files


def _goldens(monkeypatch, ids=(1,), sha="sha-golden-1"):
    monkeypatch.setattr(CL, "evaluacion_doc_ids", lambda: {"golden_qa.jsonl": list(ids)})
    monkeypatch.setattr(CL, "golden_files", lambda: {"golden_qa.jsonl": sha})


def test_label_deriva_capas_de_los_goldens(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL: Path-Entity Aligned Relational Learning with Contextual Subgraphs", None),
        ("Segundo paper ciego", None),
        ("Tercer paper largo", None),
    ])
    _goldens(monkeypatch, ids=(1, 2))
    r = CL.label(db)
    with storage.get_conn(db) as conn:
        capas = [tuple(x) for x in conn.execute(
            "SELECT id, corpus_capa FROM documents ORDER BY id")]
    assert capas == [(1, "fundacional,evaluacion"),
                     (2, "evaluacion,extendido"),
                     (3, "extendido")]
    assert r["evaluacion_doc_ids"] == [1, 2] and r["etiquetados"] == 3
    # idempotente: segunda pasada no cambia nada
    assert CL.label(db)["etiquetados"] == 0


def test_label_no_pisa_etiqueta_manual(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [("Paper suelto", "fundacional")])
    _goldens(monkeypatch, ids=(99,))
    assert CL.label(db)["etiquetados"] == 0
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT corpus_capa FROM documents").fetchone()["corpus_capa"] == "fundacional"
    CL.label(db, reset=True)
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT corpus_capa FROM documents").fetchone()["corpus_capa"] == "extendido"


def test_build_y_check_en_verde(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL: Path-Entity Aligned Relational Learning", "fundacional,evaluacion"),
        ("Paper extendido", "extendido"),
    ])
    _goldens(monkeypatch, ids=(1,))
    lock = CL.build(db)
    assert lock["evaluacion_doc_ids"] == [1]
    assert len(lock["docs"]) == 2 and lock["lotes"][0]["nombre"] == "corpus-inicial"
    r = CL.check(db)
    assert r["fatal"] == [] and r["avisos"] == []


def test_check_sin_lock(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [("P", "extendido")])
    r = CL.check(db)
    assert any("CORPUS_LOCK" in p for p in r["fatal"])


def test_check_detecta_texto_cambiado_en_doc_de_evaluacion(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL: Path-Entity Aligned Relational Learning", "fundacional,evaluacion"),
        ("Paper extendido", "extendido"),
    ])
    _goldens(monkeypatch, ids=(1,))
    CL.build(db)
    with storage.get_conn(db) as conn:
        conn.execute("UPDATE documents SET paper_hash='otrohash' WHERE id=1")
    r = CL.check(db)
    assert any("doc 1" in p and "paper_hash" in p for p in r["fatal"]), r
    assert r["avisos"] == []


def test_check_doc_extendido_cambiado_es_aviso(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL: Path-Entity Aligned Relational Learning", "fundacional,evaluacion"),
        ("Paper extendido", "extendido"),
    ])
    _goldens(monkeypatch, ids=(1,))
    CL.build(db)
    with storage.get_conn(db) as conn:
        # el troceado cambia: alguien re-ingeriría el doc con otro splitter
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text) VALUES (?,?,?)", (2, 5, "chunk nuevo"))
    r = CL.check(db)
    assert r["fatal"] == [] and any("doc 2" in p and "troceado" in p for p in r["avisos"]), r


def test_check_detecta_fichero_sobrescrito(tmp_path, monkeypatch):
    db, files = _mkdb(tmp_path, monkeypatch, [
        ("PEARL,Path-Entity Aligned Relational Learning", "fundacional,evaluacion")])
    _goldens(monkeypatch, ids=(1,))
    CL.build(db)
    files[1].write_text("otro contenido, mismo path")
    r = CL.check(db)
    assert any("doc 1" in p and "fichero" in p for p in r["fatal"]), r


def test_check_detecta_golden_cambiado(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [("P", "extendido")])
    _goldens(monkeypatch, ids=(1,), sha="sha-vieja")
    CL.build(db)
    _goldens(monkeypatch, ids=(1,), sha="sha-nueva")
    r = CL.check(db)
    assert any("golden_qa.jsonl" in p for p in r["fatal"]), r


def test_check_documentos_nuevos(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL,Path-Entity Aligned Relational Learning", "fundacional,evaluacion")])
    _goldens(monkeypatch, ids=(1,))
    CL.build(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash, corpus_capa) VALUES (?,?,?,?)",
                     ("x.pdf", "Nuevo de evaluacion", "h9", "evaluacion"))
        conn.execute("INSERT INTO documents (path, title, paper_hash, corpus_capa) VALUES (?,?,?,?)",
                     ("y.pdf", "Nuevo extendido", "h10", "extendido"))
    r = CL.check(db)
    assert any("doc 2" in p and "evaluacion" in p and "sin declarar" in p for p in r["fatal"]), r
    assert any("doc 3" in p for p in r["avisos"]) and not any("doc 3" in p for p in r["fatal"]), r


def test_build_reparte_lotes_por_diff(tmp_path, monkeypatch):
    db, _ = _mkdb(tmp_path, monkeypatch, [
        ("PEARL: Path-Entity Aligned Relational Learning", "fundacional,evaluacion"),
        ("Paper extendido", "extendido"),
    ])
    _goldens(monkeypatch, ids=(1,))
    CL.build(db, nombre="corpus-previo")
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash, corpus_capa) VALUES (?,?,?,?)",
                     ("n.pdf", "Lote 1", "hn", "extendido"))
    lock = CL.build(db, nombre="lote-1")
    lotes = {l["lote"]: l for l in lock["lotes"]}
    assert [l["nombre"] for l in lock["lotes"]] == ["corpus-previo", "lote-1"]
    assert set(lotes[0]["doc_ids"]) == {1, 2} and lotes[1]["doc_ids"] == [3]
    assert lock["docs"]["1"]["lote"] == 0 and lock["docs"]["3"]["lote"] == 1
    assert CL.check(db)["fatal"] == []
    # el lock persiste en disco con la estructura que espera el eval
    assert json.loads(CL.LOCK.read_text())["docs"]["3"]["lote"] == 1


def _fila(qid):
    return {"id": qid, "judge": 4, "judge_error": None, "unanswerable": False,
            "difficulty": "facil", "cite_precision": 1.0, "cite_coverage": 1.0,
            "answer_has_cite": True, "truncated": False, "fallback": False,
            "latency_s": 1, "judge_usage": {}, "agent_usage": {}, "abstained": None,
            "fabricated_value": None}


def test_eval_corta_antes_de_gastar_si_el_lock_cambia(tmp_path, monkeypatch):
    """El corpus cambió → la run no es comparable: se corta sin llamar al LLM."""
    monkeypatch.setattr(CL, "check", lambda *a, **k: {"fatal": ["doc 1 cambió el texto"],
                                                      "avisos": []})
    llamada = []
    monkeypatch.setattr(H, "run_one", lambda *a, **k: llamada.append(a))
    monkeypatch.setattr(sys, "argv", ["eval_end2end.py", "--ids", "pearl-b1",
                                      "--out", str(tmp_path / "r.json")])
    with pytest.raises(SystemExit, match="CORPUS_LOCK"):
        H.main()
    assert llamada == []


def test_eval_registra_capas_y_estado_del_lock_en_meta(tmp_path, monkeypatch):
    rp = tmp_path / "r.json"
    monkeypatch.setattr(H, "run_one", lambda q, turns, **kw: _fila(q["id"]))
    monkeypatch.setattr(H, "_wrap_generate", lambda retries, gen: gen)
    monkeypatch.setenv("BIBLIOTECARIO_CAPAS", "fundacional")  # se registra el valor real
    monkeypatch.setattr(sys, "argv", ["eval_end2end.py", "--ids", "pearl-b1",
                                      "--capas", "evaluacion", "--sin-lock",
                                      "--out", str(rp)])
    H.main()
    meta = json.loads(rp.read_text())["meta"]
    assert meta["corpus"] == {"capas": "evaluacion", "lock_verificado": False}
    assert os.environ["BIBLIOTECARIO_CAPAS"] == "evaluacion"


def test_eval_rechaza_capas_desconocidas(tmp_path, monkeypatch):
    monkeypatch.delenv("BIBLIOTECARIO_CAPAS", raising=False)
    monkeypatch.setattr(sys, "argv", ["eval_end2end.py", "--ids", "pearl-b1",
                                      "--capas", "evaluacioon",
                                      "--out", str(tmp_path / "r.json")])
    with pytest.raises(SystemExit):
        H.main()
    assert "BIBLIOTECARIO_CAPAS" not in os.environ


def test_eval_sin_capas_no_filtra(tmp_path, monkeypatch):
    """El default sigue siendo corpus completo: filtrar cambia la línea base."""
    rp = tmp_path / "r.json"
    monkeypatch.delenv("BIBLIOTECARIO_CAPAS", raising=False)
    monkeypatch.setattr(H, "run_one", lambda q, turns, **kw: _fila(q["id"]))
    monkeypatch.setattr(H, "_wrap_generate", lambda retries, gen: gen)
    monkeypatch.setattr(sys, "argv", ["eval_end2end.py", "--ids", "pearl-b1",
                                      "--sin-lock", "--out", str(rp)])
    H.main()
    meta = json.loads(rp.read_text())["meta"]
    assert meta["corpus"]["capas"] is None and meta["corpus"]["lock_verificado"] is False
    assert "BIBLIOTECARIO_CAPAS" not in os.environ


# Títulos reales de la BD (se detectan por título, no por doc_id). El fallo que
# motivó la tupla: el título extraído usa "Título: subtítulo" y el nombre de
# fichero usa "Título, subtítulo" — con una sola subcadena los cinco dejaban de
# ser fundacionales y salían como evaluacion,extendido.
TITULOS_REALES = [
    "PEARL: Path-Entity Aligned Relational Learning with Contextual Subgraphs for Inductive Knowledge Graph Completion",
    "Procedural Graphs: Self-Evolving Execution Structures for LLM Agents",
    "Task-CoEvolve: Efficient Harness Optimization via Adaptive Validation Task Selection",
    "The Optimizer Is the Agent: Reasoning-Driven Search across Prompts, Programs, and ML Workflows",
    "WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution",
]


def test_titulos_reales_se_detectan_fundacionales():
    for i, t in enumerate(TITULOS_REALES, start=1):
        assert CL._capa_de(t, {1, 2, 3, 4, 5}, i) == "fundacional,evaluacion", t
    # ninguno de los otros 20 títulos del corpus es fundacional
    for t in ("Self-Evolving Harness on Multiple Tasks with the Agent as Its Own Optimizer",
              "RRSI: Regularized Recursive Self-Improvement of Agent Harnesses",
              "Recurrent Harness for Agentic Continual Learning"):
        assert CL._capa_de(t, {11}, 11) == "evaluacion,extendido"
        assert CL._capa_de(t, set(), 11) == "extendido"
