import numpy as np
import pytest

from bibliotecario.core import storage
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import pearl as PEARL
from bibliotecario.knowledge import procedural as P
from bibliotecario.memory import memory_tree as MT


@pytest.fixture(autouse=True)
def _tmpdb(tmp_path, monkeypatch):
    db = tmp_path / "g.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    return db


def test_upsert_node_idempotente():
    a = G.upsert_node("technique", "Task-CoEvolve")
    b = G.upsert_node("technique", "Task-CoEvolve")
    assert a == b
    assert G.find_nodes("CoEvolve")[0].label == "Task-CoEvolve"


def test_add_edge_idempotente_y_vecinos():
    s = G.upsert_node("procedure", "variance-weighted sampling")
    d = G.upsert_node("procedure", "full-set estimation")
    e1 = G.add_edge(s, d, "triggers", "procedural")
    e2 = G.add_edge(s, d, "triggers", "procedural", weight=0.7)
    assert e1 == e2
    neigh = G.neighbors(s)
    assert len(neigh) == 1 and neigh[0][1].label == "full-set estimation"


def test_procedural_registry():
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve")
    P.link("variance-weighted sampling", "triggers", "Hájek estimation")
    procs = P.list_procedures(technique="Task-CoEvolve")
    assert any(p.label == "Hájek estimation" for p in procs)
    with pytest.raises(AssertionError):
        P.link("a", "relacion_invalida", "b")


def test_build_blueprint_tecnica_inexistente_no_tira_el_grafo(monkeypatch):
    """N1 (§3.4): no se escribe blueprint de una técnica sin respaldo.

    Regresión: el fallback `or P.list_procedures()` metía **todas** las
    técnicas en el prompt. H5 lo tapó porque el modelo se negó por su cuenta,
    una vez — no es una garantía. Aquí se niega el código.
    """
    from bibliotecario.agent import tools as T
    P.register_procedure("variance-weighted sampling", technique="Task-CoEvolve")
    monkeypatch.setattr(T, "generate", lambda *a, **k: pytest.fail("no debe llamar al LLM"))
    out = T.build_blueprint("Tecnica Que No Existe", "objetivo")
    assert out["procedures"] == []
    assert "no existe" in out["blueprint"]


def test_build_blueprint_tecnica_conocida_usa_sus_procedimientos(monkeypatch):
    from bibliotecario.agent import tools as T
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve")
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    monkeypatch.setattr(T, "generate", lambda *a, **k: "blueprint de prueba")
    out = T.build_blueprint("Task-CoEvolve", "objetivo")
    assert out["procedures"] == ["Hájek estimation"]


def test_build_blueprint_sin_fuente_no_finge_cita(monkeypatch):
    """R1-R7 exigen el texto de la fuente; sin chunks no hay nada que citar.

    Se declara en vez de escribir un blueprint que parezca fundamentado.
    """
    from bibliotecario.agent import tools as T
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve")
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    monkeypatch.setattr(T, "generate", lambda *a, **k: pytest.fail("no debe llamar al LLM"))
    out = T.build_blueprint("Task-CoEvolve", "objetivo")
    assert "sin fuente" in out["blueprint"]


def test_build_blueprint_prompt_lleva_fuente_y_reglas(tmp_path, monkeypatch):
    """P2: el prompt tiene que llevar el texto de la fuente y R1-R7, o las
    reglas son papel mojado — sin texto no se puede decir de donde sale nada.
    """
    from bibliotecario.agent import tools as T
    db = tmp_path / "p2.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper P2", "hp2"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "Task-CoEvolve: Miyai et al. (2025). varianza ponderada.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="Task-CoEvolve", doc_id=1)
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    seen: list[str] = []
    monkeypatch.setattr(T, "generate", lambda prompt, **k: seen.append(prompt) or "ok")

    out = T.build_blueprint("Task-CoEvolve", "objetivo")

    assert out["doc_id"] == 1
    assert seen, "debe llamar al LLM"
    prompt = seen[0]
    assert "Miyai et al." in prompt          # el texto de la fuente va dentro
    for rule in ("R1.", "R2.", "R3.", "R4.", "R5.", "R6.", "R7."):
        assert rule in prompt, f"falta {rule}"


def test_prompt_r6_es_en_linea_y_r1_es_suelo(tmp_path, monkeypatch):
    """P4: la marca de propuesta tiene que ir JUNTO a la afirmacion, o no sirve.

    Motivo medido: en Procedural Graphs r0 el modelo ya escribia
    «Propuesta del blueprint» pero en otra linea, y el juez no lo acreditaba —
    8 acusaciones que al re-puntuar quedaron en 1. Si la regla no esta en el
    prompt con esa exigencia, el modelo repite el mismo fallo.
    """
    from bibliotecario.agent import tools as T
    db = tmp_path / "r6.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hr6"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="X", doc_id=1)
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    seen: list[str] = []
    monkeypatch.setattr(T, "generate", lambda prompt, **k: seen.append(prompt) or "ok")

    T.build_blueprint("X", "objetivo")
    prompt = seen[0]

    lineas = prompt.split(chr(10))

    def bloque(regla: str) -> str:
        """R1 es multilínea desde la dec. 11 (la plantilla ocupa varias
        líneas): hay que tomar la continuación, no solo la primera."""
        out, dentro = [], False
        for l in lineas:
            if l.startswith(regla + "."):
                dentro = True
                out.append(l)
            elif dentro and l.startswith((" ", "\t")):
                out.append(l)
            elif dentro:
                break
        return chr(10).join(out)

    r4, r6, r1 = bloque("R4"), bloque("R6"), bloque("R1")
    assert "misma l" in r4, "R4 debe permitir el puente solo con marca junto a la frase"
    assert "misma l" in r6, "R6 debe exigir la marca en la propia frase"
    assert "suelo" in r1, "R1 debe declararse suelo: sin ancla no salva R6"


def test_build_blueprint_verified_limpio_no_reescribe(tmp_path, monkeypatch):
    """P3: si la atribución verifica, no se paga un segundo generate()."""
    from bibliotecario.agent import tools as T
    db = tmp_path / "v1.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hv1"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection over episodes.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="X", doc_id=1)
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    calls = []
    monkeypatch.setattr(T, "generate", lambda prompt, **k:
                        calls.append(prompt) or "usa variance-weighted task selection. [doc:1:0]")

    out = T.build_blueprint_verified("X", "objetivo")

    assert out["verificado"] is True
    assert out["violaciones"] == []
    assert len(calls) == 1, "limpio: no debe haber reescritura"


def test_build_blueprint_verified_reescribe_si_fabrica(tmp_path, monkeypatch):
    """P3: un módulo inventado provoca una reescritura con la violación concreta."""
    from bibliotecario.agent import tools as T
    db = tmp_path / "v2.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hv2"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection over episodes.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="X", doc_id=1)
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    seen: list[str] = []
    answers = iter(["usa AdaptiveHarnessEngine. [doc:1:0]",
                    "usa variance-weighted task selection. [doc:1:0]"])
    monkeypatch.setattr(T, "generate", lambda prompt, **k:
                        seen.append(prompt) or next(answers))

    out = T.build_blueprint_verified("X", "objetivo")

    assert out["reescrituras"] == 1
    assert out["verificado"] is True
    assert len(seen) == 2
    assert "AdaptiveHarnessEngine" in seen[1], "la reescritura debe nombrar el fallo"
    assert "1:0" in seen[1]


def test_build_blueprint_verified_sin_punteros_no_finge_verificado(tmp_path, monkeypatch):
    """Un blueprint sin citas no está 'verificado': no hay nada que comprobar.
    Marcarlo como limpio sería mentir con el mismo número (medido en una run
    real de Task-CoEvolve: verificado=True con 0 citas).
    """
    from bibliotecario.agent import tools as T
    db = tmp_path / "v3.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hv3"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection over episodes.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="X", doc_id=1)
    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    monkeypatch.setattr(T, "generate", lambda prompt, **k: "usa variance-weighted task selection.")

    out = T.build_blueprint_verified("X", "objetivo")

    assert out["verificado"] is None
    assert out["sin_punteros"] is True
    assert out["violaciones"] == []


def test_verify_and_mark_no_destruye_el_blueprint(tmp_path, monkeypatch):
    """P3 en modo informe: marca y NO reescribe.

    Motivo medido: la reescritura del brazo D empeoró las 3 runs que tocó,
    perdiendo la bibliografía y los silencios (§5.8.3). Este modo no debe
    llamar al LLM ni alterar el texto.
    """
    from bibliotecario.agent import tools as T
    db = tmp_path / "m1.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hm1"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection over episodes.", b"\x00"))
    monkeypatch.setattr(T, "generate", lambda *a, **k: pytest.fail("no debe llamar al LLM"))
    original = "usa AdaptiveHarnessEngine. [doc:1:0]"

    out = T.verify_and_mark({"blueprint": original, "doc_id": 1})

    assert out["blueprint"] == original, "no debe reescribir"
    assert out["verificado"] is False
    assert out["violaciones"][0]["termino"] == "AdaptiveHarnessEngine"
    assert out["reescrituras"] == 0


def test_verify_and_mark_ve_huerfanas_sin_puntero(tmp_path, monkeypatch):
    """Hito 5 (hallazgo 26, modo A): el informe deja de fingir limpieza.

    ReASearch salió `verificado=True` con 0 violaciones y el juez lo suspendió
    por inventar módulos sin puntero: `check_attributions` no los veía. Ahora
    las huérfanas entran en `violaciones` — también cuando no hay ningún
    puntero que comprobar — y el texto sigue intacto, sin llamar al LLM.
    """
    from bibliotecario.agent import tools as T
    db = tmp_path / "m2.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "P", "hm2"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "variance-weighted task selection over episodes.", b"\x00"))
    monkeypatch.setattr(T, "generate", lambda *a, **k: pytest.fail("no debe llamar al LLM"))
    original = ("usa AdaptiveHarnessEngine. [doc:1:0]\n"
                "El FailureVsSuccessRefiner refina el bucle de recompensa.")

    out = T.verify_and_mark({"blueprint": original, "doc_id": 1})

    assert out["blueprint"] == original, "no debe reescribir"
    assert out["verificado"] is False
    tipos = [v["tipo"] for v in out["violaciones"]]
    assert "termino_ausente" in tipos and "huerfana" in tipos
    assert out["reescrituras"] == 0

    # Sin ningún puntero el informe ya no devuelve «nada que comprobar» si
    # hay huérfanas: era justo la mentira del modo A.
    sin = T.verify_and_mark({"blueprint": "El FailureVsSuccessRefiner refina.",
                             "doc_id": None})
    assert sin["verificado"] is False
    assert sin["sin_punteros"] is True
    assert sin["violaciones"][0]["tipo"] == "huerfana"

    # Un blueprint sin punteros y sin huérfanas mantiene la lectura de siempre.
    limpio = T.verify_and_mark({"blueprint": "El agente valida cada paso.",
                                "doc_id": None})
    assert limpio["verificado"] is None
    assert limpio["violaciones"] == []


def test_pearl_pipeline_sin_llm(monkeypatch):
    monkeypatch.setattr(PEARL, "generate", lambda *a, **k: "")
    P.register_procedure("variance-weighted sampling", technique="Task-CoEvolve", doc_id=3)
    P.register_procedure("Hájek estimation", technique="Task-CoEvolve", doc_id=3)
    P.link("variance-weighted sampling", "triggers", "Hájek estimation")
    ev = PEARL.retrieve_evidence("variance-weighted sampling estimation")
    assert ev and ev[0]["score"] == 1.0
    assert ev[0]["doc_ids"] == [3]
    assert any(s["kind"] == "procedure" for s in ev[0]["steps"])


def test_memory_tree_recall_y_consolidate():
    rng = np.random.RandomState(0)
    v1 = rng.rand(8).astype("float32"); v1 /= np.linalg.norm(v1)
    v2 = rng.rand(8).astype("float32"); v2 /= np.linalg.norm(v2)
    MT.add("lección sobre sampling", v1, level="L1")
    MT.add("ruido ortogonal", v2)
    hits = MT.recall(v1, top_k=2)
    assert hits[0]["content"] == "lección sobre sampling"
    rep = MT.consolidate()
    assert rep["forgotten"] == 0


def test_search_expansion_vecinos(tmp_path, monkeypatch):
    """La expansión añade los chunks contiguos al hit principal, con score decaído."""
    from bibliotecario.memory import retriever as R
    db = tmp_path / "vecinos.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Doc Vecinos", "h1"))
        for i in range(5):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 if i == 2 else 0.0
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, f"chunk numero {i} con contexto", vec.tobytes()))
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])

    base = R.search("q", top_k=1)
    assert base[0]["chunk"] == 2 and "neighbour_of" not in base[0]
    hits = R.search_with_neighbours("q", top_k=1, window=1)
    assert {1, 2, 3} <= {h["chunk"] for h in hits}
    assert all(h["score"] <= base[0]["score"] for h in hits)
    assert any("neighbour_of" in h for h in hits)


def test_search_sin_expansion_si_window_cero(tmp_path, monkeypatch):
    from bibliotecario.memory import retriever as R
    db = tmp_path / "vecinos0.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Vacio", "h2"))
    assert R.search_with_neighbours("q", top_k=3, window=0) == []


def test_deep_sweep_cubre_apendice(tmp_path, monkeypatch):
    """El detalle específico está en un apéndice que el ranking no alcanza: el barrido debe verlo."""
    from bibliotecario.agent import tools as T
    db = tmp_path / "sweep.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Con Apendice", "h9"))
        for i in range(40):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 - i * 0.02  # el último chunk es el peor por denso
            txt = "texto general sin relacion " * 20
            if i == 30:
                # apéndice: sin solapamiento léxico con la query, solo alcanzable por cobertura
                txt = "Appendix: en igualdad de metricas se conserva la primera opcion registrada"
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, txt, vec.tobytes()))
    import bibliotecario.memory.retriever as R
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])

    top6 = {h["chunk"] for h in R.search("desempate", top_k=6)}
    found = {c["chunk"] for d in T.deep_sweep("desempate", per_doc=4)["docs"] for c in d["chunks"]}
    assert 30 not in top6  # el top-6 por relevancia no lo alcanza
    assert 30 in found  # el barrido con cobertura de documento sí


def test_deep_sweep_ordena_por_indice(tmp_path, monkeypatch):
    """El barrido ordena por índice para que el agente lea contexto contiguo."""
    import bibliotecario.memory.retriever as R
    from bibliotecario.agent import tools as T
    db = tmp_path / "orden.db"
    monkeypatch.setattr(storage, "db_path", lambda: db)
    storage.init_db(db)
    with storage.get_conn(db) as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Orden", "h10"))
        for i in range(12):
            vec = np.zeros(4, dtype="float32")
            vec[0] = 1.0 - i * 0.05
            conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                         (1, i, f"chunk {i}", vec.tobytes()))
    monkeypatch.setattr(R, "encode_one", lambda q: np.array([1.0, 0, 0, 0], dtype="float32"))
    monkeypatch.setattr(R.PEARL, "retrieve_evidence", lambda *a, **k: [])
    idx = [c["chunk"] for c in T.deep_sweep("chunk", per_doc=3)["docs"][0]["chunks"]]
    assert idx == sorted(idx)


@pytest.mark.parametrize("qid,gold_chunks", [
    ("wiki-2", {(5, 57)}),
    ("tce-3", {(3, 40)}),
    ("tce-2", {(3, 39), (3, 40)}),
    ("reas-3", {(4, 10), (4, 55), (4, 58)}),
])
def test_gold_evidence_alcanzable_en_cierre(qid, gold_chunks, monkeypatch):
    """Regresión: el cierre (top-8 + barrido) debe poder alcanzar la evidencia que
    responde a cada pregunta difícil del golden set.

    Sin esto el agente cerraba sin haber visto nunca el chunk con la respuesta
    (p. ej. el apéndice de WikiSkill, c57) y por eso fallaba aunque la cita era
    correcta. Sets de chunks porque varias respuestas son válidas por pregunta.
    """
    import json
    from pathlib import Path

    from bibliotecario.agent.tools import deep_sweep, search_papers

    root = Path(__file__).resolve().parents[1]
    db, ev = root / "data" / "bibliotecario.db", root / "evals" / "golden_qa.jsonl"
    if not ev.exists() or not db.exists():
        pytest.skip("requiere corpus ingerido")
    # db_path puede quedar monkeypatcheado por otros tests del módulo
    monkeypatch.setattr(storage, "db_path", lambda: db)
    q = next(json.loads(l)["question"] for l in ev.read_text().splitlines()
             if l.strip() and json.loads(l)["id"] == qid)
    base = {(h["doc_id"], h["chunk"]) for h in search_papers(q, top_k=8)["hits"]}
    sweep = {(d["doc_id"], c["chunk"]) for d in deep_sweep(q)["docs"] for c in d["chunks"]}
    assert gold_chunks & (base | sweep), f"{qid}: evidencia gold inalcanzable"


@pytest.mark.parametrize("qid,needle", [
    ("wiki-2", "5 failing traces"),   # el tope exacto, al final del c57
    ("tce-3", "earliest candidate"),  # la regla de desempate, a mitad del c40
])
def test_cierre_incluye_el_dato_literal(qid, needle, monkeypatch):
    """El cierre debe llevar el texto ÍNTEGRO del chunk con el dato.

    Regresión: se truncaba el chunk a 900 chars y la respuesta ("5 failing traces"),
    que está en la segunda mitad del c57) quedaba cortada. Con el texto completo el
    agente puede copiar la cifra literal en vez de inventarla.
    """
    import json
    from pathlib import Path

    from bibliotecario.agent.loop import _deep_evidence

    root = Path(__file__).resolve().parents[1]
    db, ev = root / "data" / "bibliotecario.db", root / "evals" / "golden_qa.jsonl"
    if not ev.exists() or not db.exists():
        pytest.skip("requiere corpus ingerido")
    monkeypatch.setattr(storage, "db_path", lambda: db)
    q = next(json.loads(l)["question"] for l in ev.read_text().splitlines()
             if l.strip() and json.loads(l)["id"] == qid)
    assert needle in _deep_evidence(q)
