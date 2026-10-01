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
        # El borrador en prosa ya no se acepta crudo: entra al cierre forzado,
        # que hace una llamada mas para redactar con la evidencia en la mano.
        "Ya tengo la respuesta: hay 1 documento.",
        "Respuesta final: hay 1 documento [1:0].",
    ]
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: script.pop(0) if script else "Fin.")

    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
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
        # Tercera llamada: el cierre forzado sobre el borrador en prosa.
        "Listo tras error [1:0].",
    ]
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: script.pop(0) if script else "Fin.")
    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)
    r = LOOP.run("q", max_turns=4)
    assert r["answer"] == "Listo tras error [1:0]."


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
    RT.reset_harness()
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


def _harness_limpio(monkeypatch):
    """Deja el harness y los PF en blanco: sin lesson learned entre pruebas."""
    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)


def test_consulta_distinta_no_cuenta_como_estancamiento(tmp_path, monkeypatch):
    """Queries distintas son progreso: el aviso de estancamiento no debe disparar.

    call_sig usaba sorted(args), que solo ordena las claves: toda llamada a
    search_papers daba la misma firma y flat subia aunque el modelo cambiara de
    query. Al tocar flat>=3, state.py avisaba "responde ya" y el modelo acortaba
    la salida, que es justo la via rapida que puntua 2.273 frente a 4.551.
    """
    db = tmp_path / "loop_callsig.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Test", "abc123"))

    queries = ["random resample evaluation budget",
               "statistical procedure small validation splits",
               "co-dependent improvements IMG-100",
               "evaluation budget rho 20% standard deviations"]
    espias = []

    def fake_gen(prompt, max_tokens=512, retries=2):
        espias.append(prompt)
        if len(espias) <= len(queries):
            q = queries[len(espias) - 1]
            return json.dumps({"tool": "search_papers", "args": {"query": q, "top_k": 5}})
        return "Respuesta final: cerrado [1:0]."

    monkeypatch.setattr(LOOP, "generate", fake_gen)
    _harness_limpio(monkeypatch)
    LOOP.run("¿qué dice el paper?", max_turns=len(queries) + 1)

    assert len(espias) >= len(queries)
    assert not any("AVISO ESTANCAMIENTO" in p for p in espias), (
        "una consulta distinta se conto como estancamiento")


def test_misma_consulta_si_cuenta_como_estancamiento(tmp_path, monkeypatch):
    """El aviso sigue apareciendo cuando la llamada es realmente identica."""
    db = tmp_path / "loop_mismo.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Test", "abc123"))

    espias = []

    def fake_gen(prompt, max_tokens=512, retries=2):
        espias.append(prompt)
        return json.dumps({"tool": "search_papers",
                           "args": {"query": "misma query", "top_k": 5}})

    monkeypatch.setattr(LOOP, "generate", fake_gen)
    _harness_limpio(monkeypatch)
    LOOP.run("¿qué dice el paper?", max_turns=5)
    assert any("AVISO ESTANCAMIENTO" in p for p in espias), (
        "repetir la misma consulta debe seguir avisando")


def test_respuesta_en_prosa_pasa_por_el_cierre_forzado(tmp_path, monkeypatch):
    """Un 'ya tengo la respuesta' en prosa no debe saltarse _final_answer.

    Antes se aceptaba crudo y hacia break: sin barrido profundo y sin exigir
    cita. Esa via rapida media 2.273 contra 4.551 de la que llega al cierre.
    """
    db = tmp_path / "loop_prosa.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Test", "abc123"))

    monkeypatch.setattr(LOOP, "generate",
                        lambda *a, **k: "Tengo la respuesta: 96% de ahorro.")
    cerrados = {"n": 0}

    def cierre(question, best, evidence, flat, retries=1):
        cerrados["n"] += 1
        return "El ahorro es del 96% [1:0]."

    monkeypatch.setattr(LOOP, "_final_answer", cierre)
    _harness_limpio(monkeypatch)
    r = LOOP.run("¿cuánto ahorra?", max_turns=4)
    assert cerrados["n"] == 1, "la prosa tiene que pasar por _final_answer"
    assert r["answer"] == "El ahorro es del 96% [1:0]."
