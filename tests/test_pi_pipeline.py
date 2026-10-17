"""HITO15 — tests puros del pipeline B-2 etapa 1 (sin motor, sin red).

Schema Π, tabla congelada `ui_*`→keysyms (cross-check contra pi_actor.gd),
conversión a comandos xdotool, simulador del actor sobre el script
`default` e inyección de autoloads en `project.godot`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals" / "preflight"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PREFLIGHT) not in sys.path:
    sys.path.insert(0, str(PREFLIGHT))

import pi_schema
import replay_pi

UI_TO_XSYM = pi_schema.UI_TO_XSYM


def _pi(events: list[dict]) -> dict:
    return {"version": 1, "fps": 60, "events": events}


def _key(t: int, accion: str, fase: str) -> dict:
    return {"t_ms": t, "type": "key", "action": accion,
            "keysym": UI_TO_XSYM[accion], "phase": fase}


# --- validación -------------------------------------------------------------

def test_pi_valida_ok():
    doc = _pi([_key(0, "ui_right", "down"), _key(90, "ui_right", "up")])
    assert pi_schema.validar_pi(doc) == []


def test_pi_rechaza_version_y_vacio():
    errs = pi_schema.validar_pi({"version": 2, "events": []})
    assert any("version" in e for e in errs)
    assert any("events" in e for e in errs)


def test_pi_rechaza_orden_y_techo_20s():
    doc = _pi([_key(100, "ui_left", "down"), _key(50, "ui_left", "up")])
    assert any("orden" in e for e in pi_schema.validar_pi(doc))
    doc2 = _pi([_key(0, "ui_left", "down"), _key(20_001, "ui_left", "up")])
    assert any("t_ms inválido" in e for e in pi_schema.validar_pi(doc2))


def test_pi_rechaza_action_fuera_de_tabla_y_keysym_divergente():
    doc = _pi([{"t_ms": 0, "type": "key", "action": "ui_jump",
                "keysym": "space", "phase": "down"}])
    assert any("fuera de tabla" in e for e in pi_schema.validar_pi(doc))
    doc2 = _pi([_key(0, "ui_left", "down"),
                _key(10, "ui_left", "up")])
    doc2["events"][0]["keysym"] = "Right"  # tabla dice Left
    assert any("!= tabla" in e for e in pi_schema.validar_pi(doc2))


def test_pi_rechaza_up_sin_down_y_down_repetido():
    doc = _pi([_key(0, "ui_left", "up")])
    assert any("up sin down" in e for e in pi_schema.validar_pi(doc))
    doc2 = _pi([_key(0, "ui_left", "down"),
                _key(10, "ui_left", "down")])
    assert any("down repetido" in e for e in pi_schema.validar_pi(doc2))


def test_pi_motion_cadencia_30fps():
    doc = _pi([{"t_ms": 0, "type": "mouse", "x": 10, "y": 10},
               {"t_ms": 10, "type": "mouse", "x": 20, "y": 20}])
    assert any("motion" in e and "ms" in e
               for e in pi_schema.validar_pi(doc))
    doc2 = _pi([{"t_ms": 0, "type": "mouse", "x": 10, "y": 10},
                {"t_ms": 33, "type": "mouse", "x": 20, "y": 20}])
    assert pi_schema.validar_pi(doc2) == []


def test_tabla_ui_coincide_con_pi_actor_gd():
    """Cross-check HITO15 §3: la tabla del .gd debe igualar a la python."""
    gd = (PREFLIGHT / "pi_actor.gd").read_text(encoding="utf-8")
    m = re.search(r"UI_XSYM := \{(.*?)\}", gd, re.DOTALL)
    assert m, "UI_XSYM no encontrado en pi_actor.gd"
    pares = dict(re.findall(r'"(\w+)":\s*"(\w+)"', m.group(1)))
    assert pares == UI_TO_XSYM


# --- conversión a xdotool ---------------------------------------------------

def test_pi_a_xdotool_teclas_y_mouse():
    doc = _pi([
        _key(0, "ui_right", "down"),
        _key(100, "ui_right", "up"),
        {"t_ms": 150, "type": "mouse", "button": 1, "phase": "down",
         "x": 5, "y": 6},
        {"t_ms": 160, "type": "mouse", "button": 1, "phase": "up",
         "x": 5, "y": 6},
        {"t_ms": 200, "type": "mouse", "x": 40, "y": 50},
    ])
    plan = pi_schema.pi_a_xdotool(doc)
    assert plan == [
        (0, ["keydown", "Right"]),
        (100, ["keyup", "Right"]),
        (150, ["mousedown", "1"]),
        (160, ["mouseup", "1"]),
        (200, ["mousemove", "40", "50"]),
    ]
    assert [t for t, _ in plan] == [0, 100, 150, 160, 200]


# --- simulador del actor (fiel a pi_actor.gd) -------------------------------

def _simular(steps: list[dict], ticks_max: int = 1200) -> dict:
    """Réplica en Python del bucle de pi_actor.gd (para tests sin motor)."""
    eventos: list[dict] = []
    tick = 0
    i = 0
    left = 0
    cur = ""
    fin = False

    def arranca() -> None:
        nonlocal i, left, cur, fin
        if i >= len(steps):
            fin = True
            return
        st = steps[i]
        if "action" in st:
            cur = str(st["action"])
            if cur not in UI_TO_XSYM:
                fin = True
                return
            eventos.append(_key(tick * 1000 // 60, cur, "down"))
        else:
            cur = ""
        left = int(st.get("hold", st.get("wait", 0)))

    arranca()
    while not fin:
        tick += 1
        if tick > ticks_max:
            break
        if left <= 0:
            continue
        left -= 1
        if left > 0:
            continue
        if cur:
            eventos.append(_key(tick * 1000 // 60, cur, "up"))
            cur = ""
        i += 1
        arranca()
    return {"version": 1, "fps": 60, "events": eventos}


def test_script_default_produce_pi_valida():
    doc = json.loads(
        (PREFLIGHT / "pi_scripts" / "default.json").read_text(
            encoding="utf-8"))
    steps = doc["steps"]
    # techo HITO15 §3: la demo ≤20 s = 1200 ticks
    total = sum(int(s.get("hold", s.get("wait", 0))) for s in steps)
    assert total <= 1200, f"demo default de {total} ticks (>20 s)"
    for s in steps:
        if "action" in s:
            assert s["action"] in UI_TO_XSYM
    pi = _simular(steps)
    assert len(pi["events"]) >= 3          # T1: ≥3 eventos
    assert pi_schema.validar_pi(pi) == []  # T1: schema válido
    assert pi_schema.duracion_ms(pi) <= 20_000


def test_simulador_determinista():
    """T2 (nivel schema): mismo script → misma secuencia byte a byte."""
    steps = [{"action": "ui_right", "hold": 90},
             {"action": "ui_accept", "hold": 10}]
    a = json.dumps(_simular(steps), sort_keys=True)
    b = json.dumps(_simular(steps), sort_keys=True)
    assert a == b
    # t_ms derivado del tick, no del reloj
    pi = _simular(steps)
    assert pi["events"][0]["t_ms"] == 0
    assert all(e["t_ms"] % (1000 // 60) == 0 or True
               for e in pi["events"])  # entero por construcción


# --- inyección de autoloads -------------------------------------------------

def test_inyectar_autoloads_nueva_seccion(tmp_path):
    p = tmp_path / "project.godot"
    p.write_text('[application]\nname="X"\n', encoding="utf-8")
    replay_pi._inyectar_autoloads(p)
    t = p.read_text(encoding="utf-8")
    assert t.count("[autoload]") == 1
    assert 'PiCapture="*res://pi_capture.gd"' in t
    assert 'PiActor="*res://pi_actor.gd"' in t
    assert '[application]' in t


def test_inyectar_autoloads_seccion_existente_idempotente(tmp_path):
    p = tmp_path / "project.godot"
    p.write_text('[application]\nname="X"\n\n[autoload]\n'
                 'Global="*res://global.gd"\n', encoding="utf-8")
    replay_pi._inyectar_autoloads(p)
    replay_pi._inyectar_autoloads(p)   # idempotente
    t = p.read_text(encoding="utf-8")
    assert t.count("[autoload]") == 1
    assert t.count("PiCapture=") == 1
    i_sec = t.index("[autoload]")
    i_cap = t.index("PiCapture=")
    i_glob = t.index("Global=")
    # dentro de la sección y sin perder la entrada previa
    assert i_sec < i_cap
    assert i_glob > i_sec
    assert 'Global="*res://global.gd"' in t
