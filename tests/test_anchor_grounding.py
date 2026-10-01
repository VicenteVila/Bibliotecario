"""Regresiones del anclaje (ANCHOR_GROUNDING), opt-in por variable de entorno.

El anclaje se activa en bibliotecario/agent/loop.py. Se comprueba lo que no debe
romperse: el default apagado, la propagacion por el prompt, el tratamiento de una
salida tipo tool como "no encontrado", y que el flag se lee del entorno.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bibliotecario.agent import loop as LOOP


def test_anchor_grounding_apagado_por_defecto():
    """Sin la variable de entorno el cierre no cambia: el anclaje es opt-in."""
    assert LOOP.ANCHOR_GROUNDING is False


def test_anchor_se_lee_del_entorno(monkeypatch):
    monkeypatch.setenv("ANCHOR_GROUNDING", "1")
    reloaded = importlib.reload(LOOP)
    try:
        assert reloaded.ANCHOR_GROUNDING is True
    finally:
        monkeypatch.delenv("ANCHOR_GROUNDING", raising=False)
        importlib.reload(LOOP)


def test_no_encontrado_es_token_publico():
    """El sentinel se comparte con la comprobacion de _ground, no se duplica a mano."""
    assert LOOP._NO_ENCONTRADO == "NO_ENCONTRADO"


def test_ground_devuelve_no_encontrado_si_evidencia_vacia():
    """Sin barrido no se inventa: una pasada de localizacion sobre nada devuelve el sentinel."""
    assert LOOP._ground("¿que cifra da el paper?", "") == LOOP._NO_ENCONTRADO


def test_ground_trata_salida_de_tool_como_no_encontrado(monkeypatch):
    """Si el modelo responde con una llamada a tool en vez de copiar spans, no hay anclaje util."""
    monkeypatch.setattr(LOOP, "generate",
                        lambda prompt, max_tokens=512, retries=None: '```json\n{"tool": "search_papers"}\n```')
    assert LOOP._ground("¿que cifra da el paper?", "3.3 y 1.9 aparecen aqui") == LOOP._NO_ENCONTRADO


def test_ground_reconoce_no_encontrado_en_la_salida(monkeypatch):
    monkeypatch.setattr(LOOP, "generate",
                        lambda prompt, max_tokens=512, retries=None: "NO_ENCONTRADO")
    assert LOOP._ground("¿que cifra da el paper?", "texto cualquiera") == LOOP._NO_ENCONTRADO


def test_ground_conserva_spans_verbatim(monkeypatch):
    """Si el modelo copia lineas, se devuelven tal cual para que el cierre las use."""
    spans = "[3:25] la reduccion de coste alcanza 3.3 puntos en el subconjunto"
    monkeypatch.setattr(LOOP, "generate", lambda prompt, max_tokens=512, retries=None: spans)
    assert LOOP._ground("¿que cifra da el paper?", "texto cualquiera") == spans


def test_final_answer_sin_anclaje_no_inyecta_la_seccion(monkeypatch):
    """Con el anclaje apagado el prompt NO debe contener la seccion ANCLAJE."""
    capturado: dict[str, str] = {}

    def fake_generate(prompt, max_tokens=512, retries=None):
        capturado["prompt"] = prompt
        return "respuesta con cita [3:25]."

    monkeypatch.setattr(LOOP, "generate", fake_generate)
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda question, per_doc=4, n_docs=2: "relleno")
    monkeypatch.setattr(LOOP, "ANCHOR_GROUNDING", False)

    LOOP._final_answer("¿que cifra da el paper?", "", [], 0)

    assert "ANCLAJE" not in capturado["prompt"]
    assert capturado["prompt"], "el cierre debe seguir generando con evidencia"


def test_sin_barrido_no_se_llama_al_anclaje(monkeypatch):
    """Si el barrido viene vacio, _ground cortocircuita y el cierre lo declara.

    Antes esto producia una fila con judge=0: el agente se quedaba sin respuesta
    y el juez puntuaba el vacio. El sentinel evita precisamente ese camino.
    """
    _llamadas: list[int] = []

    def fake_generate(prompt, max_tokens=512, retries=None):
        _llamadas.append(1)
        return "no hay evidencia [doc:?]"

    monkeypatch.setattr(LOOP, "generate", fake_generate)
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda question, per_doc=4, n_docs=2: "")
    monkeypatch.setattr(LOOP, "ANCHOR_GROUNDING", True)

    LOOP._final_answer("¿que cifra da el paper?", "", [], 0)

    # Solo la llamada de cierre: _ground no debe gastar una llamada sin evidencia.
    assert len(_llamadas) == 1


def test_final_answer_avisa_de_no_encontrado_y_prohibe_inventar(monkeypatch):
    """Si el anclaje no localiza el dato, el cierre lo dice y prohibe deducir."""
    capturado: dict[str, str] = {}

    def fake_generate(prompt, max_tokens=512, retries=None):
        capturado["prompt"] = prompt
        return "no he encontrado el dato [doc:?]"

    monkeypatch.setattr(LOOP, "generate", fake_generate)
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda question, per_doc=4, n_docs=2: "relleno")
    monkeypatch.setattr(LOOP, "ANCHOR_GROUNDING", True)
    monkeypatch.setattr(LOOP, "_ground", lambda question, deep, retries=1: LOOP._NO_ENCONTRADO)

    LOOP._final_answer("¿que cifra da el paper?", "", [], 0)

    prompt = capturado["prompt"]
    assert "no se ha localizado" in prompt
    assert "NO inventes" in prompt


def test_final_answer_con_spans_prohibe_introducir_nombres_ausentes(monkeypatch):
    """Con spans disponibles, el cierre solo puede apoyarse en esos spans."""
    capturado: dict[str, str] = {}

    def fake_generate(prompt, max_tokens=512, retries=None):
        capturado["prompt"] = prompt
        return "respuesta anclada [3:25]."

    monkeypatch.setattr(LOOP, "generate", fake_generate)
    monkeypatch.setattr(LOOP, "_deep_evidence", lambda question, per_doc=4, n_docs=2: "relleno")
    monkeypatch.setattr(LOOP, "ANCHOR_GROUNDING", True)
    monkeypatch.setattr(LOOP, "_ground",
                        lambda question, deep, retries=1: "[3:25] la cifra es 3.3")

    LOOP._final_answer("¿que cifra da el paper?", "", [], 0)

    prompt = capturado["prompt"]
    assert "[3:25] la cifra es 3.3" in prompt
    assert "EXCLUSIVAMENTE" in prompt