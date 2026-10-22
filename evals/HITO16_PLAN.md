# HITO 16 — B-2 etapa 2: scorer con juez multimodal sobre rúbrica oculta ρ

*(Declaración ANTES de medir — plan SOLO commiteado.)*

## §0 — Estado y bloqueos medidos

| requisito | estado |
|---|---|
| **Regla §11**: B-2 no se ratifica hasta que B-1 funcione end-to-end | ✅ scorer B-1 v2 ratificado 2026-10-15 (validación 9/9 vs 1/9) — **la regla se cumple hoy** |
| **B-2 desbloqueado** (hallazgo 16: xdotool + trazas `Π`) | ✅ **Hito 15 CUMPLE** (2026-10-17): captura/replay T1-T5, Xvfb por TCP, evidencia en `evals/preflight/results/b2_etapa1/` |
| **Juez multimodal** | ✅ clave Gemini viva; **smoke de tubería 2026-10-17 (1 llamada, declarada)**: `image_url` base64 aceptado por `…/v1beta/openai/chat/completions` → HTTP 200, `{"color":"#808080"}`, usage 1116 tok |
| **Rúbrica oculta ρ** (hallazgo 13: el agente lee su propio evaluador) | ✅ construida en este hito — **ρ vive en `evals/preflight/rubricas/`, nunca se copia al workspace** (gate U5: 0 hits medidos en la corrida oficial) |
| **Scorer D·V·A** | ✅ construido y corrido — **NO CUMPLE 2026-10-22** (§5: U1/U3/U5/U6 OK, U2 y U4 FALLAN) |

Fuente de verdad de la fórmula y los congelados: `evals/BENCHMARK_SPEC.md`
§5.2.1 (fase B-2, **§11 ☑ ratificada 2026-10-21** por el dueño junto con
§2-§3) y GameCraft §3.2. Tarea ancla: **`platformer-juego`** (`benchmark/game_tasks.yaml`
de ReaGame — el workspace actual es ese juego: HUD «Puntos», monedas, meta,
plataformas; suite B-1 `suites_v2/platformer-juego.yaml`).

## §1 — Diseño (4 artefactos + 2 ajustes)

### 1.1 `evals/preflight/rubricas/platformer-juego.json` — ρ oculta

Autoría de este hito, anclada a la instrucción de `platformer-juego`
(movimiento+salto, colisiones, meta, derrota, reinicio, monedas con HUD,
gravedad, coyote time, cámara). Estructura:

- `items[]` ≤ **24** (objetivo: ~15): `id` (`B2-{D,V,A}-NN`), `categoria`
  (`D`|`V`|`A`), `texto` (qué se evalúa), `anclajes` `{0, 0.5, 1}` literales,
  `aplica` (`max` requisito puntual | `mean` propiedad persistente),
  `tope` (0.5 en label-only / decorativo / widget por defecto / forma
  programática — regla GameCraft), `presencia` (bool: ítem observable que
  DEBE ser 0 ante el control negro).
- Categorías: **D** = Content Depth (mecánica demostrable en el replay),
  **V** = Visuals (UI/escena), **A** = Art & Presentation.
- D ≥ 6 ítems, de ellos **≥ 3 sensibles a movimiento/salto** (base del gate U4).
- Laρ se escribe ANTES de la corrida y queda en el commit de implementación.

### 1.2 `evals/preflight/juez_b2.py` — juez multimodal congelado

- **Llamada propia** (urllib, patrón `q1` de `evalq1_r4r5.py`): endpoint
  `Q1_BASE_URL` + `Q1_API_KEY` (patrón declarado de Gemini), `content` array
  = [texto con plantilla + ítems de ρ, 1 imagen_url base64 por frame PNG,
  **en orden cronológico**], `temperature=0`, `max_tokens=2400`,
  reintentos ≤2 por evaluación (429/5xx/parse).
- **`PROMPT_B2` literal** (congelado): evaluador de replay 2 fps, 1280×720,
  sin exploración, rúbrica visible SOLO para el juez, salida **solo JSON**
  `{"items":[{"id","score","justificacion"}]}` — mismo estilo de estricticidad
  que el PROMPT de Q1 (sin prosa, sin fences).
- **`parsear` estricto**: ids exactamente los de ρ (sin faltantes ni extras),
  `score ∈ {0, 0.5, 1}`, `justificacion` no vacía.
- **`agregar`**: aplica `tope` → `aplica` (max|mean) por categoría →
  `Score_B2 = 0.35·D + 0.15·V + 0.35·A`.
- **`score_completo(BUILD, M_B1, B2)`**: `BUILD × (0.15·M_B1 + Score_B2)`
  (fórmula §5.2.1, pesos congelados).
- `validar_rubrica(doc)`: ≤24, ids únicos, pesos, anclajes, aplica, tope.

### 1.3 `evals/preflight/run_fase2_b2.py` — corrida oficial y umbrales

1. **U5**: ρ bajo `evals/` (no bajo `/mnt/c/EG`) + grep `B2-` en el workspace
   y en la copia temporal → 0 hits.
2. **U6 engine**: `suite_runner_v2.py platformer-juego --json` sobre el
   workspace → `BUILD` y `M_B1 = pass/total` (dato, sin umbral).
3. **Fuentes de frames** (todas 1280×720, 2 fps, ≤40):
   - `default` — reutiliza `results/b2_etapa1/cap1/frames` si existe (Hito 15),
     si no, re-captura con `replay_pi.py`;
   - `idle` — captura+replay del nuevo script `idle` con `--dur-ms 10000`
     (Π vacío → duración forzada declarada);
   - `negro` — sintético `ffmpeg -f lavfi -i color=c=black:s=1280x720` (control).
4. **5 evaluaciones lógicas**: default (U1+U3a) · default 2.ª corrida (U3b) ·
   negro (U2) · idle (U4).
5. Persiste `evals/results/result_fase2_b2.json`: por caso ítems, categorías,
   Score_B2, usage/tokens, umbral cumplido + BUILD, M_B1, Score final.

### 1.4 `evals/preflight/pi_scripts/idle.json`

`{"steps":[{"wait":600}]}` — 10 s sin input → Π con `events: []` (control de
orden: los ítems D de movimiento/salto deben caer a 0).

### 1.5 Ajuste `replay_pi.py` — `--dur-ms N`

Duración de grabación = `max(duracion_ms(Π), N)` (para Π vacío: 6 frames
insuficientes → gate ≥10). No toca los congelados de H15 (formato, ventana,
fps).

### 1.6 Guard en `pi_schema.duracion_ms`

Si `events: []` → `0` (hoy reventaría `events[-1]`).

## §2 — Umbrales (ratificar ANTES de medir)

**Ratificados 2026-10-21 por el dueño — ANTES de la corrida oficial** (voto
previo a medir: «Sí, primero los dos arreglos menores, después lo demás»),
junto con §3 y la fila `FASE B-2` de `BENCHMARK_SPEC.md` §11. Desde aquí
ningún umbral se toca: si un gate falla → **NO CUMPLE con evidencia y decisión
del dueño**.

| gate | umbral |
|---|---|
| **U1** juez válido | default → JSON estricto completo: ids exactos de ρ, todos los scores ∈ {0,0.5,1}, justificaciones no vacías, en ≤2 intentos |
| **U2** anti-caucho | control negro → **todos los ítems `presencia:true` = 0** **y** `Score_B2_negro ≤ 0.30` |
| **U3** estabilidad | 2 corridas de default (temp 0): `ΔScore_B2 ≤ 0.10` y `Δ` por categoría ≤ 0.15 (D, V, A) |
| **U4** orden (sensibilidad) | `Score_B2(default) − Score_B2(idle) ≥ 0.10` |
| **U5** ρ oculta | 0 coincidencias de `B2-` en workspace y en copia temporal; ρ solo bajo `evals/` |
| **U6** resto | `BUILD = 1` · `M_B1` reportado (dato) · **suite ≥ 360** · ruff gate · clave-scan |

- **Coste**: ≤ **10 llamadas** a `gemini-3.1-flash-lite` (5 lógicas × ≤2
  intentos); usage/tokens reportado por caso; resto de fases coste 0.
- **Riesgos pre-declarados**: (a) endpoint multimodal enojado en corrida
  (smoke previo reduce, no elimina) → **NO CUMPLE con evidencia**;
  (b) varianza del juez → temp 0 + U3; (c) ρ de autoría propia (sesgo) → ρ
  declarada en el commit de implementación ANTES de la corrida, U2+U4 la
  gatean; (d) coste de imágenes (~17-24k tok/llamada) → reportado; (e)
  dimensiones distintas entre fuentes de frames → generador fijo 1280×720/2 fps.

**Si algún gate falla → NO CUMPLE con evidencia y decisión del dueño.**
Sin gates re-bajados; sin umbrales añadidos tras medir.

## §3 — Congelados y no congelados

**Congelados** (los de GameCraft §3.2 + este hito):

- juez `gemini-3.1-flash-lite` vía env `Q1_API_KEY`/`Q1_BASE_URL` · `temp 0` ·
  plantilla `PROMPT_B2` literal · JSON estricto por ítem;
- pesos `M 0.15 · D 0.35 · V 0.15 · A 0.35` · fórmula
  `Score = BUILD × (0.15·M_B1 + Score_B2)` · `BUILD=0 → Score=0`;
- anclajes `{0, 0.5, 1}` · ≤24 ítems · `tope 0.5` decorativos · `max`/`mean`;
- viewport 1280×720 · muestreo 2 fps · demos ≤1200 ticks (20 s) ·
  **sin exploración por el verificador** (solo el replay);
- eventos Π por tick a 60 fps (≥30 fps requerido por la spec — superset),
  deterministas (H15).

**No congelados**: la ρ específica de cada tarea (autoría por tarea; la de
`platformer-juego` se escribe en implementación), el número de demos, la
selección de frames.

## §4 — Disciplina

Plan commiteado SOLO antes que código → implementación + tests puros (≥10,
suite ≥360) + ruff → ratificación del dueño (§2-§3 **y fila §11 «FASE B-2»**)
→ corrida oficial única (U1-U6) → §5 + actualización de hallazgos 13 y 16 +
fila §11 de `BENCHMARK_SPEC.md` + tabla planes e índice en `CONOCIMIENTO.md`
+ clave-scan + commit+push. `EG/` intacto (solo lectura + copias temporales).
Commit messages en español ASCII sin acentos.

## §5 — Cierre

**CERRADO 2026-10-22 · NO CUMPLE.** Corrida oficial única con medición
(intento 4) sobre los umbrales ratificados el 2026-10-21, sin tocar nada
tras medir. **U1 · U3 · U5 · U6 OK — U2 y U4 FALLAN con evidencia**; queda
decisión del dueño (§2). Evidencia: `evals/results/result_fase2_b2.json` +
`evals/preflight/results/b2_etapa2/`.

### Disciplina §4 — commits

| paso | commit | fecha |
|---|---|---|
| Declaración (plan, §2-§3 y riesgos ANTES de medir) | `eea92ab` | 2026-10-21 |
| Implementación (ρ, juez, runner, idle, 374 tests) | `196d54b` | 2026-10-21 |
| Ratificación del dueño (§2-§3 + fila §11) | `20cad5d` | 2026-10-21 |
| Correcciones pre-medición (suite ancla, Π vacía, reintento 5xx, intentos) | `8c84540` `b52e810` `3f9f2db` `d39bc5e` | 2026-10-21/22 |
| Corrida oficial (intento 4) + este cierre | commit de cierre | 2026-10-22 |

### Intentos 0-3 (ninguno obtuvo datos del juez; coste efectivo 0)

| # | causa del aborto | llamadas | tokens |
|---|---|---|---|
| 0 | `suites_v2/platformer-juego.yaml` no existía (artefacto declarado en §0 inexistente en git) → creada como puerto verbatim de la v1 ratificada + `no_runtime_errors` | 0 | 0 |
| 1 | captura `idle`: `validar_pi` rechazaba la Π vacía que §1.4 declara (`fase_captura`/`fase_replay` trataban `errs` como fallo; §1.6 solo había blindado `duracion_ms`) | 0 | 0 |
| 2 | juez 503 ×4 **sin** reintentar: `"HTTP 5" in str(e)` no matchea `HTTP Error 503` (incumplía §4 «reintento ≤2 en 429/5xx/parse»); además `intentos` no se reportaba en la rama de error (U6 contaba mal) | 4 | 0 |
| 3 | reintento activo: 503 ×8 — Google *«This model is currently experiencing high demand»* (POST de texto mínimo también 503; listado de modelos 200 → saturación del modelo, no del payload) | 8 | 0 |
| — | sondeo hasta recuperación (POST mínimo → 200) | 1 | ~10 |

Correcciones de esos intentos commiteadas ANTES del intento 4; ninguna toca
juez (prompt/temp/modelo), rúbrica, pesos, umbrales ni frames.

### Corrida oficial (intento 4, 2026-10-22) — gates

| gate | ok | detalle literal de `evals/results/result_fase2_b2.json` |
|---|---|---|
| **U1** | ✅ | 15/15 ítems · scores∈{0,0.5,1}=True · justif 15/15 · intentos 1/2 |
| **U2** | ❌ | presencia=0: **0/10** (≠0: `B2-D-01…D-04`, `B2-V-01…03`, `B2-V-05`, `B2-A-02`, `B2-A-03`) · `Score_B2_negro=0.7762` (≤0.30 exigido) |
| **U3** | ✅ | ΔScore_B2=0.0 (≤0.1) · Δcategorías D/V/A = 0.0 (≤0.15 c/u) |
| **U4** | ❌ | `Score_B2(default)=0.3096 − Score_B2(idle)=0.3096 = 0.0` (≥0.10 exigido) |
| **U5** | ✅ | ρ en `evals/preflight/rubricas/` (fuera de EG) · workspace hits=0 · copia hits=0 |
| **U6** | ✅ | BUILD=1.0 · M_B1=0.8333 · llamadas=5/10 · suite **425** ≥360 · ruff ✓ · lint suites 55/576 ✓ · clave-scan nvapi=0 ✓ |

Datos de la corrida: **BUILD 1.0** · **M_B1 0.8333** (9/11) · **Score_B2**
default 0.3096 (D 0.1667 / V 0.8 / A 0.375) · negro 0.7762 · idle 0.3096 ·
**Score_final (dato) 0.4346** = 0.15·0.8333 + 0.3096 · **tokens 82.855**
reportados (17.368 + 17.368 + 17.531 + 30.588; el primer intento de `idle`
falló en parseo y su consumo no queda en `usage`) · **llamadas 5/10** (4 casos
+ 1 reintento de parseo).

### Verificación del instrumento (por qué el NO CUMPLE es válido)

- **U2**: los 14 frames negros tienen luminancia media **0.000** (Pillow) —
  puro negro — y el juez les pone 10 presencias ≠0 y Score 0.7762 →
  **juez caucho confirmado**; el gate anti-caucho funciona y captura.
- **U4**: default e idle difieren ≤3,76% de píxeles (frames comparados);
  dentro de la serie, default evoluciona **5,38%** (frame 0→13) frente a
  **1,61%** en idle → la entrada sí mueve algo, pero el juez otorga Score y
  categorías **idénticos**; recálculo con `agregar` = valor almacenado
  (0.3096 exactos en ambos → sin bug de almacenamiento). B1 sí demuestra
  `jugador-mueve dx=200` y `camara-sigue` → la discrepancia «replay Π no
  diferencia, B-1 sí» queda como hallazgo para el dueño.
- **U3**: `default` y `default2` evalúan la **misma** lista de frames con
  temp 0 → Δ=0 por construcción (gate tal como está ratificado).
- **EG intacto**: `find workspace -newermt` → 0 ficheros modificados (todas
  las fases trabajan en copias temporales).

### Anexo A — citas literales del juez (análisis posterior; 0 llamadas nuevas)

Extracto textual de `evals/results/result_fase2_b2.json`, ya medido: este
anexo solo cita lo que el juez respondió y recomputa sobre los frames
guardados; **no añade llamadas, ni toca gates, ni modifica umbrales**.

**U2 — sobre 14 frames de negro puro (lum 0.000) el juez afirma ver la
demo completa** (15 ítems ∈ {0, 0.5, 1}, `Score_B2_negro` = 0.7762):

| ítem | score | justificación literal |
|---|---|---|
| B2-D-01 | 1.0 | «El avatar se desplaza claramente de izquierda a derecha a lo largo de los frames.» |
| B2-D-02 | 1.0 | «Se observa un arco de salto completo donde el personaje asciende y desciende sobre las plataformas.» |
| B2-D-04 | 1.0 | «La cámara sigue el movimiento del jugador a través del escenario.» |
| B2-D-05 | 1.0 | «Se observa una bandera al final del recorrido que actúa como meta clara.» |
| B2-D-06 | 1.0 | «Hay monedas claramente visibles distribuidas por el nivel.» |

(Inventario `V` 1.0·1.0·1.0·1.0·0.5 y `A` 1.0·0.5·1.0·1.0 también sobre
negro: nada de lo citado existe en los frames.)

**U4 — default e idle: dictamen prácticamente idéntico con `Score_B2`
exactamente igual (0.3096) y `D/V/A` idénticos (0.1667 / 0.8 / 0.375):**

| caso | B2-D-01 | B2-D-02 |
|---|---|---|
| default | 0.0 — «El avatar permanece estático en la misma posición horizontal durante todos los frames.» | 0.0 — «No se observa ningún movimiento vertical ni arco de salto en la secuencia.» |
| idle | 0.0 — «El avatar permanece estático en la misma posición horizontal en todos los frames.» | 0.0 — «No se observa ningún movimiento vertical ni salto en la secuencia.» |

El caso `default` **sí tiene movimiento real** (5,38% de píxeles evolucionan
frame 0→13 frente a 1,61% de idle; salto medido ~32 px; HUD `Puntos: 0` en
ambos extremos) y **B-1 sí lo prueba** (`jugador-mueve dx=200` PASS): la
cadena replay Π → frames → juez no lo transmite o ρ no lo detecta. El
recálculo `agregar` = valor almacenado (0.3096 exactos) descarta bug de
agregación. La causa queda para el **Hito 17** (declaración; sin medir
hasta ratificar).

### M_B1 (dato; sin umbral en U6)

BUILD=1.0, M=9/11=0.8333: fallan `meta-existe` y `monedas-existen` porque
`project.godot` declara `run/main_scene="res://main.tscn"` (solo Player+HUD —
B-1 escanea la escena principal) y Coin/Goal viven en `levels/mision1.tscn`
alcanzable por menú. La suite ancla no se toca tras medirse (congelada al
escribirse).

### Score_final: dato, no nota

0.4346 es **dato** (§1.3 lo reporta siempre); bajo NO CUMPLE no vale como
nota. Nota de código: `run_fase2_b2` lo publica sin exigir todos los gates
pese a su comentario («exige todos los gates para publicarlo»); no se modifica
tras medir — endurecerlo es decisión del dueño.

### Riesgos §2 pre-declarados — balance

(a) endpoint enojado en corrida → **materializado** en intentos 2-3 (fuera de
la medición); (b) varianza del juez → 0 (temp 0; U3 Δ=0 exacto); (c) ρ de
autoría propia → declarada antes de medir y gateada por U2+U4, que **fallan**
(sin maquillaje); (d) coste de imágenes → 82.855 tok reportados, en línea con
los ~17-24k/llamada declarados; (e) dimensiones → frames fijos 1280×720/2 fps.

### Queda — decisión del dueño (nada se toca tras medir)

1. **U2**: confiabilidad del juez sobre entradas sin contenido (caucho 0.7762
   sobre negro puro).
2. **U4**: ρ/juez no discriminan default vs idle pese al movimiento medido;
   causa posible en la cadena Π→escena o en la sensibilidad de ρ.
3. Opciones explícitamente NO ejecutadas: re-bajar umbrales (prohibido),
   repetir corrida (la varianza no es la causa: Δ=0 exacto), cambiar
   juez/rúbrica/pesos (congelados: requiere enmienda ratificada).
