# HITO 17 — PLAN (declaración): grounding del juez B-2

> **DECLARADO 2026-10-22.** Este fichero es una **declaración**, no una
> medición: todavía no hay código nuevo, ni corridas, ni llamadas al juez.
> Los umbrales de §2 están **☐ sin ratificar** — el hito no empieza a medir
> hasta que el dueño ratifique §2 y la opción de §1.

## §0 — Estado y bloqueos medidos

El Hito 16 (2026-10-22, **NO CUMPLE**) dejó dos fallos de **grounding** del
juez `gemini-3.1-flash-lite`, con citas literales en `evals/HITO16_PLAN.md`
§5 «Anexo A»:

- **U2 ❌ — juez caucho**: 14 frames de negro puro (lum 0.000) con
  `Score_B2_negro` 0.7762 e ítems inventando la demo («El avatar se
  desplaza claramente…», «Hay monedas claramente visibles…») sobre frames
  sin nada dentro.
- **U4 ❌ — no discrimina**: `Score(default)=Score(idle)=0.3096` (Δ=0.0 <
  0.10) pese a default evolucionar **5,38%** de píxeles (idle **1,61%**) y
  a que B-1 sí prueba `jugador-mueve dx=200`. El recálculo `agregar` =
  valor almacenado descarta bug de agregación: el fallo está aguas abajo
  (frames → juez, o detección de ρ).

Lo que **ya está descartado** (medido en H16): varianza (U3 Δ=0 exacto con
temp 0), bug de almacenamiento (0.3096 exactos en ambos), fuga de ρ (U5
0/0) y los bugs de reintento 503 (corregidos en H16). El `Score_final`
0.4346 de la evidencia sigue siendo **dato, no nota**.

## §1 — Diseño (opciones para el dueño; sin implementar)

Tres vías de enmienda, no excluyentes entre sí:

- **Opción A — enmienda del prompt (`PROMPT_B2`)**: exigir evidencia por
  ítem (« puntúa solo lo visible; un frame sin X → score 0 ») con anclas
  negativas explícitas. Riesgo: el prompt está **congelado (H16 §3)** —
  tocarlo requiere enmienda declarada; puede alterar U3/U4.
- **Opción B — prefiltro no-LLM antes de puntuar**: análisis de frames sin
  modelo (luminancia/entropía/histograma) que anule o descarte ítems cuando
  el frame no tiene contenido medible → U2 pasa por construcción y baja el
  coste. Riesgo: el umbral del prefiltro es **nuevo** (declarar y ratificar);
  por sí solo no arregla U4.
- **Opción C — cambio de modelo**: juez con mejor grounding visual (otro
  `gemini-*` u otro proveedor vía `Q1_BASE_URL`). Riesgo: rompe el congelado
  H16 §3 (modelo + temp) → U3 se re-mide; cambia coste/varianza.

La decisión (opción o combinación) se declara en un commit **ANTES** de
escribir código. Sin decisión, este plan no avanza.

## §2 — Umbrales propuestos (☐ sin ratificar — no medir hasta ☑)

| gate | umbral propuesto | estado |
|---|---|---|
| **U1** juez válido | igual H16: JSON estricto completo, justificaciones no vacías, ≤2 intentos | ☐ sin ratificar |
| **U2′** anti-caucho (con prefiltro si Opción B) | ítems `presencia:true` = 0 sobre negro **y** `Score_B2_negro ≤ 0.30` | ☐ sin ratificar |
| **U3** estabilidad | Δ`Score_B2` ≤ 0.10 y Δ por categoría ≤ 0.15, temp 0 | ☐ sin ratificar |
| **U4′** orden (sensibilidad) | `Score_B2(default) − Score_B2(idle) ≥ 0.10` | ☐ sin ratificar |
| **U5** ρ oculta | 0 coincidencias de `B2-` en workspace y copia temporal | ☐ sin ratificar |
| **U6** resto | `BUILD=1` · suite ≥ 360 · ruff · clave-scan · llamadas ≤ 10 | ☐ sin ratificar |
| **U7** grounding (nuevo, si procede) | trampa sintética: frame con objeto pintado vs su versión borrada → score ≥ 0.5 el primero y 0 la segunda (propuesta; forma final = diseño en §1) | ☐ sin ratificar |

Sin ratificación, cualquier corrida que use estos gates **no cuenta**.
Esta tabla no se toca tras medir (disciplina dura).

## §3 — Congelados y no congelados

- **Congelados heredados (H16 §3)**: pesos `0.15 · 0.35 · 0.15 · 0.35`,
  fórmula `Score = BUILD × (0.15·M_B1 + Score_B2)`, anclajes `{0,0.5,1}`,
  viewport 1280×720 a 2 fps, ρ oculta bajo `evals/preflight/rubricas/`,
  evidencia intocable (`results/result_*.json` y `logs/`).
- **Congelados hasta enmienda declarada**: plantilla `PROMPT_B2`, modelo
  `gemini-3.1-flash-lite`, `temp 0` (Opción A/C los cambia → enmienda).
- **No congelados**: el diseño final de U7, el umbral del prefiltro
  (Opción B), el número y origen de los demos.

## §4 — Disciplina (sin medir hasta ratificar)

1. Este plan se commitea **como declaración**: código 0, llamadas 0.
2. El dueño elige opción en §1 y ratifica §2 (☐→☑) — **ANTES** de
   implementar nada que mida y de cualquier llamada al juez.
3. Solo entonces: implementación + tests puros (suite ≥ 360) + ruff +
   fila §11 de `BENCHMARK_SPEC.md` con los gates ya ratificados →
   corrida oficial única (U1-U7) → §5 con veredicto.
4. Commits en español ASCII sin acentos; clave-scan en cada commit
   (patrón en `AGENTS.md`).
5. Si un gate falla → **NO CUMPLE con evidencia y decisión del dueño**;
   umbrales no se tocan tras medir; todo intento fallido se documenta con
   su causa y su coste.

§5 (cierre) se escribe al cerrar; mientras tanto no existe. Evidencia
previa de referencia: `evals/results/result_fase2_b2.json` (H16) y el
«Anexo A» de `evals/HITO16_PLAN.md` §5.
