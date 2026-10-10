"""Regresiones del prompt de parada (PROMPT_LEGACY), opt-in por variable de entorno.

El commit 15261a0 quito la orden "CIERRE OBLIGADO: responde YA" y anadio la rama
de parada explicita. Eso bajo la fabricacion de 31.5% a 0% (McNemar p <= 4.8e-07)
y es el cimiento del Hito 0.

El flag existe para poder comparar LOS DOS PROMPTS A LA MISMA TEMPERATURA, que es
lo que hace falta para aislar la ventaja de r5 (4.714, corrio a temp 0.2) del
efecto de temperatura (0.2 -> 0.0 cuesta ~0.17 de juez en respondibles mientras
baja la fabricacion del 51.6% al 33.9%). Sin el flag, r5 no tiene baseline
comparable y la deuda del Hito 1 no se puede resolver.

Verificado fuera de test, contra git: con PROMPT_LEGACY=1 los prompts SHA-256
coinciden con 15261a0^, y con =0 con la cabecera de main. Aqui se comprueba lo
que no debe romperse mientras se mantiene eso.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bibliotecario.agent import loop as LOOP
from bibliotecario.agent import state as STATE

COLA_COMUN = "- La pregunta pide un dato concreto"


def _recarga(monkeypatch, valor: str):
    monkeypatch.setenv("PROMPT_LEGACY", valor)
    importlib.reload(STATE)
    importlib.reload(LOOP)


def _restaura(monkeypatch):
    monkeypatch.delenv("PROMPT_LEGACY", raising=False)
    importlib.reload(STATE)
    importlib.reload(LOOP)


def test_prompt_actual_es_el_default():
    """Sin la variable de entorno sigue vigente el prompt del Hito 0."""
    assert STATE.PROMPT_LEGACY is False
    cierre = LOOP._close_prompt("q", "ctx", "", "", 0)
    assert "CIERRE OBLIGADO" not in cierre
    assert "Si la evidencia contiene literalmente el dato" in cierre
    assert "declarar que la evidencia reunida no contiene lo pedido" in STATE.STATIC_PROMPT
    assert "después responde con lo que tengas" not in STATE.STATIC_PROMPT


def test_flag_se_lee_del_entorno(monkeypatch):
    _recarga(monkeypatch, "1")
    try:
        assert STATE.PROMPT_LEGACY is True
        cierre = LOOP._close_prompt("q", "ctx", "", "", 0)
        assert "CIERRE OBLIGADO: responde YA" in cierre
        assert "CIERRE: redacta" not in cierre
        assert "después responde con lo que tengas" in STATE.STATIC_PROMPT
        assert "declarar que la evidencia reunida no contiene lo pedido" not in STATE.STATIC_PROMPT
    finally:
        _restaura(monkeypatch)


def test_el_flag_solo_toca_la_cabecera_del_cierre(monkeypatch):
    """Lo que hay DETRAS de la cabecera es texto comun a las dos variantes.

    Si alguna edicion metiera la cola dentro del if, los dos prompts dejarian de
    ser el mismo sistema con una sola linea cambiada y la comparacion de
    temperatura contra prompt no serviria para nada.
    """
    actual = LOOP._close_prompt("q", "ctx", "", "", 0)
    _recarga(monkeypatch, "1")
    try:
        legacy = LOOP._close_prompt("q", "ctx", "", "", 0)
    finally:
        _restaura(monkeypatch)

    assert COLA_COMUN in actual and COLA_COMUN in legacy
    assert actual.split(COLA_COMUN)[1] == legacy.split(COLA_COMUN)[1]
    assert actual.split(COLA_COMUN)[0] != legacy.split(COLA_COMUN)[0]


def test_el_resto_del_static_prompt_es_comun(monkeypatch):
    """REGLAS, LOOP y TOOLS son texto comun: solo cambian objetivo y CIERRE."""
    actual = STATE.STATIC_PROMPT
    _recarga(monkeypatch, "1")
    try:
        legacy = STATE.STATIC_PROMPT
    finally:
        _restaura(monkeypatch)

    assert actual != legacy
    for marca in ("LOOP: piensa", "TOOLS:", "search_papers(query, top_k)",
                  "get_status(): estado del sistema."):
        assert marca in actual and marca in legacy
    assert actual.split("TOOLS:")[1] == legacy.split("TOOLS:")[1]
