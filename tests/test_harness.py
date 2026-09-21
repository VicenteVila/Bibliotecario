
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
    n = reg.evolve_from_failures([{"trigger": "timeout X", "field": "last_action.status", "intervention": "retry"},
                                  {"trigger": "timeout X", "field": "last_action.status", "intervention": "retry"}])
    assert n == 2 and reg.stats()["total"] == before + 2


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
