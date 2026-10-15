extends SceneTree
## Motor de tests de comportamiento — scorer Capa B-1 **v2** (2026-10-14).
##
## v1 (`check_suite.gd`) sigue intacto y runnable. v2 = v1 + 5 `kind`s nuevos
## que cierran la brecha declarada en §5.2.2: v1 sólo verificaba existencia
## estructural y cinemática; v2 observa CAMBIOS en el tiempo.
##
## REGLA (GameDevBench §2.2): cada test verifica UNA feature pedida
## explícitamente en la instrucción de la tarea. Nada inventado.
## REGLA 2: se EJECUTA el juego. Nunca se hace `grep` sobre el código.
##
## Configuración: lee `res://_checks.json`, escrito por `suite_runner_v2.py`.
## Salida: `VALIDATION_PASSED` / `VALIDATION_FAILED` + M = pass/total.
##
## Los 5 `kind`s NUEVOS (§5.2.2):
##   hud_value_changes  — el número de un Label CAMBIA tras una acción
##   state_after_action — una propiedad de un nodo CAMBIA tras una acción
##   wait_accumulates   — un contador CRECE sin input (Idle/Simulation)
##   reaches_state      — un indicador de final SE HACE VISIBLE al conducir
##   restart_resets     — reiniciar RESETea el estado observado
##
## A/B (§5.2.2.b, 2026-10-15 — huecos con paper detrás, v2 aún sin ratificar):
##   resource_within_bounds — un valor NO desborda su cota (SAGE: *resource
##                            overflow*). Se muestrea cada frame de física.
##   no_runtime_errors      — NO es de este motor: lo sintetiza el runner
##                            (suite_runner_v2.py) escaneando `SCRIPT ERROR:`.
##                            Si llega aquí, se emite FAIL ruidoso (kind desconocido).
##
## Límite declarado: `reaches_state` y `restart_resets` verifican el ALAMBRE
## (que el final es alcanzable y se muestra, que el reinicio resetea), no que
## una IA sepa ganar. El techo de frames sigue vigente.

var cfg: Dictionary = {}
var checks: Array = []
var results: Array = []
var scene: Node = null
var player: Node2D = null
var target: Node = null
var cam: Camera2D = null

# --- estado del chequeo de comportamiento en curso ---
var pend: Array = []
var pi := 0
var frames := 0
var x0 := 0.0
var y0 := 0.0
var y_start := 0.0
var jump_best := 0.0
var cam_dist := 0.0
var action := ""
var total_frames := 0
var last_phys := -1
var main_scene_path := "res://main.tscn"

## Techo de seguridad contra colgadas (NO es presupuesto científico).
## v1 usaba 900 frames globales; con 5 kind's v2 (150-320 frames cada uno) eso
## se queda corto y el último check queda "no evaluado". Se sube y se DECLARA.
## El presupuesto real por check va en cada `frames:` de la suite.

# --- estado específico de los kind's v2 ---
var v2_snap := {}        # muestra inicial del check v2 en curso
var v2_restart_mid := {} # muestra intermedia para restart_resets
const MAX_FRAMES := 6000

const V2_KINDS := ["hud_value_changes", "state_after_action",
					"wait_accumulates", "reaches_state", "restart_resets",
					"resource_within_bounds"]
const STATIC_KINDS := ["build", "node_exists", "node_is", "canvas",
					"label_match", "scene_count", "has_method", "collision"]

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
	print("=== CAPA B-1 v2 · tarea: %s ===" % str(cfg.get("task", "?")))

	if cfg.has("main_scene"):
		main_scene_path = str(cfg["main_scene"])
	else:
		var ps = ProjectSettings.get_setting("application/run/main_scene", "res://main.tscn")
		if ps != "":
			main_scene_path = ps
	print("   escena principal: %s" % main_scene_path)

	for c in checks:
		var kind = str(c.get("kind", ""))
		if kind in STATIC_KINDS:
			_run_static(c)

	for c in checks:
		var kind2 = str(c.get("kind", ""))
		if kind2 in ["moves", "jump", "camera_follows", "falls", "lands", "settles"] \
				or kind2 in V2_KINDS:
			pend.append(c)
		elif kind2 != "" and not (kind2 in STATIC_KINDS):
			# fallback ruidoso: un kind desconocido FALLA con su nombre en vez
			# de colarse en silencio (p. ej. no_runtime_errors, que es del runner)
			_emit(false, str(c.get("id", "?")), "kind no soportado por el motor: " + kind2)

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
				_emit(true, id, desc + " — " + n.name)

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
			_emit(n4 != null, id, desc + (" — " + n4.name if n4 else " — sin CanvasLayer"))

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
	if scene == null:
		var packed = load(main_scene_path)
		if packed == null:
			for c in pend:
				_emit(false, str(c.get("id", "?")), "escena no cargable")
			_finish()
			return
		scene = packed.instantiate()
		root.add_child(scene)

	# v2: NO se resuelve el target aquí. Los juegos que crean nodos en _ready()
	# no los tienen todavía durante _initialize. Se resuelve en frames==1, ya
	# con _ready() corrido. Esto hace v2 robusto tanto a nodos en .tscn como a
	# nodos creados por script.
	jump_best = 0.0
	cam_dist = 0.0
	action = str(pend[0].get("action", "ui_right"))

## Resuelve el nodo bajo prueba (una vez, en frames==1).
func _resolve_target() -> bool:
	var c0: Dictionary = pend[pi]
	target = _find_by_names(c0.get("names", ["Player", "Jugador"]))
	if target == null:
		target = _find_player(scene)
	var needs_target := str(c0.get("kind", "")) in ["moves", "jump", "falls", "lands", "settles", "camera_follows"]
	if target == null and needs_target:
		for i in range(pi, pend.size()):
			_emit(false, str(pend[i].get("id", "?")), "sin nodo bajo prueba")
		_finish()
		return false
	if target != null and player == null and target is Node2D and _looks_like_player(target):
		player = target
	var cf = _find_by_type("Camera2D")
	if cf != null:
		cam = cf
	if target != null and target is Node2D:
		x0 = target.global_position.x
		y0 = target.global_position.y
		print("   nodo bajo prueba: %s @ (%.1f, %.1f)" % [target.name, x0, y0])
	return true

## Muestra inicial según el kind del check en curso.
func _begin_check(c: Dictionary) -> void:
	v2_snap = {}
	v2_restart_mid = {}
	var kind = str(c.get("kind", ""))
	match kind:
		"hud_value_changes", "wait_accumulates":
			v2_snap["label"] = _label_number(c.get("label", []))
		"state_after_action":
			v2_snap["prop"] = _read_prop(c)
		"reaches_state":
			v2_snap["visible"] = _visible_indicator(c)
		"restart_resets":
			v2_snap["label"] = _label_number(c.get("watch_label", []))
			if target != null and target is Node2D:
				v2_snap["pos"] = target.global_position
		"resource_within_bounds":
			v2_snap = {"n": 0, "bad": NAN, "bad_frame": -1, "peak": NAN}

func _process(_delta: float) -> bool:
	total_frames += 1
	if total_frames > MAX_FRAMES:
		print("[WARN] techo de %d frames alcanzado — se reporta parcial" % MAX_FRAMES)
		for i in range(pi, pend.size()):
			_emit(false, str(pend[i].get("id", "?")),
				"no evaluado — techo de frames (" + str(pend[i].get("kind", "")) + ")")
		_finish()
		return true

	# v2: el progreso del check se ata a los frames de FÍSICA, no a los de
	# _process. En headless _process corre varias veces por tick de física, y el
	# juego sólo avanza en física. Así `frames:` significa pasos de física.
	var phys := Engine.get_physics_frames()
	if phys == last_phys:
		return false
	last_phys = phys
	frames += 1

	if not pend.is_empty() and pi < pend.size():
		var c: Dictionary = pend[pi]
		var kind = str(c.get("kind", ""))
		var nframes = int(c.get("frames", 45))

		# frames==1: _ready() ya corrió → resolver target y muestrear estado inicial
		if frames == 1:
			if not _resolve_target():
				return true
			if kind in V2_KINDS:
				_begin_check(c)

		if frames == 5:
			if kind == "moves":
				Input.action_press(str(c.get("action", "ui_right")))
			elif kind == "jump":
				Input.action_press("ui_accept")
			elif kind == "camera_follows":
				if cam != null:
					cam_dist = cam.global_position.distance_to(target.global_position)
			elif kind == "falls":
				target.global_position.y -= float(c.get("rise", 300.0))
				y_start = target.global_position.y
			elif kind in ["lands", "settles"]:
				y_start = target.global_position.y
			elif kind == "hud_value_changes":
				Input.action_press(str(c.get("action", "ui_right")))
			elif kind == "state_after_action":
				Input.action_press(str(c.get("action", "ui_right")))
			elif kind == "reaches_state":
				Input.action_press(str(c.get("action", "ui_right")))
			elif kind == "restart_resets":
				# fase 1: conducir hacia el estado de juego
				var da = str(c.get("drive_action", ""))
				if da != "":
					Input.action_press(da)

		# restart_resets: en el punto medio se pulsa el reinicio
		if kind == "restart_resets" and frames == (nframes / 2):
			var da2 = str(c.get("drive_action", ""))
			if da2 != "":
				Input.action_release(da2)
			v2_restart_mid["label"] = _label_number(c.get("watch_label", []))
			if target != null:
				v2_restart_mid["pos"] = target.global_position
			var ra = str(c.get("restart_action", "ui_accept"))
			Input.action_press(ra)

		if kind == "jump" and frames > 5 and frames < 25:
			var dy = y0 - target.global_position.y
			if dy > jump_best:
				jump_best = dy

		# resource_within_bounds: se muestrea CADA frame de física (sin input)
		if kind == "resource_within_bounds":
			var v = _read_bound_value(c)
			if not is_nan(v):
				v2_snap["n"] = int(v2_snap.get("n", 0)) + 1
				var pk = float(v2_snap.get("peak", NAN))
				if is_nan(pk) or v > pk:
					v2_snap["peak"] = v
				if is_nan(float(v2_snap.get("bad", NAN))):
					var vmax_b = float(c.get("max", INF))
					var vmin_b = float(c.get("min", -INF))
					if v > vmax_b or v < vmin_b:
						v2_snap["bad"] = v
						v2_snap["bad_frame"] = frames

		if frames == nframes:
			_resolve_check(c, kind, nframes)
			pi += 1
			frames = 0
			jump_best = 0.0
			if pi >= pend.size():
				_finish()
				return true
			if target != null and target is Node2D:
				target.global_position = Vector2(x0, y0)
				if target is CharacterBody2D:
					target.velocity = Vector2.ZERO
			if cam != null and target != null:
				cam_dist = cam.global_position.distance_to(target.global_position)
			# v2: el muestreo inicial del siguiente check ocurre en su frames==1,
			# ya con _ready() y la posición reseteadas. No se muestrea aquí.
	return false

## Resuelve el check en curso al llegar a `frames == nframes`.
func _resolve_check(c: Dictionary, kind: String, nframes: int) -> void:
	var id := str(c.get("id", "?"))
	var desc := str(c.get("desc", ""))

	match kind:
		"moves":
			Input.action_release(str(c.get("action", "ui_right")))
			var dx = abs(target.global_position.x - x0)
			_emit(dx > 1.0, id, "%s — dx=%.2f px en %d frames" % [desc, dx, nframes])
		"jump":
			Input.action_release("ui_accept")
			_emit(jump_best > 1.0, id, "%s — subida máx %.2f px" % [desc, jump_best])
		"camera_follows":
			if cam == null:
				_emit(false, id, desc + " — sin Camera2D")
			else:
				var dnow = cam.global_position.distance_to(target.global_position)
				_emit(abs(dnow - cam_dist) < 1.0 or dnow < 50.0, id,
					"%s — dist cámara→jugador %.1f → %.1f" % [desc, cam_dist, dnow])
		"falls":
			Input.action_release(str(c.get("action", "ui_right")))
			var dyf = target.global_position.y - y_start
			_emit(dyf > 10.0, id, "%s — cayó %.1f px tras teleport arriba" % [desc, dyf])
		"lands", "settles":
			var landed = false
			if target is CharacterBody2D:
				landed = target.is_on_floor()
			var fallen = target.global_position.y - y_start
			_emit(landed, id, "%s — is_on_floor=%s · descenso %.1f px" % [desc, landed, fallen])

		# ---------------- kind's v2 ----------------
		"hud_value_changes":
			Input.action_release(str(c.get("action", "ui_right")))
			var after = _label_number(c.get("label", []))
			var before = v2_snap.get("label", NAN)
			if is_nan(before) or is_nan(after):
				_emit(false, id, "%s — no pude leer un número del HUD (antes=%s ahora=%s)"
					% [desc, str(before), str(after)])
			else:
				_emit(abs(after - before) > 0.001, id,
					"%s — valor del HUD %.3f → %.3f (Δ=%.3f)" % [desc, before, after, after - before])

		"state_after_action":
			Input.action_release(str(c.get("action", "ui_right")))
			var p_after = _read_prop(c)
			var p_before = v2_snap.get("prop", null)
			if p_before == null or p_after == null:
				_emit(false, id, "%s — no pude leer la propiedad '%s'"
					% [desc, str(c.get("property", "?"))])
			else:
				_emit(str(p_before) != str(p_after), id,
					"%s — propiedad %s: %s → %s" % [desc, str(c.get("property", "?")), str(p_before), str(p_after)])

		"wait_accumulates":
			# deliberadamente SIN input: mide acumulación pasiva
			var acc_after = _label_number(c.get("label", []))
			var acc_before = v2_snap.get("label", NAN)
			if is_nan(acc_before) or is_nan(acc_after):
				_emit(false, id, "%s — no pude leer un número (antes=%s ahora=%s)"
					% [desc, str(acc_before), str(acc_after)])
			else:
				_emit(acc_after > acc_before, id,
					"%s — acumulación pasiva %.3f → %.3f en %d frames sin input"
					% [desc, acc_before, acc_after, nframes])

		"reaches_state":
			Input.action_release(str(c.get("action", "ui_right")))
			var found = _visible_indicator(c)
			var was = str(v2_snap.get("visible", ""))
			if found == "":
				_emit(false, id, "%s — ningún indicador de final VISIBLE tras conducir %d frames (inicial: %s)"
					% [desc, nframes, ("'" + was + "'" if was != "" else "nada")])
			else:
				_emit(true, id, "%s — indicador final visible: '%s' (inicial: %s)"
					% [desc, found, ("'" + was + "'" if was != "" else "nada")])

		"resource_within_bounds":
			var vmax = float(c.get("max", INF))
			var vmin = float(c.get("min", -INF))
			var ns = int(v2_snap.get("n", 0))
			var bad = float(v2_snap.get("bad", NAN))
			if ns == 0:
				_emit(false, id, "%s — no pude leer el valor observado en %d frames"
					% [desc, nframes])
			elif not is_nan(bad):
				_emit(false, id, "%s — COTA EXCEDIDA: %.3f fuera de [%.3f, %.3f] en el frame %d (%d muestras)"
					% [desc, bad, vmin, vmax, int(v2_snap.get("bad_frame", -1)), ns])
			else:
				_emit(true, id, "%s — %d muestras dentro de [%.3f, %.3f] (pico %.3f)"
					% [desc, ns, vmin, vmax, float(v2_snap.get("peak", NAN))])

		"restart_resets":
			var ra = str(c.get("restart_action", "ui_accept"))
			Input.action_release(ra)
			var r_after = _label_number(c.get("watch_label", []))
			var r_mid = v2_restart_mid.get("label", NAN)
			var ok := false
			var evidence := ""
			if not is_nan(r_mid) and not is_nan(r_after):
				# el valor observado debe bajar tras reiniciar
				ok = r_after < r_mid
				evidence = "valor %s: %.3f (pre-reinicio) → %.3f (post)" % [
					str(c.get("watch_label", [])), r_mid, r_after]
			else:
				# sin label numérico: se observa si el jugador volvió al spawn
				if target != null and v2_snap.has("pos"):
					var p_start: Vector2 = v2_snap["pos"]
					var dist_now = target.global_position.distance_to(p_start)
					ok = dist_now < 5.0
					evidence = "distancia al spawn inicial %.1f px" % dist_now
				else:
					ok = false
					evidence = "sin target ni label observables"
			_emit(ok, id, "%s — %s" % [desc, evidence])

# ---- utilidades ----

func _label_number(needles) -> float:
	"""Número del primer Label visible cuyo texto coincide con alguna aguja."""
	var n := _find_visible_label_number(needles)
	return n

func _find_visible_label_number(needles) -> float:
	if scene == null:
		return NAN
	var r = _scan_labels_for_number(scene, _as_list(needles))
	return r

func _as_list(v) -> Array:
	if v == null:
		return []
	if v is Array:
		return v
	if v is String and v != "":
		return [v]
	return []

func _scan_labels_for_number(n: Node, needles: Array) -> float:
	if n is Label and n.is_visible_in_tree():
		var t: String = n.text.to_lower()
		for nd in needles:
			if str(nd).to_lower() in t:
				var num = _first_number(n.text)
				if not is_nan(num):
					return num
	for c in n.get_children():
		var r = _scan_labels_for_number(c, needles)
		if not is_nan(r):
			return r
	return NAN

func _first_number(s: String) -> float:
	var re := RegEx.new()
	re.compile("-?\\d+(\\.\\d+)?")
	var m = re.search(s)
	if m:
		return float(m.get_string())
	return NAN

func _read_prop(c: Dictionary):
	"""Lee una propiedad arbitraria de un nodo (para state_after_action)."""
	var n = _find_by_names(c.get("names", []))
	if n == null:
		return null
	var prop = str(c.get("property", ""))
	if prop == "":
		return null
	if not prop in n:
		return null
	return n.get(prop)

func _read_bound_value(c: Dictionary) -> float:
	"""Valor numérico observado: propiedad de un nodo, o número de un Label."""
	if str(c.get("property", "")) != "":
		var v = _read_prop(c)
		if v is float or v is int:
			return float(v)
		return NAN
	return _label_number(c.get("label", c.get("watch_label", [])))

func _visible_indicator(c: Dictionary) -> String:
	"""Devuelve el texto de un indicador de final VISIBLE, o "" si no hay ninguno."""
	if scene == null:
		return ""
	# 1) Labels visibles cuyo texto coincide con las agujas de final
	var texts := _as_list(c.get("texts", c.get("text", [])))
	if texts.size() > 0:
		var found = _find_visible_label_text(scene, texts)
		if found != "":
			return found
	# 2) Nodos visibles cuyo nombre coincide (y que estén en pantalla)
	var names := _as_list(c.get("names", []))
	for nm in names:
		var n = _find_by_name(scene, str(nm).to_lower())
		if n != null and n.is_visible_in_tree():
			return n.name
	return ""

func _find_visible_label_text(n: Node, needles: Array) -> String:
	if n is Label and n.is_visible_in_tree():
		var t: String = n.text.to_lower()
		for nd in needles:
			if str(nd).to_lower() in t:
				return n.text
	for c in n.get_children():
		var r = _find_visible_label_text(c, needles)
		if r != "":
			return r
	return ""

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
