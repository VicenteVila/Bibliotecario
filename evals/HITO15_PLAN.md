# HITO 15 — B-2 etapa 1: trazas `Π` + replay determinista (sin juez)

**Declaración escrita ANTES de medir.** Continúa B-2 (hallazgo 16) tras
cerrar H1. Decisiones del dueño pre-declaradas: **alcance = etapa 1**
(replay+trazas, sin juez multimodal ni rúbrica `ρ` — todo eso queda para el
Hito 16) y **demos guionizadas** (política fija por tarea; el grabador
admite sesiones humanas después con el mismo formato).

## §0 — Estado del bloqueo (medido 2026-10-17)

| bloqueante de B-2 (hallazgo 16) | estado |
|---|---|
| `xdotool` ausente | ✅ **desbloqueado** — `.deb` oficiales extraídos a `~/opt/xdotool` **sin root** (`xdotool version` OK y conecta a `DISPLAY=:0`); instalación duradera opcional: `sudo apt install xdotool` |
| Xvfb / ffmpeg | ✅ ya instalados (`/usr/bin/Xvfb`, `/usr/bin/ffmpeg`) |
| ReaGame no emite trazas `Π` | ❌ **objetivo de este hito** |
| Regla «B-2 no se ratifica sin B-1 end-to-end» | ✅ cumplida desde 2026-10-15 (smoke 10/10 + reparación 10→80) |
| API Gemini para el juez | ✅ viva (HTTP 200 medido) — **no usada en etapa 1** (0 tokens) |

**Regla de este hito:** solo etapa 1 — **el scorer B-2 NO se ratifica** (la
fórmula `0.15·M_B1 + 0.35·D_B2 + 0.15·V_B2 + 0.35·A_B2` y la rúbrica `ρ`
siguen sin ratificar; §5.2.1 BENCHMARK_SPEC queda «NO ratificar todavía»
hasta el Hito 16). Congelamos aquí únicamente el **formato `Π`** y la
**ventana de replay** por coherencia con GameCraft §3.2 (1280×720 · 30 fps ·
≤20 s · muestreo 2 fps).

## §1 — Diseño (nada en ReaGame; todo por copia temporal, como B-1)

Todos los artefactos nuevos en `evals/preflight/` (el runner los copia al
workspace temporal; `ReaGame queda intacto`):

1. **`pi_capture.gd`** — grabador in-engine (autoload inyectado en la
   **copia**): `notification(WM_CLOSE_REQUEST)`/`NOTIFICATION_EXIT_TREE` →
   escribe `_pi.json`. Fuente de verdad de la `Π` **la emite el actor**
   (riesgo b) — el grabador persiste lo que el actor declara + cualquier
   `_input` humano futuro.
2. **`pi_actor.gd`** — política guionizada (autoload en la copia): lee
   `_pi_script.json`, ejecuta las acciones en **ticks de física** (t_ms =
   `frame × 1000/60`, entero y determinista — no reloj de pared), presiona
   con `Input.action_press/release`, **y registra cada evento en `Π` con la
   tecla X equivalente** para que el replay sea nivel-X. Sesión ≤20 s.
3. **`pi_schema.py`** — validación de `Π` (evento `{t_ms, type: key|mouse,
   keysym|button, phase: down|up, x?, y?}`, orden creciente, t_ms ≤ 20000,
   ≤30 fps en mouse-motion) + **tabla congelada** `ui_left→Left`,
   `ui_right→Right`, `ui_up→Up`, `ui_down→Down`, `ui_accept→space`,
   `ui_cancel→Escape` (acciones fuera de tabla → error declarado, no
   aproximación).
4. **`replay_pi.py`** — dos fases en directorios temporales + `Xvfb :99`
   1280×720×24:
   - **A · captura**: copia del workspace + `project.godot` con los dos
     autoloads + `_pi_script.json` → `godot --path tmp` (ventana) →
     `_pi.json` → se guarda como demo.
   - **B · replay**: copia fresca → `xdotool` inyecta los eventos de `Π`
     en sus `t_ms` (keysym + `windowactivate`/foco declarado), `ffmpeg
     -f x11grab -r 2` graba → `replay.mp4` + `frames/step_XX.png`
     (muestreo 2 fps, ≤40 frames por demo de 20 s).
   - Demo inicial: `pi_scripts/default.json` (genérica: espera, mueve
     derecha, salta, acepta — declarada en §3).
5. **Tests puros** `tests/test_pi_pipeline.py` (sin motor): schema,
   límites 20 s/30 fps, tabla `ui_*`→keysyms, conversión `Π` → lista de
   comandos `xdotool` con timestamps, rechazos (orden, exceso, tecla fuera
   de tabla). Engine smoke = corrida oficial, no pytest.

## §2 — Umbrales de la corrida oficial (ratificables) y riesgos

| # | umbral |
|---|---|
| T1 | captura windowed en Xvfb produce `_pi.json` **válido** (schema) de ≥3 eventos |
| T2 | **determinismo**: dos capturas con el mismo script → **secuencia de eventos idéntica** (t_ms por tick) |
| T3 | replay: exit 0, `replay.mp4` existe y **≥10 frames** PNG no-negros (2 fps × sesión ≥10 s) |
| T4 | **ReaGame intacto** (hashes de `workspace/current` antes/después idénticos) |
| T5 | suite **≥338** verdes + ruff gate |

Coste: **0 tokens LLM** (sin juez, sin generación); presupuesto de tiempo
≤2 timeouts de 180 s por ejecución de motor.

Riesgos pre-declarados:

- **(a)** `x11grab`/`xdotool` sobre Xvfb puede fallar en este entorno WSL →
  fallback declarado y permitido: `DISPLAY=:0` (WSLg). Si ambos fallan →
  NO CUMPLE con la evidencia de stderr.
- **(b)** `Input.action_press` quizá no dispara `_input` del grabador → por
  eso `Π` la emite **el actor** (diseño ya elegido); el hook `_input` solo
  cubre humanos futuros.
- **(c)** equivalencia acción-in-engine vs tecla-X en replay (el juego
  puede mapear distinto) → T3 comprueba ejecución sin error y frames; la
  equivalencia semántica de estado queda como limitación declarada de
  etapa 1.
- **(d)** foco de ventana: `xdotool` sin foco pierde teclas → se usa
  `windowactivate`+`windowfocus` y se declara; si el juego no recibe input,
  T3 cae a frames estáticos (declarado: se mirará el contenido, no solo
  el recuento).
- **(e)** la ventana temporal arranca con errores de runtime del propio
  juego (hallazgo 18) → la sesión no debe abortarse por eso: el umbral es
  `Π` válida + replay vivo, **no** la calidad del juego (eso es B-1/D/V/A).

## §3 — Disco de declaración

- **Congelados en etapa 1**: formato `Π`, tabla `ui_*`→keysyms, viewport
  1280×720, 30 fps de captura, ≤20 s, muestreo 2 fps, `Xvfb :99`.
- **Demo inicial `pi_scripts/default.json`** (guionizada, ~8-12 s):
  `espera 60f → ui_right 90f → ui_accept 10f → ui_right 60f → ui_accept
  10f → espera 30f` — cubre movimiento + interacción sin mouse (el mouse
  queda en el schema con `type: mouse` para etapa 2/humanos).
- **No ratificado en este hito**: scorer B-2, rúbrica `ρ`, juez multimodal,
  pesos, fórmula.

## §4 — Disciplina

Plan commiteado SOLO antes que código → implementación + tests puros +
suite ≥338 + ruff → ratificación del dueño (§2-§3) → corrida oficial única
(T1-T5) → §5 + hallazgo 16 en `CONOCIMIENTO.md` (tabla planes + índice) +
clave-scan + commit+push. Nada de `EG/` se modifica (solo lectura +
copias temporales). Commit messages en español ASCII sin acentos.

## §5 Cierre

**CUMPLE 2026-10-17.** Declaración (`fac658e`) e implementación (`71b2ef7`)
ANTES de medir; §2-§3 ratificados por el dueño; corrida oficial única.
Coste: **0 tokens LLM** (sin juez, sin API). Resultados T1-T5:

- **T1 SÍ** — captura produce `_pi.json` válido: **8 eventos / 3833 ms /
  `errores_schema=[]`** (umbral ≥3), tanto en `:0` como en Xvfb.
- **T2 SÍ** — dos capturas → documentos **byte-idénticos**
  (`json.dumps(sort_keys=True)`), t_ms derivados de tick (1000, 2500,
  2666…); además las capturas de Xvfb coinciden con las de `:0`
  (determinismo cross-display).
- **T3 SÍ (Xvfb, ruta primaria)** — replay `exit=0`, **14 frames ≥10**,
  **0 negros**, luminancia media **78.31**, `ffmpeg_exit=0` (mp4 7.0 s),
  **0 fallos xdotool**, ventana **0,0 × 1280x720**. Frame 7 inspeccionado
  visualmente: el juego real (HUD «Puntos: 0», jugador rojo sobre
  plataforma verde).
- **T4 SÍ** — hash md5 del workspace de ReaGame antes/después idéntico:
  `255883e3ed6168cf533df7f9879e6636` (651 archivos). ReaGame solo lectura
  + copias temporales (patrón B-1).
- **T5 SÍ** — suite **350 passed** (338 + 12 `test_pi_pipeline`) y ruff
  gate limpio sobre `bibliotecario/`, runners/evals activos, preflight
  nuevo y `tests/`.

**Desviaciones medidas durante la corrida (riesgo (a) agotado por orden):**

1. **WSLg monta `/tmp/.X11-unix` como tmpfs `ro`** → Xvfb no puede crear
   su socket unix (`chmod` → EROFS; `-nolisten tcp` lo mataba). Arreglo
   runtime: Xvfb con `-listen tcp -ac` y display `localhost:99`
   (puerto 6099); `_arrancar_xvfb` sondea unix primero y TCP después (y
   salta displays ocupados). xdotool/godot/ffmpeg funcionan por TCP.
2. **Fallback `:0` (WSLg) agotado**: con ventana en 364,266 el x11grab
   1280×720 devolvió **11/11 frames negros** (lum 0.02) — capturado como
   evidencia en el report (entrada `ok=false`). Arreglo: `--position 0,0`
   en ambas invocaciones del motor + ruta Xvfb.
3. Sin WM: `windowraise` + `windowfocus --sync` bastaron (0 fallos).
4. Lección operativa: `pkill -f "Xvfb :99"` mata el propio shell
   (self-match con el patrón).

**Evidencia:** `evals/preflight/results/b2_etapa1/` — `cap1|cap2/
demo_pi.json`, `report_b2.json` (lista acumulada: 2 capturas `:0`, 2
capturas Xvfb, replay `:0` fallido, replay Xvfb **ok**), `replay.mp4` +
`frames/` (gitignorados: binario), `.gitignore` local. Commits: plan
`fac658e` → impl `71b2ef7` → ajuste runtime + cierre (este).

**No ratificado en este hito** (para el Hito 16, decisión del dueño):
scorer B-2, rúbrica `ρ`, juez multimodal, pesos y fórmula.
