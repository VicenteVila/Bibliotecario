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
    monkeypatch.delenv("CLOSE_LEGACY", raising=False)
    monkeypatch.delenv("URGENCY", raising=False)
    monkeypatch.delenv("E_GROUND", raising=False)
    monkeypatch.delenv("ANS_CLEAN", raising=False)
    importlib.reload(STATE)
    importlib.reload(LOOP)


# --- candidata E: anclaje antes de poder responder o abstener -----------------


def test_e_ground_apagado_no_toca_el_prompt(monkeypatch):
    """Sin E_GROUND el prompt tiene que salir byte-identico al de promptstop."""
    import hashlib

    monkeypatch.delenv("E_GROUND", raising=False)
    importlib.reload(STATE)
    try:
        assert hashlib.sha256(STATE.STATIC_PROMPT.encode()).hexdigest()[:10] == "22f838287e"
        assert "cada afirmación necesita" not in STATE.STATIC_PROMPT
    finally:
        monkeypatch.delenv("E_GROUND", raising=False)
        importlib.reload(STATE)


def test_e_ground_anade_anclaje_sin_tocar_los_controles_de_fabricacion(monkeypatch):
    """E toca los dos fallos medidos y NADA de lo que ya da 0/64 de fabricacion.

    Medido item a item (candA vs promptstop): tce-b1 es una falsa abstencion
    (el dato si esta, promptstop no lo encuentra) y reas-b4 es responder con 0
    citas. Esos dos valen 6 puntos de los 6,55 que cuesta llegar a 4.50.

    Lo que NO puede mover: el objetivo que declara la ausencia valida, ni la
    rama de cierre que dice "declara y cierra sin dar ningun dato por cierto".
    Si lo moviera, volveriamos a la fabricacion de 14/64 de candA.
    """
    monkeypatch.setenv("E_GROUND", "1")
    try:
        importlib.reload(STATE)
        s = STATE.STATIC_PROMPT
        # los dos fallos medidos
        assert "deep_sweep" in s and "Antes de declarar que no aparece" in s
        assert "cada afirmación necesita su [doc:chunk]" in s
        # los controles de fabricacion, intactos y ANTES no despues
        assert "son respuestas válidas" in s          # objetivo de estado
        assert "Responder con algo parecido es peor" in s   # rama de cierre
        assert s.index("deep_sweep: el dato puede estar") < s.index("Responder con algo parecido")
        # ni una pizca de la urgencia que reintroduce fabricacion
        assert "RESPONDE de inmediato" not in s
        assert "después responde con lo que tengas" not in s
    finally:
        monkeypatch.delenv("E_GROUND", raising=False)
        importlib.reload(STATE)


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


# --- eje del cierre, desacoplado del estado -------------------------------------


def test_close_legacy_por_defecto_sigue_a_prompt_legacy():
    """Sin variables, los dos ejes van juntos: se conserva la config de r5."""
    assert STATE.PROMPT_LEGACY is False
    assert STATE.CLOSE_LEGACY is False


def test_close_se_puede_separar_del_estado(monkeypatch):
    """Estado viejo + cierre nuevo: es la candidata A del Hito 1.

    La fabricacion la arreglo el cierre condicional, no el texto de estado; el
    texto de estado pone la orden de responder. Separarlos permite combinar la
    mitad buena de cada uno. `PROMPT_LEGACY=1` solo no sirve para eso porque
    arrastra el cierre consigo.
    """
    monkeypatch.setenv("PROMPT_LEGACY", "1")
    monkeypatch.setenv("CLOSE_LEGACY", "0")
    try:
        importlib.reload(STATE)
        importlib.reload(LOOP)
        assert STATE.PROMPT_LEGACY is True
        assert STATE.CLOSE_LEGACY is False
        cierre = LOOP._close_prompt("q", "ctx", "", "", 0)
        # el estado es el viejo (urgencia de responder)...
        assert "RESPONDE de inmediato" in STATE.STATIC_PROMPT
        # ...y el cierre es el nuevo (rama condicional)
        assert "CIERRE OBLIGADO" not in cierre
        assert "Si NO lo contiene" in cierre
    finally:
        _restaura(monkeypatch)


def test_prompt_legacy_solo_sigue_arrastrando_el_cierre(monkeypatch):
    """`PROMPT_LEGACY=1` sin tocar CLOSE_LEGACY sigue siendo la config de r5."""
    monkeypatch.setenv("PROMPT_LEGACY", "1")
    monkeypatch.delenv("CLOSE_LEGACY", raising=False)
    try:
        importlib.reload(STATE)
        importlib.reload(LOOP)
        assert STATE.CLOSE_LEGACY is True
        assert "CIERRE OBLIGADO" in LOOP._close_prompt("q", "ctx", "", "", 0)
    finally:
        _restaura(monkeypatch)


# --- candidata C: urgencia sin perder el objetivo de abstencion ---------------


def test_urgency_apagado_deja_el_prompt_nuevo_tocado(monkeypatch):
    """Sin URGENCY el prompt nuevo tiene que salir byte-identico al actual.

    Si esta prueba falla, alguien ha metido un cambio en el prompt por un lado
    y las runs dejarian de ser comparables con las ya medidas.
    """
    import hashlib

    monkeypatch.delenv("URGENCY", raising=False)
    importlib.reload(STATE)
    try:
        assert hashlib.sha256(STATE.STATIC_PROMPT.encode()).hexdigest()[:10] == "22f838287e"
        assert "RESPONDE de inmediato" not in STATE.STATIC_PROMPT
    finally:
        monkeypatch.delenv("URGENCY", raising=False)
        importlib.reload(STATE)


def test_urgency_devuelve_las_dos_lineas_sin_tocar_el_objetivo(monkeypatch):
    """URGENCY=1: urgencia restaurada Y la rama de abstencion intacta.

    Es la apuesta de la candidata C: la fabricacion la arreglo el objetivo
    ("declarar que no aparece" vale como respuesta, 0/64) y la calidad la
    costearon las dos lineas de urgencia quitadas. Si URGENCY quitara tambien
    el objetivo volveriamos a la fabricacion de 14/64 sin haber ganado nada.
    """
    monkeypatch.setenv("URGENCY", "1")
    try:
        importlib.reload(STATE)
        s = STATE.STATIC_PROMPT
        # urgencia restaurada (estado viejo)
        assert "RESPONDE de inmediato" in s
        assert "después responde con lo que tengas" in s
        # objetivo de abstencion intacto (estado nuevo): es lo que mantiene fab=0
        assert "son respuestas válidas" in s
        assert "no aparece en la evidencia" in s
        # y el resto del prompt no se mueve
        assert "TOOLS:" in s and "search_papers(query, top_k)" in s
    finally:
        monkeypatch.delenv("URGENCY", raising=False)
        importlib.reload(STATE)


# --- candidata F = E + guarda antifuga ---------------------------------------


def test_f_sin_ansi_clean_es_byte_identica_a_e(monkeypatch):
    """ANS_CLEAN apagado no puede mover ni un byte de la E ya medida."""
    import hashlib

    monkeypatch.setenv("E_GROUND", "1")
    monkeypatch.delenv("ANS_CLEAN", raising=False)
    try:
        importlib.reload(STATE)
        assert hashlib.sha256(STATE.STATIC_PROMPT.encode()).hexdigest()[:10] == "52ee3bdf3d"
    finally:
        monkeypatch.delenv("E_GROUND", raising=False)
        monkeypatch.delenv("ANS_CLEAN", raising=False)
        importlib.reload(STATE)


def test_f_banea_la_fuga_sin_tocar_los_controles(monkeypatch):
    """F anade SOLO la prohibicion de devolver razonamiento.

    Medido en candE: las respuestas que eran narracion del propio proceso se
    dispararon de 2 (promptstop: pg-b5, wiki-b4) a 4 (candE: tce-b5, tce-b6,
    tce-b7, wiki-b4) y todas puntuan 1. Eso se llevo -8 puntos de los +12 que
    gano en el resto. F no puede tocar nada de lo que ya funciona.
    """
    monkeypatch.setenv("E_GROUND", "1")
    monkeypatch.setenv("ANS_CLEAN", "1")
    try:
        importlib.reload(STATE)
        s = STATE.STATIC_PROMPT
        assert "nunca el razonamiento, la lista de chunks mirados" in s
        # lo que E ya arreglado, intacto
        assert "cada afirmación necesita su [doc:chunk]" in s
        assert "Antes de declarar que no aparece, ejecuta deep_sweep" in s
        # los controles de fabricacion, sin mover
        assert "son respuestas válidas" in s
        assert "Responder con algo parecido es peor" in s
        # y la guarda va despues de las reglas de busqueda
        assert s.index("deep_sweep: el dato puede estar") < s.index("nunca el razonamiento")
    finally:
        monkeypatch.delenv("E_GROUND", raising=False)
        monkeypatch.delenv("ANS_CLEAN", raising=False)
        importlib.reload(STATE)
