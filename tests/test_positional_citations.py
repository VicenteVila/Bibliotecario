"""Citas posicionales `[N]` (brazo posicional del A/B de blueprints).

Motivo: `_source_for` presentaba la fuente como `[chunk 41]` sin doc_id, pero
R1 exigía `[doc:<id>:<chunk>]` — el modelo tenía que adivinar el doc_id en cada
puntero, y esa adivinanza es una fuente de `puntero_roto` medible sin juez.
Aquí el modelo solo escribe `[N]`; el mapeo a `[doc:X:Y]` es determinista.
"""
import pytest

from bibliotecario.core import storage
from bibliotecario.knowledge import procedural as P


@pytest.fixture
def _fuente():
    """Doc 1 con dos chunks y una técnica que apunta a ellos.

    Usa la BD aislada del conftest (db_path ya parcheado): escribir en otro
    fichero dejaba chunks invisibles para `_fuente_chunks`.
    """
    with storage.get_conn() as conn:
        conn.execute("INSERT INTO documents (path, title, paper_hash) VALUES (?,?,?)",
                     ("f", "Paper Pos", "hpos"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 0, "Task-CoEvolve: variance-weighted task selection.", b"\x00"))
        conn.execute("INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                     (1, 7, "Hájek estimation corrects the biased subset score.", b"\x00"))
    P.register_procedure("variance-weighted task selection", technique="X", doc_id=1)
    P.register_procedure("Hájek estimation", technique="X", doc_id=1)
    return True


def test_map_mapea_validos_y_fuera_de_rango():
    from bibliotecario.agent.tools import map_positional_citations

    mapa = {1: (2, 0), 2: (2, 41)}
    out, stats = map_positional_citations(
        "El método usa «sampling» [1] y estima con [2], pero también mira [99].", mapa)

    assert "[doc:2:0]" in out
    assert "[doc:2:41]" in out
    assert "[doc:0:0]" in out          # fuera de rango: puntero que nunca resuelve
    assert stats == {"mapeados": 2, "fuera_de_rango": 1}


def test_map_no_toca_doc_pointers_ni_prosa():
    """Un blueprint legacy con `[doc:X:Y]` canónicos no se corrompe."""
    from bibliotecario.agent.tools import map_positional_citations

    texto = "Cita legacy [doc:3:5] y prosa con año [2024] y una lista [1]."
    out, stats = map_positional_citations(texto, {1: (1, 0)})

    assert "[doc:3:5]" in out          # canónico intacto
    assert "[2024]" in out             # 4 dígitos: no es cita posicional
    assert "[doc:1:0]" in out
    assert stats == {"mapeados": 1, "fuera_de_rango": 0}


def test_map_mapa_vacio_marca_todo_fuera():
    from bibliotecario.agent.tools import map_positional_citations

    out, stats = map_positional_citations("apunta a [3]", {})
    assert out == "apunta a [doc:0:0]"
    assert stats["fuera_de_rango"] == 1


def test_fuente_numerada_sin_ids_visibles(_fuente, monkeypatch):
    from bibliotecario.agent import tools as T

    doc_id, texto, mapa = T._fuente_numerada("X", P.list_procedures(technique="X"))

    assert doc_id == 1
    assert "[1]" in texto and "[2]" in texto
    assert "[chunk" not in texto
    assert "doc_id" not in texto
    assert mapa == {1: (1, 0), 2: (1, 7)}
    # misma selección que el legacy: chunk 0 siempre, más el que nombra el proc.
    leg_doc, leg_txt = T._source_for("X", P.list_procedures(technique="X"))
    assert leg_doc == doc_id
    assert "[chunk 0]" in leg_txt and "[chunk 7]" in leg_txt


def test_build_blueprint_legacy_byte_identico(_fuente, monkeypatch):
    """positional=False por defecto: camino antiguo intacto, sin mapa."""
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    seen: list[str] = []
    monkeypatch.setattr(T, "generate", lambda prompt, **k: seen.append(prompt) or
                        "ok [doc:1:0]")

    out = T.build_blueprint("X", "objetivo")

    assert "citas_posicionales" in out and out["citas_posicionales"] is None
    assert "[doc:<id>:<chunk>]" in seen[0]      # reglas legacy
    assert "R0." not in seen[0]
    assert "[doc:1:0]" in out["blueprint"]      # sin mapeo: el texto queda como salió


def test_build_blueprint_positional_mapea_y_reporta(_fuente, monkeypatch):
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    seen: list[str] = []
    # el modelo cita [1] (chunk 0) y fabrica el índice [99]
    monkeypatch.setattr(T, "generate", lambda prompt, **k: seen.append(prompt) or
                        "usa variance-weighted task selection. [1] y otro modulo. [99]")

    out = T.build_blueprint("X", "objetivo", positional=True)

    assert "[doc:1:0]" in out["blueprint"]      # [1] → chunk 0 del doc 1
    assert "[doc:0:0]" in out["blueprint"]      # [99] → puntero_roto para el verificador
    assert out["citas_posicionales"] == {"mapeados": 1, "fuera_de_rango": 1}
    assert "R0." in seen[0]
    assert "[N]" in seen[0]
    assert "[doc:<id>:<chunk>]" not in seen[0]  # el legacy no se cuela en el brazo posicional


def test_build_blueprint_positional_sin_llm_no_mapea(_fuente, monkeypatch):
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    monkeypatch.setattr(T, "generate", lambda *a, **k: "")

    out = T.build_blueprint("X", "objetivo", positional=True)

    assert out["citas_posicionales"] is None
    assert "(sin LLM" in out["blueprint"]


def test_positional_compila_con_verify_and_mark(_fuente, monkeypatch):
    """El blueprint mapeado entra en el verificador existente sin cambios."""
    from bibliotecario.agent import tools as T

    monkeypatch.setattr(T.PEARL, "retrieve_evidence", lambda *a, **k: [])
    monkeypatch.setattr(T, "generate", lambda prompt, **k:
                        "usa variance-weighted task selection. [1]")

    bp = T.build_blueprint("X", "objetivo", positional=True)
    out = T.verify_and_mark(bp)

    assert out["verificado"] is True
    assert out["violaciones"] == []
    from bibliotecario.agent.attribution import _POINTER
    assert _POINTER.findall(out["blueprint"]) == [("1", "0")]
