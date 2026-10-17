extends Node
## HITO15 §1.2 — política guionizada (demos guionizadas, decisión del dueño).
##
## Lee `res://_pi_script.json` y ejecuta pasos `{wait: N}` o
## `{action: ui_*, hold: N}` en ticks de física (60 fps). El timestamp de Π
## es `t_ms = tick * 1000 / 60` (entero, determinista — sin reloj de
## pared): dos capturas con el mismo script producen la misma secuencia.
## Techo de seguridad: 1200 ticks (20 s, límite GameCraft §3.2).

const FPS := 60
const TICKS_MAX := 1200
## Tabla congelada HITO15 §3 — debe coincidir con `UI_TO_XSYM` de
## `pi_schema.py` (el validador python los cross-checkea en tests).
const UI_XSYM := {
	"ui_left": "Left",
	"ui_right": "Right",
	"ui_up": "Up",
	"ui_down": "Down",
	"ui_accept": "space",
	"ui_cancel": "Escape",
}

var _steps: Array = []
var _i := 0
var _left := 0
var _tick := 0
var _cur := ""
var _fin := false


func _ready() -> void:
	var f := FileAccess.open("res://_pi_script.json", FileAccess.READ)
	if f == null:
		push_error("pi_actor: falta res://_pi_script.json")
		set_physics_process(false)
		return
	var doc = JSON.parse_string(f.get_as_text())
	if doc == null or not (doc is Dictionary) or not doc.has("steps"):
		push_error("pi_actor: _pi_script.json sin steps")
		set_physics_process(false)
		return
	_steps = doc["steps"]
	_arranca_paso()
	set_physics_process(true)


func _t_ms() -> int:
	return int(_tick * 1000 / FPS)


func _arranca_paso() -> void:
	if _i >= _steps.size():
		_fin = true
		PiCapture.finish()
		return
	var st = _steps[_i]
	if st.has("action"):
		_cur = str(st["action"])
		if not UI_XSYM.has(_cur):
			push_error("pi_actor: accion fuera de tabla: " + _cur)
			_cur = ""
			_fin = true
			PiCapture.finish()
			return
		Input.action_press(_cur)
		PiCapture.record({"t_ms": _t_ms(), "type": "key", "action": _cur,
			"keysym": UI_XSYM[_cur], "phase": "down"})
	else:
		_cur = ""
	_left = int(st.get("hold", st.get("wait", 0)))


func _physics_process(_delta: float) -> void:
	if _fin:
		return
	_tick += 1
	if _tick > TICKS_MAX:
		_fin = true
		PiCapture.finish()
		return
	if _left <= 0:
		return
	_left -= 1
	if _left > 0:
		return
	if _cur != "":
		Input.action_release(_cur)
		PiCapture.record({"t_ms": _t_ms(), "type": "key", "action": _cur,
			"keysym": UI_XSYM[_cur], "phase": "up"})
		_cur = ""
	_i += 1
	_arranca_paso()
