"""HITO15 §1.3 — schema de las trazas `Π` y conversión a comandos xdotool.

Congelados HITO15 §3 (etapa 1, B-2): tabla `ui_*`→keysyms, techo de 20 s,
≤30 fps en mouse-motion. Sin red, sin motor — tests puros.
"""
from __future__ import annotations

MAX_T_MS = 20_000            # GameCraft §3.2: demos ≤20 s
MIN_MOTION_DT_MS = 33        # ≤30 fps en mouse-motion (1000/30 ≈ 33)
FPS_PI = 60                  # ticks de física del grabador

# Tabla congelada HITO15 §3 — debe coincidir con `UI_XSYM` de pi_actor.gd
# (tests/test_pi_pipeline.py lo cross-checkea contra el fichero .gd).
UI_TO_XSYM: dict[str, str] = {
    "ui_left": "Left",
    "ui_right": "Right",
    "ui_up": "Up",
    "ui_down": "Down",
    "ui_accept": "space",
    "ui_cancel": "Escape",
}


def validar_pi(doc: dict) -> list[str]:
    """Devuelve la lista de errores del documento `Π` (vacía = válido)."""
    errs: list[str] = []
    if not isinstance(doc, dict):
        return ["Π no es un objeto"]
    if doc.get("version") != 1:
        errs.append(f"version != 1: {doc.get('version')!r}")
    evs = doc.get("events")
    if not isinstance(evs, list) or not evs:
        errs.append("events ausente o vacío")
        return errs

    prev_t = -1
    prev_motion_t: int | None = None
    presionadas: set[str] = set()
    for n, ev in enumerate(evs):
        if not isinstance(ev, dict):
            errs.append(f"evento {n} no es objeto")
            continue
        t = ev.get("t_ms")
        if not isinstance(t, int) or t < 0 or t > MAX_T_MS:
            errs.append(f"evento {n}: t_ms inválido ({t!r})")
            continue
        if t < prev_t:
            errs.append(f"evento {n}: t_ms {t} < anterior {prev_t} "
                        "(orden violado)")
        prev_t = t

        etipo = ev.get("type")
        if etipo == "key":
            accion = ev.get("action", "")
            xsym = ev.get("keysym", "")
            fase = ev.get("phase")
            if accion:
                esperado = UI_TO_XSYM.get(accion)
                if esperado is None:
                    errs.append(f"evento {n}: action fuera de tabla "
                                f"({accion!r})")
                elif xsym != esperado:
                    errs.append(f"evento {n}: keysym {xsym!r} != tabla "
                                f"{esperado!r} para {accion!r}")
            elif not xsym:
                errs.append(f"evento {n}: key sin action ni keysym")
            if fase not in ("down", "up"):
                errs.append(f"evento {n}: phase inválida ({fase!r})")
            elif accion:
                if fase == "down":
                    if accion in presionadas:
                        errs.append(f"evento {n}: down repetido de {accion}")
                    presionadas.add(accion)
                else:
                    if accion not in presionadas:
                        errs.append(f"evento {n}: up sin down de {accion}")
                    presionadas.discard(accion)
        elif etipo == "mouse":
            b = ev.get("button")
            if b is None:
                # mouse-motion: sin phase; coordenadas y cadencia ≤30 fps
                x, y = ev.get("x"), ev.get("y")
                if not isinstance(x, int) or not isinstance(y, int):
                    errs.append(f"evento {n}: motion sin x/y enteros")
                else:
                    if prev_motion_t is not None and t - prev_motion_t \
                            < MIN_MOTION_DT_MS:
                        errs.append(
                            f"evento {n}: motion a {t - prev_motion_t} ms "
                            f"(<{MIN_MOTION_DT_MS})")
                    prev_motion_t = t
            else:
                fase = ev.get("phase")
                if fase not in ("down", "up"):
                    errs.append(f"evento {n}: phase inválida ({fase!r})")
                if not isinstance(b, int) or not (1 <= b <= 3):
                    errs.append(f"evento {n}: button inválido ({b!r})")
        else:
            errs.append(f"evento {n}: type inválido ({etipo!r})")
    return errs


def duracion_ms(doc: dict) -> int:
    evs = doc.get("events") or []
    return max((ev.get("t_ms", 0) for ev in evs), default=0)


def pi_a_xdotool(doc: dict) -> list[tuple[int, list[str]]]:
    """`(t_ms, argv)` de xdotool por cada evento, en orden.

    key down/up → `keydown|keyup <keysym>` · mouse botón → `mousedown|mouseup
    n` · motion → `mousemove x y`. El runner duerme hasta `t_ms`.
    """
    plan: list[tuple[int, list[str]]] = []
    for ev in doc.get("events") or []:
        t = int(ev.get("t_ms", 0))
        if ev.get("type") == "key":
            plan.append((t, ["key" + ev["phase"], ev["keysym"]]))
        elif ev.get("type") == "mouse":
            if ev.get("button") is None:
                plan.append((t, ["mousemove", str(ev["x"]), str(ev["y"])]))
            else:
                plan.append((t, ["mouse" + ev["phase"], str(ev["button"])]))
    return plan
