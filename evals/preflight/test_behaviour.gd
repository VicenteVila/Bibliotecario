extends SceneTree
## Preflight del scorer de Capa B — FASE B-1.
## Fuente del método: GameDevBench §3.2 — "directly test game behavior".
##
## REGLA: no se evalúa el código. Se ejecuta el juego y se observa.
## Un `grep "move_and_slide"` aprobaría un juego con la función escrita
## pero nunca conectada. Este script la ejecuta y MIDE el desplazamiento.
##
## Uso:
##   EG/.tools/godot --headless --path <proyecto_del_juego> \
##                   --script <ruta/a/este/test_behaviour.gd>
##
## Salida: línea `VALIDATION_PASSED` o `VALIDATION_FAILED` (GameDevBench).
## Exit code: 0 si pasa, 1 si falla.
##
## Preflight 2026-10-14: 5/5 PASS sobre workspace/current de ReaGame,
## dx=85.00 px. ReaGame NO fue modificado (copia temporal).

var frames := 0
var player: Node2D = null
var scene: Node = null
var x0 := 0.0
var results: Array = []

func _initialize() -> void:
	print("=== PREFLIGHT CAPA B-1 — test de comportamiento en Godot ===")
	var packed = load("res://main.tscn")
	if packed == null:
		_emit(false, "C1 carga de main.tscn", "no se pudo cargar res://main.tscn")
		_finish()
		return
	scene = packed.instantiate()
	root.add_child(scene)

	# --- C1: el proyecto arranca y tiene un nodo jugador ---
	player = _find_player(scene)
	_emit(player != null, "C1 el proyecto arranca y hay un nodo jugador",
		"jugador encontrado: %s" % player.name if player else "sin nodo jugador")

	if player == null:
		_finish()
		return

	# --- C2: es CharacterBody2D (física real, no Area2D decorativo) ---
	_emit(player is CharacterBody2D, "C2 el jugador es CharacterBody2D",
		"tipo real: %s" % player.get_class())

	# --- C3: tiene move_and_slide (comportamiento, no presencia de texto) ---
	_emit(player.has_method("move_and_slide"), "C3 el jugador tiene move_and_slide")

	# --- C4: las acciones de input están registradas ---
	var left := InputMap.has_action("ui_left")
	var right := InputMap.has_action("ui_right")
	var jump := InputMap.has_action("ui_accept")
	_emit(left and right and jump, "C4 acciones ui_left/ui_right/ui_accept registradas",
		"left=%s right=%s jump=%s" % [left, right, jump])

	x0 = player.global_position.x
	print("   posición inicial x=%.2f y=%.2f" % [x0, player.global_position.y])

func _process(_delta: float) -> bool:
	frames += 1

	# empujamos input durante 40 frames de física
	if frames == 5:
		Input.action_press("ui_right")
	if frames == 45:
		Input.action_release("ui_right")

	if frames == 50:
		if player == null:
			_finish()
			return true
		var x1 = player.global_position.x
		var dx = abs(x1 - x0)
		# --- C5: el jugador se MUEVE bajo input. Éste es el test de comportamiento ---
		_emit(dx > 1.0, "C5 el jugador se mueve bajo input (comportamiento observado)",
			"dx=%.2f px en 40 frames (x0=%.2f -> x1=%.2f)" % [dx, x0, x1])
		_finish()
		return true
	return false

func _find_player(n: Node) -> Node2D:
	if n is Node2D and (n.name.to_lower().contains("player") or n.name.to_lower().contains("jugador")):
		return n
	for c in n.get_children():
		var r = _find_player(c)
		if r != null:
			return r
	return null

func _emit(ok: bool, name: String, detail := "") -> void:
	results.append({"ok": ok, "name": name})
	print("[%s] %s%s" % ["PASS" if ok else "FAIL", name, (" — " + detail) if detail != "" else ""])

func _finish() -> void:
	var n_pass = 0
	for r in results:
		if r["ok"]:
			n_pass += 1
	print("")
	print("=== RESULTADO: %d/%d tests de comportamiento PASAN ===" % [n_pass, results.size()])
	var all_ok = n_pass == results.size() and results.size() > 0
	print("VALIDATION_%s" % ("PASSED" if all_ok else "FAILED"))
	quit(0 if all_ok else 1)
