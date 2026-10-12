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


DEEP_FALSO = ("[3:25] Task-CoEvolve\nRandom-Resample cuts cost by 96% but that is not "
              "efficiency, because uniform sampling also spends its budget on easier "
              "tasks that terminate quickly.\n"
              "[5:13] WikiSkill\nThe Inference Agent is restricted from accessing the "
              "Wiki Layer during training rollouts.")


def _prepara_verificacion(monkeypatch, respuestas):
    monkeypatch.setattr(LOOP, "VERIFY_CITATION", True)
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda *a, **k: DEEP_FALSO)
    cola = list(respuestas)
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: cola.pop(0))


def test_verificacion_reescribe_si_la_cita_no_alcanza(monkeypatch):
    _prepara_verificacion(monkeypatch, [
        "El ahorro es del 96% porque reparte mal [3:25].",
        "Correcto: uniform sampling gasta el presupuesto en tareas faciles [3:25].",
    ])
    out = LOOP._final_answer("¿por que no es eficiencia?", "", ["ev"], 0)
    assert out.startswith("Correcto: uniform sampling")
    assert "96%" not in out


def test_verificacion_conserva_original_si_el_verificador_dice_ok(monkeypatch):
    _prepara_verificacion(monkeypatch, [
        "El ahorro es del 96% [3:25].",
        "OK",
    ])
    assert LOOP._final_answer("q", "", ["ev"], 0) == "El ahorro es del 96% [3:25]."


def test_verificacion_rechaza_reescritura_con_cita_ajena(monkeypatch):
    _prepara_verificacion(monkeypatch, [
        "El ahorro es del 96% [3:25].",
        "Otra cosa distinta [9:99].",
    ])
    assert LOOP._final_answer("q", "", ["ev"], 0) == "El ahorro es del 96% [3:25]."


def test_verificacion_rechaza_reescritura_sin_cita(monkeypatch):
    _prepara_verificacion(monkeypatch, [
        "El ahorro es del 96% [3:25].",
        "Uniform sampling gasta en tareas faciles.",
    ])
    assert LOOP._final_answer("q", "", ["ev"], 0) == "El ahorro es del 96% [3:25]."


def test_verificacion_no_corre_si_la_cita_no_resuelve_en_el_barrido(monkeypatch):
    _prepara_verificacion(monkeypatch, ["Cosa con cita no indexada [7:7]."])
    assert LOOP._final_answer("q", "", ["ev"], 0) == "Cosa con cita no indexada [7:7]."


def test_verificacion_apagada_por_defecto(monkeypatch):
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda *a, **k: DEEP_FALSO)
    llamadas = []

    def gen(*a, **k):
        llamadas.append(a[0])
        return "El ahorro es del 96% [3:25]."

    monkeypatch.setattr(LOOP, "generate", gen)
    assert LOOP.VERIFY_CITATION is False
    LOOP._final_answer("q", "", ["ev"], 0)
    assert len(llamadas) == 1


def test_key_insights_no_lleva_la_pregunta(tmp_path, monkeypatch):
    """275 de 275 lecciones tenían `Q: <pregunta>` en key_insights.

    La columna no contenía insights, contenía la pregunta, y load_lessons la
    inyectaba en el prompt: en producción cada run veía las 5 últimas preguntas
    del corpus.
    """
    db = tmp_path / "li.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Doc", "h1"))

    script = ['```json\n{"tool": "get_status", "args": {}}\n```',
              "Ya está: hay 1 documento.",
              "Hay 1 documento [1:0]."]
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: script.pop(0) if script else "Fin.")
    guardada = {}
    monkeypatch.setattr(LOOP.REF, "save_lesson", lambda *a, **k: guardada.update(k))

    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)

    LOOP.run("¿cuántos documentos hay?", max_turns=5)

    assert guardada, "sin isolated=True debe escribir la lección"
    ki = guardada["key_insights"]
    assert "Q:" not in ki, f"el prefijo antiguo sigue ahí: {ki!r}"
    assert "documentos" not in ki, f"la pregunta se filtra: {ki!r}"
    assert "turnos" in ki, f"debe decir qué pasó, no qué se preguntó: {ki!r}"


def test_run_cierra_la_run_si_el_bucle_lanza(tmp_path, monkeypatch):
    """87 de 1121 runs se quedaron con finished_at NULL.

    La excepción se escapaba sin pasar por finish_run. Ahora va en finally.
    """
    db = tmp_path / "fin.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)

    def boom(*a, **k):
        raise RuntimeError("revienta aquí dentro")

    monkeypatch.setattr(LOOP, "generate", boom)

    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)

    with pytest.raises(RuntimeError, match="revienta"):
        LOOP.run("q", max_turns=3)

    with storage.get_conn(db) as conn:
        rows = conn.execute("SELECT finished_at FROM harness_runs").fetchall()
    assert len(rows) == 1
    assert rows[0]["finished_at"] is not None, "la run quedó huérfana"


def test_run_sin_iteraciones_no_escribe_turnos_negativos(tmp_path, monkeypatch):
    """turn=-1 antes del bucle: sin eso, max_turns=0 reventaría con NameError."""
    db = tmp_path / "nt.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    monkeypatch.setattr(LOOP, "generate", lambda *a, **k: "Fin.")
    monkeypatch.setattr(LOOP.REF, "save_lesson", lambda *a, **k: None)

    from bibliotecario.harness import runtime as RT
    RT.reset_harness()
    import bibliotecario.harness.pfs as PFS
    monkeypatch.setattr(PFS, "_registry", None)

    r = LOOP.run("q", max_turns=0)
    assert r["turns"] == 0
    with storage.get_conn(db) as conn:
        row = conn.execute("SELECT metadata FROM harness_runs").fetchone()
    assert json.loads(row["metadata"])["turns"] == 0


def test_run_blueprint_p1_prima_la_tool_sobre_el_loop(monkeypatch):
    """P1' (§5): el loop reúne evidencia, pero el blueprint lo escribe la tool.

    Regresión: enrutar `build_blueprint` al loop bajaría el tope de 1500 tokens
    al `max_tokens=1024` con el que `run()` genera **cada turno** (§5.5). Aquí
    se comprueba que la evidencia del loop llega a la tool y que el blueprint
    devuelto es el de la tool, no el del turno.
    """
    from bibliotecario.agent import tools as T

    seen: dict = {}
    monkeypatch.setattr(
        LOOP, "run",
        lambda *a, **k: {"answer": "no usado", "turns": 3,
                         "evidence": ["search_papers(q): hallazgo"], "run_id": "r1"},
    )

    def fake_build(technique, goal, extra_source=""):
        seen["extra"] = extra_source
        return {"technique": technique, "goal": goal, "procedures": ["p"],
                "blueprint": "bp de la tool"}

    monkeypatch.setattr(T, "build_blueprint", fake_build)

    out = LOOP.run_blueprint("Task-CoEvolve", "validar release")

    assert out["blueprint"] == "bp de la tool"
    assert out["loop_turns"] == 3
    assert "search_papers" in seen["extra"]


def test_run_blueprint_sin_evidence_del_loop_sigue_escribiendo(monkeypatch):
    """Aunque el loop no traiga nada, la tool escribe con su propio presupuesto."""
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(
        LOOP, "run",
        lambda *a, **k: {"answer": "", "turns": 0, "evidence": [], "run_id": "r2"},
    )
    monkeypatch.setattr(
        T, "build_blueprint",
        lambda technique, goal, extra_source="": {"blueprint": "ok", "procedures": []},
    )
    assert LOOP.run_blueprint("Task-CoEvolve", "objetivo")["blueprint"] == "ok"
