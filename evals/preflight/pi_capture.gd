extends Node
## HITO15 §1.1 — persistidor de las trazas Π (copia temporal, ReaGame intacto).
##
## Fuente de verdad: los eventos que declara `pi_actor` (política
## guionizada). El hook `_input` solo cubre sesiones humanas futuras —
## `Input.action_press` emite `InputEventAction`, no `InputEventKey`, así
## que no hay doble registro. Escribe `res://_pi.json` y cierra el árbol.

const XSYM_TECLAS := {
	KEY_LEFT: "Left",
	KEY_RIGHT: "Right",
	KEY_UP: "Up",
	KEY_DOWN: "Down",
	KEY_SPACE: "space",
	KEY_ESCAPE: "Escape",
}

var eventos: Array = []
var _fin := false


func record(ev: Dictionary) -> void:
	if _fin:
		return
	eventos.append(ev)


func _input(event: InputEvent) -> void:
	if event is InputEventKey:
		var xsym: String = XSYM_TECLAS.get(event.keycode, "")
		if xsym == "":
			return  # tecla fuera del subconjunto declarado (etapa 1)
		record({"t_ms": Time.get_ticks_msec(), "type": "key", "action": "",
			"keysym": xsym,
			"phase": "down" if event.pressed else "up"})
	elif event is InputEventMouseButton and event.button_index <= 3:
		record({"t_ms": Time.get_ticks_msec(), "type": "mouse",
			"button": int(event.button_index),
			"phase": "down" if event.pressed else "up",
			"x": int(event.position.x), "y": int(event.position.y)})


func finish() -> void:
	if _fin:
		return
	_fin = true
	var f := FileAccess.open("res://_pi.json", FileAccess.WRITE)
	if f == null:
		push_error("PiCapture: no se pudo escribir res://_pi.json")
	else:
		f.store_string(JSON.stringify(
			{"version": 1, "fps": 60, "events": eventos}, "  "))
	get_tree().quit()
