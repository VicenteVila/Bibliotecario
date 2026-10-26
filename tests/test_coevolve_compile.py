"""Compilador 0-token: estudios -> memoria, grafo -> skills y recall léxico."""
from __future__ import annotations

import numpy as np
import pytest

from bibliotecario.coevolve import compiler as C
from bibliotecario.coevolve import task_pool as TP
from bibliotecario.core import storage
from bibliotecario.knowledge import procedural as P
from bibliotecario.memory import memory_tree as MT


@pytest.fixture(autouse=True)
def _tmpdb(tmp_path, monkeypatch):
    db = tmp_path / "compile.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    return db


def _study(slug: str, title: str, body: str, kind: str = "study") -> None:
    with storage.get_conn() as conn:
        conn.execute(
            "INSERT INTO wiki_pages (slug, title, body, kind) VALUES (?,?,?,?)",
            (slug, title, body, kind))


def _count(table: str, where: str = "") -> int:
    with storage.get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) c FROM {table} {where}").fetchone()["c"]


def test_estudios_dry_run_apply_e_idempotencia():
    _study("estudio-1", "Uno", "cuerpo uno")
    _study("estudio-2", "Dos", "cuerpo dos")
    _study("raw-1", "Crudo", "no compilar", kind="raw")

    dry = C.compile_studies()
    assert dry == {"studies": 2, "existing": 0, "created": 2,
                   "created_slugs": ["estudio-1", "estudio-2"],
                   "updated": 0, "updated_slugs": [], "apply": False}
    assert _count("memory_items") == 0

    first = C.compile_studies(apply=True)
    assert first["created"] == 2
    assert _count("memory_items") == 2
    with storage.get_conn() as conn:
        contents = [r["content"] for r in conn.execute(
            "SELECT content FROM memory_items ORDER BY id").fetchall()]
    assert contents[0].startswith("[study:estudio-1] Uno")
    assert contents[1].startswith("[study:estudio-2] Dos")

    second = C.compile_studies(apply=True)
    assert second["created"] == 0 and second["existing"] == 2
    assert _count("memory_items") == 2


def test_estudio_actualizado_se_recompila_sin_duplicar():
    _study("estudio-1", "Uno", "cuerpo viejo")
    C.compile_studies(apply=True)
    with storage.get_conn() as conn:
        conn.execute("UPDATE wiki_pages SET body='cuerpo nuevo' WHERE slug='estudio-1'")

    dry = C.compile_studies()
    assert dry["existing"] == 1 and dry["updated"] == 1 and dry["created"] == 0
    with storage.get_conn() as conn:
        assert "cuerpo viejo" in conn.execute(
            "SELECT content FROM memory_items").fetchone()["content"]

    out = C.compile_studies(apply=True)
    assert out["updated"] == 1 and out["created"] == 0
    assert _count("memory_items") == 1
    with storage.get_conn() as conn:
        content = conn.execute("SELECT content FROM memory_items").fetchone()["content"]
    assert "cuerpo nuevo" in content and "cuerpo viejo" not in content

    again = C.compile_studies(apply=True)
    assert again["updated"] == 0 and again["created"] == 0


def test_skills_desde_grafo_dry_run_apply_e_idempotencia():
    P.register_procedure("A", technique="Técnica X")
    P.register_procedure("B", technique="Técnica X")
    P.link("A", "triggers", "B")

    dry = C.compile_skills()
    assert dry["techniques"] == 1 and dry["created"] == 1
    assert dry["total_tech_skills"] == 0
    assert _count("skills") == 0

    first = C.compile_skills(apply=True)
    assert first["created"] == 1 and first["total_tech_skills"] == 1
    with storage.get_conn() as conn:
        row = conn.execute("SELECT * FROM skills WHERE name=?",
                           ("tech_skill_tecnica_x",)).fetchone()
    assert row is not None
    assert "trigger: Técnica X" in row["skill_md"]
    assert "A -> B" in row["skill_md"]
    assert _count("wiki_pages", "WHERE kind='skill'") == 1

    second = C.compile_skills(apply=True)
    assert second["created"] == 0 and second["updated"] == 0
    assert second["total_tech_skills"] == 1


def test_skill_compilada_se_rehidrata_en_la_capa():
    from bibliotecario.harness.layers import ProceduralSkillLayer

    P.register_procedure("A", technique="Técnica X")
    P.register_procedure("B", technique="Técnica X")
    P.link("A", "triggers", "B")
    C.compile_skills(apply=True)

    layer = ProceduralSkillLayer()
    assert layer.load_from_db() == 1
    hits = layer.retrieve_skills("Técnica X", {})
    assert [s.name for s in hits] == ["tech_skill_tecnica_x"]


def test_compilador_y_snapshot_no_llaman_al_llm(monkeypatch):
    from bibliotecario.agent import tools as T

    _study("estudio-1", "Uno", "cuerpo uno")
    P.register_procedure("A", technique="Técnica X")
    monkeypatch.setattr(T, "generate", lambda *a, **k: pytest.fail("no debe llamar al LLM"))

    out = C.run(apply=True)
    assert out["llm_tokens"] == 0
    assert out["studies"]["created"] == 1
    assert out["skills"]["created"] == 1
    assert out["coevolve"]["tasks"] == 0


def test_recall_text_usa_memoria_sin_embedding():
    MT.add("Task-CoEvolve usa muestreo ponderado por varianza", level="L2")
    MT.add("otra nota sobre ingestión", level="L2")

    hits = MT.recall_text("muestreo varianza")
    assert hits and "muestreo ponderado" in hits[0]["content"]
    assert MT.recall_text("ornitorrinco") == []
    assert MT.recall(np.zeros(4, dtype="float32")) == []


def test_tool_recall_memory_expuesta():
    from bibliotecario.agent import tools as T

    MT.add("Task-CoEvolve usa muestreo ponderado por varianza", level="L2")
    assert "recall_memory" in T.TOOLS
    out = T.recall_memory("muestreo varianza")
    assert out["count"] == 1
    assert "Task-CoEvolve" in out["hits"][0]["content"]


def test_snapshot_coevolve_es_read_only_y_determinista():
    t1 = TP.add_task("a", "qa")
    t2 = TP.add_task("b", "qa")
    TP.record_outcome(t1, True)
    TP.record_outcome(t1, False)
    TP.record_outcome(t2, True)

    snap = C.snapshot(rho=0.5, seed=7)
    assert snap["tasks"] == 2 and snap["outcomes"] == 3
    assert snap["pbar_ones"] == 1 and snap["pbar_zeros"] == 0
    assert len(snap["sample"]) == 1
    assert C.snapshot(rho=0.5, seed=7)["sample"] == snap["sample"]
    with pytest.raises(ValueError):
        C.snapshot(rho=0)
