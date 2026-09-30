"""Loop end-to-end con LLM simulado: verifica maquinaria sin gastar cuota."""
import json

import pytest

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


def test_parser_tolera_json_suelto_y_malformado():
    # JSON sin vallas y con prefijo de razonamiento (Nemotron/gpt-oss)
    assert LOOP.parse_tool_call('Vamos a buscar.\n{"tool": "search_papers", "args": {"query": "x"}}') \
        == ("search_papers", {"query": "x"})
    # args sin clave "tool" → llamada malformada ("")
    assert LOOP.parse_tool_call('razonamiento...\n{"query": "x", "top_k": 5}')[0] == ""
    # prosa normal → no es llamada
    assert LOOP.parse_tool_call("La respuesta es 42.") == (None, {})


def test_presupuesto_agotado_sintetiza(tmp_path, monkeypatch):
    """Si se agotan turnos con tool calls, el cierre produce prosa, no JSON crudo."""
    db = tmp_path / "loop3.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Test", "abc123"))
    calls = {"n": 0}

    def fake_gen(prompt, max_tokens=512, retries=2):
        calls["n"] += 1
        if calls["n"] <= 2:
            return '```json\n{"tool": "get_status", "args": {}}\n```'
        return "Síntesis final en prosa con cita [1:0]."

    monkeypatch.setattr(LOOP, "generate", fake_gen)
    from bibliotecario.harness import runtime as RT
    monkeypatch.setattr(RT, "_harness", None)
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)
    r = LOOP.run("q", max_turns=2)
    assert r["answer"] == "Síntesis final en prosa con cita [1:0]."
    assert not r["answer"].lstrip().startswith("(")


@pytest.mark.parametrize("text,expected", [
    # volcados: no son respuestas válidas y hay que reintentar el cierre
    ('{"tool": "search_papers", "args": {"query": "x", "top_k": 5}}', True),
    ('{"query": "x", "top_k": 5}', True),
    ('{"hits": [{"doc_id": 3, "chunk": 40, "text": "x"}]}', True),
    # JSON malformado (el modelo se cortó a media estructura)
    ('{"tool": "search_papers", "args": {"query": "ReASearch over", "top_k": 5": 5}}', True),
    # respuestas reales en prosa
    ("WikiSkill samples up to 8 traces per iteration [5:57].", False),
    ("ReASearch persists learning via lessons.md read on later runs.", False),
    ("A valid json {\"a\": 1} mentioned in prose.", False),
])
def test_toolish_detecta_volcajes_json(text, expected):
    """El cierre no debe devolver un volcado de tool como respuesta.

    Regresión de reas-1: el modelo emitted una llamada de tool truncada y el
    guardián la dejó pasar como respuesta, así que el judge marcaba la pregunta
    como fallida aunque el agente no hubiera dicho nada del tema.
    """
    from bibliotecario.agent.loop import _toolish
    assert _toolish(text) is expected
