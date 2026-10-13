"""Capa de comprensión (knowledge/study.py) — la que se puede aprender.

No es un blueprint: no se construye nada. Lo que estos tests defienden es que
(1) el estudio se escribe con punteros en el formato que sí resuelven, (2) se
persiste y se reutiliza, y (3) si la fuente se trunca, el estudio lo declara —
que es R5 aplicada al propio artefacto.
"""
from __future__ import annotations

from bibliotecario.core import storage
from bibliotecario.knowledge import study as S


def _sembrar(doc_id: int, chunks: list[str], title: str = "Paper de prueba"):
    with storage.get_conn() as conn:
        # id explicito: sin el, sqlite autoasigna 1,2,3… y no coincide con el
        # doc_id que el test cree estar sembrando.
        conn.execute("INSERT INTO documents (id, path, title) VALUES (?,?,?)",
                     (doc_id, f"p{doc_id}.pdf", title))
        for i, t in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (doc_id, chunk_idx, text) VALUES (?,?,?)",
                (doc_id, i, t),
            )


def test_full_source_annoa_chunks_y_no_trunca_cabe():
    _sembrar(1, ["introduccion", "metodo", "resultados"])
    src, truncado = S._full_source(1)
    assert truncado is False
    assert "[chunk 0] introduccion" in src
    assert "[chunk 2] resultados" in src


def test_full_source_declara_el_truncado():
    """Si no cabe, se trunca **y se dice**. Un estudio que se queda corto y no
    lo declara es el defecto que R5 existe para cazar."""
    _sembrar(1, ["a" * 100, "b" * 100, "c" * 100])
    src, truncado = S._full_source(1, max_chars=150)
    assert truncado is True
    assert "[chunk 0]" in src
    assert "[chunk 2]" not in src


def test_full_source_sin_chunks():
    _sembrar(1, [])
    assert S._full_source(1) == ("", False)


def test_prompt_lleva_reglas_secciones_y_otros_papers():
    _sembrar(3, ["Task-CoEvolve selecciona tareas por varianza."], "Task-CoEvolve")
    _sembrar(6, ["Un survey sobre harnesses."], "Survey de harnesses")
    p, meta = S._prompt(3)
    assert meta["truncado"] is False
    for seccion in ("## Qué propone", "## Cómo funciona", "## Qué es nuevo",
                    "## Qué no dice", "## Relación con otras técnicas", "## Fuente"):
        assert seccion in p
    # Las reglas que el A/B midió que hacen falta, en su forma probada.
    assert "R1 es suelo" in p
    assert "[doc:3:14]" in p          # formato literal, canónico
    assert "[doc3:14]" in p and "no valen" in p  # y el que NO vale, dicho
    assert "[chunk 0] Task-CoEvolve" in p
    # El cruce con otros papers va con su texto, no con el título solo:
    # relacionar de memoria sería una atribución sin fuente.
    assert "Un survey sobre harnesses" in p


def test_prompt_declara_la_fuente_truncada(monkeypatch):
    _sembrar(1, ["x" * 200] * 10)
    monkeypatch.setattr(S, "STUDY_MAX_CHARS", 300)
    p, meta = S._prompt(1)
    assert meta["truncado"] is True
    assert "se ha truncado" in p


def test_study_persiste_y_se_reutiliza(monkeypatch):
    _sembrar(1, ["El paper propone PEARL. [chunk 0]"])
    llamadas = []

    def _fake(prompt, **kw):
        llamadas.append(prompt)
        return "## Qué propone\nPEARL alinea entidades. [doc:1:0]\n"

    monkeypatch.setattr(S.llm if hasattr(S, "llm") else _llm_mod(), "generate", _fake)

    r1 = S.study_paper(1)
    assert r1["ok"] and r1["cached"] is False
    assert len(llamadas) == 1
    assert S.get_study(1).startswith("## Qué propone")

    # Segunda llamada: cacheado, sin generar de nuevo. Es lo que le da valor
    # de transferencia — regenerarlo cada vez sería volver a empezar de cero.
    r2 = S.study_paper(1)
    assert r2["cached"] is True
    assert len(llamadas) == 1


def test_study_force_regenera(monkeypatch):
    _sembrar(1, ["texto"])
    n = {"i": 0}

    def _fake(prompt, **kw):
        n["i"] += 1
        return f"v{n['i']}"

    monkeypatch.setattr(_llm_mod(), "generate", _fake)
    S.study_paper(1)
    S.study_paper(1, force=True)
    assert n["i"] == 2


def test_study_llm_vacio_no_persiste(monkeypatch):
    """Un '' del proveedor no es un estudio. Antes del fix de llm.generate esto
    se guardaba como página vacía en la wiki."""
    _sembrar(1, ["texto"])
    monkeypatch.setattr(_llm_mod(), "generate", lambda *a, **k: "")
    r = S.study_paper(1)
    assert r["ok"] is False and r["error"] == "llm_vacio"
    assert S.get_study(1) is None


def test_normalize_se_aplica_al_estudio(monkeypatch):
    """Si el modelo escribe [doc:1:chunk:2], sale normalizado a [doc:1:2] —
    que es lo único que parsean los verificadores."""
    _sembrar(1, ["texto"])
    monkeypatch.setattr(_llm_mod(), "generate",
                        lambda *a, **k: "Algo [doc:1:chunk:2] y [doc2:3].")
    r = S.study_paper(1)
    assert "[doc:1:2]" in r["study"]
    assert "[doc:2:3]" in r["study"]
    assert "chunk:" not in r["study"]


def test_list_studies(monkeypatch):
    _sembrar(1, ["texto"])
    monkeypatch.setattr(_llm_mod(), "generate", lambda *a, **k: "x")
    S.study_paper(1)
    st = S.list_studies()
    assert len(st) == 1 and st[0]["slug"] == "study-1"


def _llm_mod():
    from bibliotecario.core import llm
    return llm
