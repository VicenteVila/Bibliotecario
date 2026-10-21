# HITO 16 — B-2 etapa 2: scorer con juez multimodal sobre rúbrica oculta ρ

*(Declaración ANTES de medir — plan SOLO commiteado.)*

## §0 — Estado y bloqueos medidos

| requisito | estado |
|---|---|
| **Regla §11**: B-2 no se ratifica hasta que B-1 funcione end-to-end | ✅ scorer B-1 v2 ratificado 2026-10-15 (validación 9/9 vs 1/9) — **la regla se cumple hoy** |
| **B-2 desbloqueado** (hallazgo 16: xdotool + trazas `Π`) | ✅ **Hito 15 CUMPLE** (2026-10-17): captura/replay T1-T5, Xvfb por TCP, evidencia en `evals/preflight/results/b2_etapa1/` |
| **Juez multimodal** | ✅ clave Gemini viva; **smoke de tubería 2026-10-17 (1 llamada, declarada)**: `image_url` base64 aceptado por `…/v1beta/openai/chat/completions` → HTTP 200, `{"color":"#808080"}`, usage 1116 tok |
| **Rúbrica oculta ρ** (hallazgo 13: el agente lee su propio evaluador) | ❌ falta mecanismo → **ρ vive en `evals/preflight/rubricas/`, nunca se copia al workspace** (gate U5) |
| **Scorer D·V·A** | ❌ no existe — este hito lo construye |

Fuente de verdad de la fórmula y los congelados: `evals/BENCHMARK_SPEC.md`
§5.2.1 (fase B-2, **§11 ☐ dejar en blanco** — se vota en la ratificación) y
GameCraft §3.2. Tarea ancla: **`platformer-juego`** (`benchmark/game_tasks.yaml`
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
5. Persiste `evals/result_fase2_b2.json`: por caso ítems, categorías,
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

(pendiente de la corrida oficial)
