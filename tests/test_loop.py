"""Loop end-to-end con LLM simulado: verifica maquinaria sin gastar cuota."""
import json

from bibliotecario.agent import loop as LOOP
from bibliotecario.core import storage


def test_loop_end_to_end_scripted(tmp_path, monkeypatch):
    db = tmp_path / "loop.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Test", "abc123"))

    script = [
        'Busco.\n```json\n{"tool": "get_status", "args": {}}\n```',
        "Respuesta final: hay 1 documento.",
    ]
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: script.pop(0) if script else "Fin.")

    from bibliotecario.harness import runtime as RT
    monkeypatch.setattr(RT, "_harness", None)
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)

    r = LOOP.run("¿cuántos documentos hay?", max_turns=5)
    assert r["answer"].startswith("Respuesta final")
    assert len(r["evidence"]) == 1
    with storage.get_conn(db) as conn:
        runs = conn.execute("SELECT COUNT(*) c FROM harness_runs").fetchone()["c"]
        lessons = conn.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"]
    assert runs == 1 and lessons == 1
    assert json.dumps(r["evidence"], ensure_ascii=False)


def test_loop_tool_invalida_recupera(tmp_path, monkeypatch):
    db = tmp_path / "loop2.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    script = [
        '```json\n{"tool": "no_existe", "args": {}}\n```',
        "Listo tras error.",
    ]
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: script.pop(0) if script else "Fin.")
    from bibliotecario.harness import runtime as RT
    monkeypatch.setattr(RT, "_harness", None)
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)
    r = LOOP.run("q", max_turns=4)
    assert r["answer"] == "Listo tras error."
