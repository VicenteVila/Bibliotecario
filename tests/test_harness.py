import json

from bibliotecario.agent.loop import parse_tool_call
from bibliotecario.harness.pfs import get_pf_registry


def test_parse_tool_call_ok():
    name, args = parse_tool_call('Pienso.\n```json\n{"tool": "get_status", "args": {}}\n```')
    assert name == "get_status" and args == {}


def test_parse_tool_call_none():
    name, _ = parse_tool_call("Respuesta final sin bloque.")
    assert name is None


def test_parse_tool_call_unknown():
    name, _ = parse_tool_call('```json\n{"tool": "inexistente", "args": {}}\n```')
    assert name is None


def test_pf_flat_y_nested():
    reg = get_pf_registry()
    flat = {"last_action.status": "error: timeout", "attempt_count": 1, "max_attempts": 3}
    nested = {"last_action": {"status": "failure"}, "attempt_count": 2, "max_attempts": 3}
    assert any(p.name == "retry_on_failure" for p in reg.find_matching(flat))
    assert any(p.name == "retry_on_failure" for p in reg.find_matching(nested))
    res = reg.execute_matching(flat)
    retry = [r for r in res if r["pf"] == "retry_on_failure"]
    assert retry and retry[0]["action"] in ("retry", "escalate")


def test_pf_fallback_no_ollama():
    reg = get_pf_registry()
    res = reg.execute_matching({"last_action": {"status": "rate_limit"}})
    fb = [r for r in res if r["pf"] == "fallback_on_exhaustion"]
    assert fb and "ollama" not in str(fb[0]).lower()


def test_pf_evolve_unique_names():
    reg = get_pf_registry()
    before = reg.stats()["total"]
    # Hito 4: devuelve los nombres creados (el caller los persiste en harness_edits)
    names = reg.evolve_from_failures([{"trigger": "timeout X", "field": "last_action.status", "intervention": "retry"},
                                      {"trigger": "timeout X", "field": "last_action.status", "intervention": "retry"}])
    assert len(names) == 2 and names[0] != names[1]
    assert all(n.startswith("auto_pf_") for n in names)
    assert reg.stats()["total"] == before + 2


def test_harness_run_persist(tmp_path, monkeypatch):
    from bibliotecario.core import storage
    from bibliotecario.harness.runtime import RuntimeHarness
    db = tmp_path / "h.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    h = RuntimeHarness()
    rid = h.start_run({"q": "x"})
    h.finish_run(rid, 0.8, {"turns": 2})
    with storage.get_conn(db) as conn:
        row = conn.execute("SELECT score FROM harness_runs WHERE id=?", (rid,)).fetchone()
    assert row["score"] == 0.8


def test_agent_tools_status(tmp_path, monkeypatch):
    from bibliotecario.agent.tools import get_status
    from bibliotecario.core import storage
    db = tmp_path / "s.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    st = get_status()
    assert st["documents"] == 0 and "nodes" in st


def test_finish_run_fusiona_metadata_en_las_de_sobre_escribirla(tmp_path, monkeypatch):
    """start_run guarda la pregunta; finish_run no puede borrarla.

    Antes el UPDATE pisaba toda la clave, así que la `question` desaparecía y una
    fila de harness_runs era anónima: score sin saber qué pregunta lo produjo.
    """
    from bibliotecario.core import storage
    from bibliotecario.harness.runtime import RuntimeHarness

    db = tmp_path / "m.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    h = RuntimeHarness()
    rid = h.start_run({"question": "¿cuántos documentos hay?"})
    h.finish_run(rid, None, {"turns": 3, "tools": 2})
    h.record_score(rid, 0.75, {"eval_id": "pearl-b1"})

    with storage.get_conn(db) as conn:
        row = conn.execute("SELECT score, metadata FROM harness_runs WHERE id=?",
                           (rid,)).fetchone()
    meta = json.loads(row["metadata"])
    assert row["score"] == 0.75
    # Las tres claves de tres fases distintas conviven.
    assert meta["question"] == "¿cuántos documentos hay?"
    assert meta["turns"] == 3 and meta["tools"] == 2
    assert meta["eval_id"] == "pearl-b1"


def test_record_score_desconocido_no_escribe(tmp_path, monkeypatch):
    """Devuelve False en vez de inventar una fila."""
    from bibliotecario.core import storage
    from bibliotecario.harness.runtime import RuntimeHarness

    db = tmp_path / "n.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    h = RuntimeHarness()
    assert h.record_score("no-existe", 1.0) is False
    with storage.get_conn(db) as conn:
        assert conn.execute("SELECT COUNT(*) c FROM harness_runs").fetchone()["c"] == 0


def test_record_score_soporta_metadata_rota(tmp_path, monkeypatch):
    """Un JSON corrupto no debe tumbar el UPDATE del score."""
    from bibliotecario.core import storage
    from bibliotecario.harness.runtime import RuntimeHarness

    db = tmp_path / "r.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    h = RuntimeHarness()
    rid = h.start_run()
    with storage.get_conn(db) as conn:
        conn.execute("UPDATE harness_runs SET metadata='no-es-json' WHERE id=?", (rid,))
    assert h.record_score(rid, 1.0, {"eval_id": "x"}) is True
    with storage.get_conn(db) as conn:
        row = conn.execute("SELECT score, metadata FROM harness_runs WHERE id=?",
                           (rid,)).fetchone()
    assert row["score"] == 1.0
    assert json.loads(row["metadata"])["eval_id"] == "x"
