# HITO 18 — PLAN: scorer B-2 híbrido (métrica determinista + juez V/A)

> **DECLARADO y RATIFICADO 2026-10-22.** El dueño ratificó **§1 (diseño)
> y §2 (umbrales U1-U7) tal como están escritos**, ☐→☑, **antes de
> implementar y antes de cualquier llamada al juez**. En este momento el
> hito sigue con **código 0 y llamadas 0**: esto es la marca de
> ratificación; §5 (cierre) se escribe al terminar.

## §0 — Estado y diagnóstico post-mortem del Hito 17

El H17 (2026-10-22, **NO CUMPLE**, veredicto en su §5) cerró con:

- **U2 ✅ por construcción** — el prefiltro Opción B anula el caso negro
  con 0 llamadas (caucho 0.7762 de H16, resuelto por diseño).
- **U4 ❌ medido** — `Score(default) = Score(idle) = 0.3096` (Δ = 0.0).
- U7 sin medir por 503 del endpoint degradado (F1 midió
  `trampa_con` = 0.675: el juez ve contenido pintado).

**Diagnóstico post-mortem (0 llamadas, sobre frames ya evidenciados).**
Las justificaciones de F3 describen default e idle con el mismo texto
(«el avatar permanece estático…», «no se observa movimiento»), pero el
análisis de píxeles de las mismas capturas dice lo contrario:

| caso | frames | Δ entre frames consecutivos (media) | máx | Δ vs primera (media) |
|---|---|---|---|---|
| default (H15, replay con inputs Π) | 14 | **0.952** | 2.811 | 1.286 |
| idle (H17 F3, replay sin inputs) | 26 | **0.046** | 1.081 | 1.152 |

**Conclusión**: el movimiento objetivo del default es **20× el idle** y el
juez lo reporta ausente en ambos — los LLM son estructuralmente malos
diffing secuencias de frames. El juez `gemini-3.1-flash-lite` **sí
describe bien calidad visual** (sus ítems V/A de F3 son coherentes:
«cuadrado rojo distinguible», «plataforma verde visible») pero **no es
válido para detectar acción**. La causa de U4 no es el prompt ni la
sobrecarga del endpoint: es el rol que se le pidió al juez.

Datos del diagnóstico citados arriba son medición sobre capturas ya
evidenciadas (H15 `b2_etapa1/cap1/frames`, H17 `b2_etapa2/idle/frames`) —
se declaran aquí a transparencia total; no hubo corrida oculta. Los
umbrales de §2 se calibran sobre esos números con margen ≥3× y la corrida
oficial de H18 **re-mide todo desde cero**.

## §1 — Diseño (B-2 híbrido) — RATIFICADO 2026-10-22 por el dueño

**Reparto de roles:**

- **Detección de acción → métrica determinista no-LLM** (`M_mov`):
  diferencia media absoluta entre frames consecutivos en escala de grises
  (Pillow `convert("L")`, luma ITU-R 601-2). Sin umbral de luminancia,
  sin RNG, sin red, sin 503.
- **Calidad visual (V) y estética (A) → juez LLM** con su `PROMPT_B2`
  congelado, la ρ completa de 15 ítems y temp 0. **Los ítems D del juez
  se siguen pidiendo y registrando, pero no puntúan** (D pasó a ser
  100% determinista: B-1 `jugador-mueve` + `M_mov`).
- **Anti-caucho → prefiltro Opción B** (H17), intacto: caso con todos
  los frames planos → 0 llamadas, ítems 0 por construcción.

**Nueva definición de `Score_B2` (enmienda de pesos internos):**

```
S_mov   = clamp(M_mov(default) / 0.50, 0, 1)        # M_mov_ref = 0.50
Score_B2 = 0.50·S_mov + 0.25·V_juez + 0.25·A_juez
```

`V_juez`/`A_juez` = medias por categoría de la ρ completa sobre el caso
default (con prefiltro). La fórmula externa **no cambia**:
`Score_final = BUILD × (0.15·M_B1 + Score_B2)`. `M_mov_ref = 0.50` da
nota plena al demo actual (0.952 → S_mov = 1.0 clamp) y proporcionalidad
para demos con ~mitad de movimiento; es un número nuevo a ratificar.

**Métrica `M_mov` (definición operativa):** frames → escala de grises →
`Δ_i = media(|I_{i+1} − I_i|)` → `M_mov = media(Δ_i)`. Se calcula sobre
las capturas oficiales del caso (viewport 1280×720, 2 fps, congelado
heredado). El idle se sigue capturando (replay sin inputs) porque la
sensibilidad se mide por **sustracción**, no por score del juez.

**Gates (propuesta, ver §2):** U1/U2/U5/U6 idénticos a H17 salvo el
presupuesto de llamadas (baja a ≤8); **U4′ sustituye a U4** por el gate
determinista de movimiento; **U7 se parte en U7a** (trampa del juez:
igual que H17, con ≥0.5 / vacío = 0 — grounding del 50% V/A que aún
puntúa) **y U7b** (trampa de la métrica: secuencia sintética con sprite
en movimiento ≥ 0.20 vs su gemela estática ≤ 0.05 — determinista,
Pillow, sin llamadas).

**Presupuesto de llamadas H18:** default(≤2) + default2(≤2) +
trampa_con(≤2) + trampa_vacio(≤2) = **≤8** (idle y negro ya no llaman:
idle no necesita juez en el diseño híbrido; negro sigue anulado por el
prefiltro). Incluso con el endpoint de H17 al 50% de 503, **U4′ es
invulnerable a la infraestructura**.

**Salida:** `evals/results/result_fase2_b2_h18.json` (H16 y H17
intocables). Artefactos previstos: `evals/preflight/movimiento_b2.py`
(métrica + trampas U7b), `evals/preflight/run_fase2_b2_h18.py`,
`tests/test_movimiento_h18.py`, fila §11 + **enmienda 6** en
`BENCHMARK_SPEC.md`.

**Lo que este diseño NO hace:** no toca `PROMPT_B2`, modelo, temp 0,
anclajes, la ρ de `platformer-juego`, el prefiltro, la fórmula externa
ni B-1. No elimina al juez: le quita únicamente el rol que las
evidencias de H16-H17 demostraron que no puede cumplir.

### §1.B — Diseño implementado (declarado en el commit de implementación, ANTES de medir)

**`evals/preflight/movimiento_b2.py`.** `m_mov(frames)` = media de
`|I_{i+1} − I_i|` sobre grises (Pillow `convert("L")`, dtype int16);
`s_mov(m)` = `clamp(m/0.50, 0, 1)`; `score_b2_hibrido(s, v, a)` =
`0.50·s + 0.25·v + 0.25·a`. Trampas U7b: `trampas_mov(destino)` genera
con Pillow (sin RNG) 8 frames 1280×720 de fondo plano con un sprite
amarillo 64×64 que avanza 40 px/frame y su gemela con el sprite fijo.
Gates `gate_u4p` y `gate_u7b` con los umbrales ratificados de §2.

**`evals/preflight/run_fase2_b2_h18.py`.** Corrida oficial (salida
`evals/results/result_fase2_b2_h18.json`; H16/H17 intactos). Reusa de
H16/H17: gates U1/U2/U5/U6, `_json_suite_runner`, builders de frames,
`_eval` con prefiltro, `_gate_u5`, trampa U7a (`frames_trampa` +
`grounding-trampa.json`). Secuencia: U5 → B-1 → frames (default reusa
H15; idle replaya; negro ffmpeg; trampas Pillow) → **M_mov** (default,
idle, U7b) → juez solo en default, default2, negro (anulado por
prefiltro → 0 llamadas) y U7a con/vacío → Score_B2 híbrido con el
`V`/`A` del juez default → gates U1, U2, U3h (Δhib ≤0.10 y ΔV/A ≤0.15),
U4 (M_mov), U5, U6 (BUILD + ≤8 llamadas), U7a, U7b. `Score_final` solo
con U1-U7 todos OK vía `calcular_score_final(..., GATES_H18)` y
`Score_B2` híbrido. **Idle no llama al juez** (solo aporta frames para
U4′). Presupuesto real: default(≤2)+default2(≤2)+U7a con(≤2)+vacío(≤2)
= **8**; negro e idle = 0.

**Tests.** `tests/test_movimiento_h18.py` (11 puros, sin red): M_mov
estático/alterno/degenerate, trampas U7b separando, clamp de S_mov,
fórmula híbrida, bordes de U4′/U7b, U3h, set de gates H18 (exige
U7a+U7b) y `Score_final` con score híbrido. Suite total ≥ 448.

**Lo que §1.B no cambia**: nada de lo ratificado en §1/§2; la corrida
oficial re-mide todo desde cero. Esta declaración se commitea ANTES de
cualquier llamada al juez.

## §2 — Umbrales (RATIFICADOS 2026-10-22 por el dueño — antes de implementar y de medir)

| gate | umbral | calibración (sobre datos ya evidenciados) | estado |
|---|---|---|---|
| **U1** juez válido | igual H17: JSON estricto, justif. no vacías, ≤2 intentos (sobre default y default2) | — | ☑ 2026-10-22 |
| **U2** anti-caucho | igual H17: presencias = 0 sobre negro **y** Score ≤ 0.30, por construcción (prefiltro) | — | ☑ 2026-10-22 |
| **U3** estabilidad | Δ`Score_B2` ≤ 0.10 y Δ V/A ≤ 0.15 (default vs default2, temp 0) | idéntico a H17 | ☑ 2026-10-22 |
| **U4′** movimiento (nuevo) | `M_mov(default) ≥ 0.20` **y** `M_mov(default) − M_mov(idle) ≥ 0.15` **y** `M_mov(idle) ≤ 0.15` | default 0.952 (4.8×), Δ 0.906 (6.0×), idle 0.046 (3.3× de margen) | ☑ 2026-10-22 |
| **U5** ρ oculta | igual H17: 0 coincidencias de `B2-` en workspace y copia | — | ☑ 2026-10-22 |
| **U6** resto | `BUILD = 1.0` · ruff · suite · llamadas **≤ 8** | H17: 8/10 con idle incluido | ☑ 2026-10-22 |
| **U7a** grounding del juez | igual H17: `Score_B2(con) ≥ 0.5` y `Score_B2(vacío) = 0.0` (mini-ρ `grounding-trampa`) | F1 midió con = 0.675 | ☑ 2026-10-22 |
| **U7b** trampa de la métrica (nueva) | secuencia sintética con sprite moviéndose: `M_mov ≥ 0.20`; su gemela estática: `M_mov ≤ 0.05` | cálculo a priori: sprite 64×64 moviéndose 40 px/frame → Δ ≈ 1.4; estático → 0 exacto | ☑ 2026-10-22 |

`Score_final` solo se publica con **U1-U7 todos OK** (D2, set completo).
Sin ratificación de esta tabla, cualquier corrida que la use **no cuenta**.
Esta tabla no se toca tras medir (disciplina dura).

## §3 — Congelados y enmiendas

- **Se conservan congelados**: fórmula externa `BUILD × (0.15·M_B1 +
  Score_B2)`, anclajes `{0, 0.5, 1}`, `PROMPT_B2`, modelo
  `gemini-3.1-flash-lite`, temp 0, viewport 1280×720 a 2 fps, ρ
  `platformer-juego` (15 ítems completos), prefiltro Opción B, evidencia
  intocable, disciplina D2.
- **Enmienda ratificada (2026-10-22, junto con §2)**: pesos internos de
  `Score_B2` — antes `0.35·D + 0.15·V + 0.35·A` (juez);
  ahora `0.50·S_mov + 0.25·V + 0.25·A` (híbrido). `M_mov_ref = 0.50`
  es número nuevo. Umbrales U4′/U6/U7a/U7b como en §2.
- **No congelado**: diseño interno de `movimiento_b2.py`, el runner H18,
  el presupuesto exacto de tests.

## §4 — Disciplina (sin medir hasta ratificar)

1. Este plan se commiteó **como declaración** (`0825e2e`): código 0,
   llamadas 0.
2. ✔ **Ratificación del dueño 2026-10-22**: §1 y §2 ☐→☑ — **antes** de
   implementar y de cualquier llamada al juez.
3. Solo entonces: implementación + tests puros (suite ≥ 437) + ruff +
   fila §11 de `BENCHMARK_SPEC.md` (enmienda 6) → **corrida oficial
   única** (U1-U7) → §5 con veredicto.
4. Commits en español ASCII sin acentos; clave-scan en cada commit.
5. Si un gate falla → **NO CUMPLE con evidencia y decisión del dueño**;
   umbrales no se tocan tras medir; todo intento fallido se documenta con
   su causa y su coste.

§5 (cierre) se escribe al cerrar; mientras tanto no existe. Evidencia
previa de referencia: `evals/results/result_fase2_b2_h17.json` (H17) y
su §5; diagnóstico de movimiento citado en §0 de este plan.

## §5 — Cierre 2026-10-22: **CUMPLE** (8/8 gates · Score_final 0.9187)

Corrida oficial única ejecutada tras la implementación (`63c2176`). El
endpoint `gemini-3.1-flash-lite` estaba degradado ese día (~50% HTTP 503
medido antes de lanzar); el diseño H18 fue **inmune**: U4′, U7b, U2, U5 y
U6 no dependen del juez, y las 4 evaluaciones lógicas que sí lo usan
(default, default2, U7a con/vacío) completaron con **5 llamadas de 8**
presupuestadas. **No hubo intento fallido: F1 = corrida oficial.**
Umbrales intactos; nada se tocó tras medir.

| intento | archivo | resultado | llamadas | tokens | log |
|---|---|---|---|---|---|
| **F1 (oficial)** | `evals/results/result_fase2_b2_h18.json` | **CUMPLE** | 5 | 38 335 | `evals/logs/h18_run.log` |

### Veredicto por gate

- **U1 OK** — 15/15 ítems, scores ∈ {0, 0.5, 1}, justificaciones 15/15,
  1 intento.
- **U2 OK — por construcción** — prefiltro detectó los 14 frames
  planos del negro → **0 llamadas**, Score_B2 = 0.0, 10/10 presencias
  en 0. (Tercera corrida consecutiva: el caucho de H16 está muerto.)
- **U3 OK** — default vs default2: ΔScore_B2_hib = 0.0, ΔV = 0.0,
  ΔA = 0.0 (temp 0, reproducible).
- **U4′ OK — determinista** — `M_mov(default) = 0.9519 ≥ 0.20` ·
  `Δ(default−idle) = 0.903 ≥ 0.15` · `M_mov(idle) = 0.0489 ≤ 0.15`.
  Consistente con el diagnóstico de §0 (0.952 / 0.046). **Sin una sola
  llamada al juez.**
- **U5 OK** — ρ bajo `evals/` (fuera de EG), 0 apariciones en workspace
  y en copia.
- **U6 OK** — BUILD = 1.0 · M_B1 = 0.8333 · **5/8 llamadas**.
- **U7a OK** — trampa del juez: `Score_B2(con) = 0.675 ≥ 0.5` ·
  `Score_B2(vacío) = 0.0 ≤ 0` (2 intentos, un reintento consumido).
- **U7b OK** — trampa de la métrica: `M_mov(mov) = 0.8725 ≥ 0.20` ·
  `M_mov(estática) = 0.0 ≤ 0.05`. Determinista, 0 llamadas.

### Score publicado (D2 satisfecho: 8/8 gates OK)

```
S_mov   = clamp(0.9519 / 0.50, 0, 1) = 1.0
Score_B2 = 0.50·1.0 + 0.25·0.8 (V) + 0.25·0.375 (A) = 0.7937
Score_final = BUILD(1.0) × (0.15·M_B1(0.8333) + Score_B2(0.7937)) = 0.9187
```

### Lectura (para el dueño)

**El instrumento B-2 es válido por primera vez.** Lo que H16 y H17 no
alcanzaron — un scorer Capa B que mida contenido y no caucho — lo cierra
H18 **cambiando el rol del juez, no sus umbrales**: el juez describe bien
(V=0.8, A=0.375 sobre el demo real; V=1.0 sobre la trampa pintada) pero
no detecta acción; `M_mov` sí (19× de separación default/idle). El
scorer ya no depende de la sensibilidad de un LLM para su gate de
contenido, ni del endpoint para su gate de movimiento.

**Dos precisiones, sin maquillaje:**

1. `Score_final = 0.9187` es la nota de **una** configuración de arnés
   sobre **una** tarea (`platformer-juego`) de la suite `D^val`. **No es
   un resultado de benchmark definitivo**: §10 sigue marcando `Sens(x)`,
   `D^eval`, Harness Cards y presupuesto como pendientes. Es, dentro del
   estándar del propio spec (§0), un **diagnóstico de QA con instrumento
   ya válido**.
2. `M_mov_ref = 0.50` (el divisor de `S_mov`) está calibrado sobre este
   demo: da nota plena (1.0) al movimiento actual. Es un número nuevo,
   ratificado en §2 y **no tocado tras medir**; si la sensibilidad de la
   nota a demos más débiles importa, se re-calibra en un hito futuro con
   línea base nueva, nunca re-bajando el umbral de U4′.

**Próximo paso natural** (no parte de este hito): con B-1 y B-2 ambos
válidos, el bloqueante que queda para una medición definitiva de Capa B
es `Sens(x)` → re-juzgar a nivel de pregunta → construir `H_aux`
(`BENCHMARK_SPEC.md` §10.1-§10.2.1). Y la tesis del proyecto —
`skills = 0` — sigue intacta: esto mejora la **regla**, no el producto.
