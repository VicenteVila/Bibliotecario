extends SceneTree
## Motor de tests de comportamiento — scorer Capa B-1 (RATIFICADO 2026-10-14).
##
## REGLA (GameDevBench §2.2): cada test verifica UNA feature pedida
## explícitamente en la instrucción de la tarea. Nada inventado.
##
## REGLA 2: se EJECUTA el juego. Nunca se hace `grep` sobre el código.
##
## Configuración: lee `res://_checks.json`, escrito por `suite_runner.py`.
## Salida: `VALIDATION_PASSED` / `VALIDATION_FAILED` + M = pass/total.
##
## Congelado (§11): motor Godot 4.7.1 · este fichero · comando de ejecución.
## Una vez escrita una suite, NO se modifica sin declarar benchmark nuevo.

var cfg: Dictionary = {}
var checks: Array = []
var results: Array = []
var scene: Node = null
var player: Node2D = null
var target: Node2D = null
var cam: Camera2D = null

# --- estado del chequeo de comportamiento en curso ---
var pend: Array = []
var pi := 0
var frames := 0
var x0 := 0.0
var y0 := 0.0
var y_start := 0.0   # posición desde la que se mide una caída (tras teleport)
var jump_best := 0.0
var cam_dist := 0.0
var action := ""
var total_frames := 0
var main_scene_path := "res://main.tscn"
## Techo duro: el motor NUNCA se cuelga. Si se supera, se reporta lo que haya.
const MAX_FRAMES := 900
func _initialize() -> void:
	var f = FileAccess.open("res://_checks.json", FileAccess.READ)
	if f == null:
		print("[FAIL] _check_build — no se pudo leer res://_checks.json")
		_emit(false, "_check_config", "falta res://_checks.json")
		_finish()
		return
	var parsed = JSON.parse_string(f.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		_emit(false, "_check_config", "JSON inválido")
		_finish()
		return
	cfg = parsed
	checks = cfg.get("checks", [])
	print("=== CAPA B-1 · tarea: %s ===" % str(cfg.get("task", "?")))

	# ---- FASE ESTÁTICA ----
	# la escena a probar: la del propio proyecto (run/main_scene), salvo override
	if cfg.has("main_scene"):
		main_scene_path = str(cfg["main_scene"])
	else:
		var ps = ProjectSettings.get_setting("application/run/main_scene", "res://main.tscn")
		if ps != "":
			main_scene_path = ps
	print("   escena principal: %s" % main_scene_path)

	for c in checks:
		var kind = str(c.get("kind", ""))
		if kind in ["build", "node_exists", "node_is", "canvas",
					"label_match", "scene_count", "has_method", "collision"]:
			_run_static(c)

	# ---- FASE DE COMPORTAMIENTO ----
	for c in checks:
		var kind2 = str(c.get("kind", ""))
		if kind2 in ["moves", "jump", "camera_follows", "falls", "lands", "settles"]:
			pend.append(c)

	if pend.is_empty():
		_finish()
		return
	_begin_behaviour()

func _run_static(c: Dictionary) -> void:
	var kind = str(c.get("kind", ""))
	var id = str(c.get("id", "?"))
	var desc = str(c.get("desc", ""))

	match kind:
		"build":
			var packed = load(main_scene_path)
			if packed == null:
				_emit(false, id, desc + " — no se pudo cargar %s" % main_scene_path)
				return
			scene = packed.instantiate()
			root.add_child(scene)
			_emit(true, id, desc + " — %s" % main_scene_path)

		"node_exists":
			var n = _find_by_names(c.get("names", []))
			if n == null:
				_emit(false, id, desc + " — no encontrado. nombres: %s" % str(c.get("names", [])))
			else:
				if player == null and _looks_like_player(n):
					player = n
				_emit(true, id, desc + " — %s" % n.name)

		"node_is":
			var n2 = _find_by_names(c.get("names", []))
			if n2 == null:
				_emit(false, id, desc + " — nodo no encontrado")
				return
			var want = str(c.get("is", ""))
			var ok = false
			match want:
				"CharacterBody2D": ok = n2 is CharacterBody2D
				"Area2D": ok = n2 is Area2D
				"RigidBody2D": ok = n2 is RigidBody2D
				"StaticBody2D": ok = n2 is StaticBody2D
				"Node2D": ok = n2 is Node2D
				"CanvasLayer": ok = n2 is CanvasLayer
				"Camera2D": ok = n2 is Camera2D
				"Label": ok = n2 is Label
				"Sprite2D": ok = n2 is Sprite2D
				"AnimatedSprite2D": ok = n2 is AnimatedSprite2D
				"TileMap": ok = n2 is TileMap
				"TileMapLayer": ok = n2 is TileMapLayer
			_emit(ok, id, desc + " — tipo real: %s · esperado %s" % [n2.get_class(), want])

		"has_method":
			var n3 = _find_by_names(c.get("names", []))
			if n3 == null:
				_emit(false, id, desc + " — nodo no encontrado")
				return
			var m = str(c.get("method", ""))
			_emit(n3.has_method(m), id, desc + " — %s.has_method(%s)" % [n3.name, m])

		"canvas":
			var n4 = _find_by_type("CanvasLayer")
			_emit(n4 != null, id, desc + (" — %s" % n4.name if n4 else " — sin CanvasLayer"))

		"label_match":
			var needle = str(c.get("text", "")).to_lower()
			var found = _find_label_text(needle)
			_emit(found != "", id, desc + (" — '%s'" % found if found != "" else " — ningún Label contiene '%s'" % needle))

		"scene_count":
			var want2 = int(c.get("min", 1))
			var have = 0
			var d = DirAccess.open("res://")
			if d != null:
				d.list_dir_begin()
				var fn = d.get_next()
				while fn != "":
					if fn.ends_with(".tscn"):
						have += 1
					fn = d.get_next()
			_emit(have >= want2, id, desc + " — %d escenas .tscn (mínimo %d)" % [have, want2])

		"collision":
			var n5 = _find_by_names(c.get("names", []))
			if n5 == null:
				_emit(false, id, desc + " — nodo no encontrado")
				return
			var is_body = n5 is CollisionObject2D
			_emit(is_body, id, desc + (" — %s con capa %d" % [n5.name, n5.collision_layer] if is_body else " — %s sin CollisionObject2D" % n5.name))

# ---- FASE DE COMPORTAMIENTO ----

func _begin_behaviour() -> void:
	# si la escena aún no existe, la cargamos
	if scene == null:
		var packed = load(main_scene_path)
		if packed == null:
			for c in pend:
				_emit(false, str(c.get("id", "?")), "escena no cargable")
			_finish()
			return
		scene = packed.instantiate()
		root.add_child(scene)

	# resolver el nodo bajo prueba
	var c0: Dictionary = pend[0]
	target = _find_by_names(c0.get("names", ["Player", "Jugador"]))
	if target == null:
		target = _find_player(scene)
	if target == null:
		for c in pend:
			_emit(false, str(c.get("id", "?")), "sin nodo bajo prueba")
		_finish()
		return
	if player == null:
		player = target

	# cámara si hace falta
	var cf = _find_by_type("Camera2D")
	if cf != null:
		cam = cf

	x0 = target.global_position.x
	y0 = target.global_position.y
	jump_best = 0.0
	cam_dist = 0.0
	action = str(c0.get("action", "ui_right"))
	print("   nodo bajo prueba: %s @ (%.1f, %.1f)" % [target.name, x0, y0])

func _process(_delta: float) -> bool:
	# --- techo duro: el motor nunca cuelga ---
	total_frames += 1
	if total_frames > MAX_FRAMES:
		print("[WARN] techo de %d frames alcanzado — se reporta parcial" % MAX_FRAMES)
		for i in range(pi, pend.size()):
			_emit(false, str(pend[i].get("id", "?")),
				"no evaluado — techo de frames (" + str(pend[i].get("kind", "")) + ")")
		_finish()
		return true

	frames += 1

	if not pend.is_empty() and pi < pend.size():
		var c: Dictionary = pend[pi]
		var kind = str(c.get("kind", ""))
		var nframes = int(c.get("frames", 45))

		if frames == 5:
			if kind == "moves":
				Input.action_press(str(c.get("action", "ui_right")))
			elif kind == "jump":
				Input.action_press("ui_accept")
			elif kind == "camera_follows":
				if cam != null:
					cam_dist = cam.global_position.distance_to(target.global_position)
			elif kind == "falls":
				# teleportar arriba: si hay gravedad, la Y debe CRECER.
				# ADVERTENCIA: sólo válido si hay espacio libre encima.
				target.global_position.y -= float(c.get("rise", 300.0))
				y_start = target.global_position.y
			elif kind == "lands" or kind == "settles":
				# SIN teleport: se espera a que el jugador asiente.
				# is_on_floor()==true implica que la gravedad lo bajó Y que la
				# colisión lo detuvo. Ambas a la vez, sin intervenir.
				y_start = target.global_position.y

		if kind == "jump" and frames > 5 and frames < 25:
			var dy = y0 - target.global_position.y
			if dy > jump_best:
				jump_best = dy

		if frames == nframes:
			if kind == "moves":
				Input.action_release(str(c.get("action", "ui_right")))
				var dx = abs(target.global_position.x - x0)
				_emit(dx > 1.0, str(c.get("id", "?")),
					"%s — dx=%.2f px en %d frames" % [str(c.get("desc", "")), dx, nframes])
			elif kind == "jump":
				Input.action_release("ui_accept")
				_emit(jump_best > 1.0, str(c.get("id", "?")),
					"%s — subida máx %.2f px" % [str(c.get("desc", "")), jump_best])
			elif kind == "camera_follows":
				if cam == null:
					_emit(false, str(c.get("id", "?")), "%s — sin Camera2D" % str(c.get("desc", "")))
				else:
					var dnow = cam.global_position.distance_to(target.global_position)
					_emit(abs(dnow - cam_dist) < 1.0 or dnow < 50.0,
						str(c.get("id", "?")),
						"%s — dist cámara→jugador %.1f → %.1f" % [str(c.get("desc", "")), cam_dist, dnow])
			elif kind == "falls":
				var dyf = target.global_position.y - y_start
				_emit(dyf > 10.0, str(c.get("id", "?")),
					"%s — cayó %.1f px tras teleport arriba" % [str(c.get("desc", "")), dyf])
			elif kind == "lands" or kind == "settles":
				# sin teleport: is_on_floor() implica gravedad + colisión a la vez
				var landed = false
				if target is CharacterBody2D:
					landed = target.is_on_floor()
				var fallen = target.global_position.y - y_start
				_emit(landed, str(c.get("id", "?")),
					"%s — is_on_floor=%s · descenso %.1f px desde el spawn" % [str(c.get("desc", "")), landed, fallen])

			pi += 1
			frames = 0
			jump_best = 0.0
			if pi >= pend.size():
				_finish()
				return true
			# resetear posición y velocidad entre pruebas de comportamiento
			target.global_position = Vector2(x0, y0)
			if target is CharacterBody2D:
				target.velocity = Vector2.ZERO
			if cam != null:
				cam_dist = cam.global_position.distance_to(target.global_position)
	return false

# ---- utilidades ----

func _find_by_names(names) -> Node:
	if scene == null:
		return null
	if names is String:
		names = [names]
	for nm in names:
		var n = _find_by_name(scene, str(nm).to_lower())
		if n != null:
			return n
	return null

func _find_by_name(n: Node, want: String) -> Node:
	if n.name.to_lower() == want or n.name.to_lower().contains(want):
		return n
	for c in n.get_children():
		var r = _find_by_name(c, want)
		if r != null:
			return r
	return null

func _find_by_type(t: String) -> Node:
	if scene == null:
		return null
	return _find_by_type_r(scene, t)

func _find_by_type_r(n: Node, t: String) -> Node:
	if n.get_class() == t:
		return n
	for c in n.get_children():
		var r = _find_by_type_r(c, t)
		if r != null:
			return r
	return null

func _find_label_text(needle: String) -> String:
	if scene == null:
		return ""
	return _find_label_r(scene, needle)

func _find_label_r(n: Node, needle: String) -> String:
	if n is Label:
		var t = n.text.to_lower()
		if needle == "" or t.contains(needle):
			return n.text
	for c in n.get_children():
		var r = _find_label_r(c, needle)
		if r != "":
			return r
	return ""

func _find_player(n: Node) -> Node2D:
	if n is Node2D and (n.name.to_lower().contains("player") or n.name.to_lower().contains("jugador")):
		return n
	for c in n.get_children():
		var r = _find_player(c)
		if r != null:
			return r
	return null

func _looks_like_player(n: Node) -> bool:
	var s = n.name.to_lower()
	return s.contains("player") or s.contains("jugador") or s.contains("heroe") or s.contains("héroe")

func _emit(ok: bool, id: String, desc := "") -> void:
	results.append({"ok": ok, "id": id})
	print("[%s] %s%s" % ["PASS" if ok else "FAIL", id, (" — " + desc) if desc != "" else ""])

func _finish() -> void:
	var n_pass = 0
	for r in results:
		if r["ok"]:
			n_pass += 1
	var total = results.size()
	print("")
	print("=== M = %d/%d ===" % [n_pass, total])
	# BUILD: si la escena no cargó, nota final 0 (cero, no techo)
	var build_ok = false
	for r in results:
		if str(r["id"]).begins_with("_check_build") or str(r["id"]) == "build":
			build_ok = r["ok"]
	if not build_ok and not scene:
		print("BUILD = 0 → SCORE = 0")
		print("VALIDATION_FAILED")
		quit(1)
		return
	print("VALIDATION_%s" % ("PASSED" if n_pass == total and total > 0 else "FAILED"))
	quit(0 if n_pass == total and total > 0 else 1)
