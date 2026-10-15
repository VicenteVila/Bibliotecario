extends Node2D
## Fixture de validación del scorer Capa B-1 **v2**.
##
## Juego sintético que ejercita los 5 `kind`s nuevos:
##   · hud_value_changes  — recoger la moneda sube el contador del HUD
##   · state_after_action — pulsar ui_up baja el maná
##   · wait_accumulates   — un temporizador suma monedas pasivas SIN input
##   · reaches_state      — alcanzar la meta muestra la etiqueta VICTORIA
##   · restart_resets     — reiniciar pone el marcador a cero
##
## `BROKEN = true` deja la ESCENA idéntica (mismos nodos, mismos nombres) pero
## sin cablear la lógica: el HUD queda congelado, no hay ingreso pasivo, la
## victoria nunca se muestra y el reinicio no resetea. Eso permite verificar que
## los kind's v2 DISCRIMINAN: PASS contra v2_ok, FAIL contra v2_broken.

const BROKEN := true

var player: CharacterBody2D
var coin: Area2D
var win_label: Label
var score_label: Label
var mana_label: Label
var passive_label: Label
var respawn: Timer
var passive_timer: Timer
var cam: Camera2D

var score := 0
var charge := 0.0
var mana := 10
var passive := 0

func _ready() -> void:
	if not InputMap.has_action("restart"):
		InputMap.add_action("restart")
		var ev := InputEventKey.new()
		ev.physical_keycode = KEY_R
		InputMap.action_add_event("restart", ev)

	# suelo
	var floor_body := StaticBody2D.new()
	floor_body.name = "Floor"
	var fshape := CollisionShape2D.new()
	var frect := RectangleShape2D.new()
	frect.size = Vector2(4000, 40)
	fshape.shape = frect
	floor_body.add_child(fshape)
	floor_body.position = Vector2(0, 200)
	add_child(floor_body)

	# jugador — arranca a la izquierda de la moneda
	player = CharacterBody2D.new()
	player.name = "Player"
	var pshape := CollisionShape2D.new()
	var prect := RectangleShape2D.new()
	prect.size = Vector2(32, 32)
	pshape.shape = prect
	player.add_child(pshape)
	player.position = Vector2(-400, 100)
	add_child(player)

	# moneda — a la derecha del spawn, se recoge al avanzar
	coin = Area2D.new()
	coin.name = "Coin"
	var cshape := CollisionShape2D.new()
	var ccirc := CircleShape2D.new()
	ccirc.radius = 18.0
	cshape.shape = ccirc
	coin.add_child(cshape)
	coin.position = Vector2(-280, 160)
	coin.body_entered.connect(_on_coin)
	add_child(coin)

	# meta — más a la derecha, alcanzable conduciendo
	var goal := Area2D.new()
	goal.name = "Goal"
	var gshape := CollisionShape2D.new()
	var grect := RectangleShape2D.new()
	grect.size = Vector2(40, 200)
	gshape.shape = grect
	goal.add_child(gshape)
	goal.position = Vector2(200, 100)
	goal.body_entered.connect(_on_goal)
	add_child(goal)

	# HUD
	var hud := CanvasLayer.new()
	hud.name = "HUD"
	add_child(hud)
	score_label = _mk_label(hud, "ScoreLabel", Vector2(10, 10))
	mana_label = _mk_label(hud, "ManaLabel", Vector2(10, 40))
	passive_label = _mk_label(hud, "PassiveLabel", Vector2(10, 70))
	win_label = _mk_label(hud, "WinLabel", Vector2(300, 10))
	win_label.text = "VICTORIA"
	win_label.visible = false

	cam = Camera2D.new()
	cam.name = "Camera"
	add_child(cam)

	respawn = Timer.new()
	respawn.wait_time = 1.0
	respawn.one_shot = true
	respawn.timeout.connect(_respawn_coin)
	add_child(respawn)
	respawn.start()

	passive_timer = Timer.new()
	passive_timer.wait_time = 0.5
	passive_timer.timeout.connect(_passive_tick)
	add_child(passive_timer)
	passive_timer.start()

	_refresh()

func _mk_label(parent: Node, lname: String, pos: Vector2) -> Label:
	var l := Label.new()
	l.name = lname
	l.position = pos
	parent.add_child(l)
	return l

func _physics_process(delta: float) -> void:
	player.velocity.y += 900.0 * delta
	var vx := 0.0
	if Input.is_action_pressed("ui_right"):
		vx += 220.0
	if Input.is_action_pressed("ui_left"):
		vx -= 220.0
	player.velocity.x = vx
	player.move_and_slide()
	if cam != null:
		cam.position = player.position

	if Input.is_action_just_pressed("ui_accept") and player.is_on_floor():
		player.velocity.y = -420.0

	# state_after_action: ui_up "juega una carta" y gasta maná
	if Input.is_action_just_pressed("ui_up"):
		if not BROKEN:
			mana = max(0, mana - 1)
			_refresh()

	if Input.is_action_just_pressed("restart"):
		_do_restart()

	# resource_within_bounds (cota tipo SAGE resource overflow): carga tope 10
	if BROKEN:
		charge += 0.5
	else:
		charge = minf(charge + 0.5, 10.0)

	if BROKEN and Engine.get_physics_frames() == 10:
		# hueco B: error de script en caliente para no_runtime_errors.
		# Va al final: aborta sólo este frame, el juego sigue.
		var _nulo = null
		_nulo.metodo_inexistente()

func _on_coin(body: Node) -> void:
	if body != player:
		return
	if BROKEN:
		# el HUD NO se actualiza: la moneda "se recoge" pero el contador no sube
		coin.visible = false
		respawn.start()
		return
	score += 1
	coin.visible = false
	coin.set_deferred("monitoring", false)
	respawn.start()
	_refresh()

func _respawn_coin() -> void:
	coin.visible = true
	coin.set_deferred("monitoring", true)
	coin.position = Vector2(player.position.x + 120, player.position.y)

func _on_goal(body: Node) -> void:
	if body != player:
		return
	if BROKEN:
		# la victoria NUNCA se muestra aunque se alcance la meta
		return
	win_label.visible = true

func _passive_tick() -> void:
	if BROKEN:
		# no hay acumulación pasiva: el contador queda congelado
		return
	passive += 1
	_refresh()

func _do_restart() -> void:
	if BROKEN:
		# el reinicio NO resetea nada
		return
	score = 0
	mana = 10
	passive = 0
	win_label.visible = false
	player.position = Vector2(-400, 100)
	_refresh()

func _refresh() -> void:
	score_label.text = "Puntos: %d" % score
	mana_label.text = "Mana: %d" % mana
	passive_label.text = "Pasivos: %d" % passive
