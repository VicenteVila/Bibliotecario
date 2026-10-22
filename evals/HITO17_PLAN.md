# HITO 17 — PLAN (declaración): grounding del juez B-2

> **DECLARADO y RATIFICADO 2026-10-22.** El dueño eligió la **Opción B
> (prefiltro no-LLM)** de §1 y ratificó **§2 completo (U1-U7) tal como está
> escrito**, ☐→☑, **antes de implementar y antes de medir**. En este momento
> el hito sigue con **código 0 y llamadas 0 al juez**: esto es la marca de
> ratificación; §5 (cierre) se escribe al terminar.

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

**Decisión del dueño — 2026-10-22: Opción B (prefiltro no-LLM).**
Registrada en el commit de ratificación, ANTES de escribir código. Las
opciones A y C quedan sin elegir para este hito; cualquier combinación
posterior exigiría nueva decisión del dueño.

### §1.B — Diseño implementado (declarado en el commit de implementación, ANTES de medir)

**Prefiltro (Opción B).** Regla **sin umbral calibrado**: un frame es
«sin contenido» si es **color plano** (todos los píxeles idénticos —
`min == max` por canal); el control negro de U2 (`ffmpeg lavfi
color=black`) lo cumple exactamente. Un caso se anula **solo si TODOS sus
frames son planos** → el juez **no se llama (0 llamadas)** y todos los
ítems salen 0 con la misma forma que un JSON del juez → U2 pasa **por
construcción**. Se aplica a `default`, `default2`, `idle` y `negro` (los
reales pasan al juez; los planos se anulan) y el informe por caso
(`prefiltro`: total, planos, `sin_contenido`, motivo) queda persistido
en la evidencia. Artefacto: `evals/preflight/prefiltro_b2.py`.

**U7 — trampa sintética (medida SIN prefiltro: al juez crudo).** Dos
imágenes 1280×720 deterministas con Pillow (sin RNG): fondo plano +
sprites pintados (suelo, plataforma, avatar, moneda) = `trampa_con`, y el
mismo fondo sin sprites = `trampa_vacio`. El juez crudo (`PROMPT_B2`
congelado, temp 0, ≤2 intentos) evalúa cada imagen contra la mini-ρ
`grounding-trampa.json` (3 ítems D/V/A declarados en este commit; pasa
el validador congelado de rúbricas). Gate ratificado: `Score_B2(con) ≥
0.5` **y** `Score_B2(vacío) = 0.0` — un juez caucho falla la segunda.
La trampa NO pasa por el prefiltro a propósito: su marco vacío debe
puntuar 0 en el juez, que es lo que U7 mide. Artefactos:
`evals/preflight/run_fase2_b2_h17.py` + `rubricas/grounding-trampa.json`.

**Salida y coste.** La corrida oficial escribe a
`evals/results/result_fase2_b2_h17.json`
(la de H16 `result_fase2_b2.json` es evidencia intocable y **no se pisa**).
Llamadas ≤10 (U6 reutilizado): default(≤2) + default2(≤2) + idle(≤2) +
negro(**0** por prefiltro) + U7 con(≤2) + U7 vacío(≤2) = **10 en el peor
caso**. `Score_final` solo se publica con U1-U7 todos OK (D2 aplicado al
set completo).

**Lo que esta enmienda NO promete**: U4 sigue midiendo la sensibilidad
del juez sobre contenido real (default vs idle) — si el juez no
discrimina, H17 cae en U4 con evidencia y vuelve a decisión del dueño
(opciones A/C). Nada de umbrales U1-U6 se toca.

## §2 — Umbrales (RATIFICADOS 2026-10-22 por el dueño — antes de implementar y de medir)

| gate | umbral | estado |
|---|---|---|
| **U1** juez válido | igual H16: JSON estricto completo, justificaciones no vacías, ≤2 intentos | ☑ 2026-10-22 |
| **U2′** anti-caucho (con prefiltro si Opción B) | ítems `presencia:true` = 0 sobre negro **y** `Score_B2_negro ≤ 0.30` | ☑ 2026-10-22 |
| **U3** estabilidad | Δ`Score_B2` ≤ 0.10 y Δ por categoría ≤ 0.15, temp 0 | ☑ 2026-10-22 |
| **U4′** orden (sensibilidad) | `Score_B2(default) − Score_B2(idle) ≥ 0.10` | ☑ 2026-10-22 |
| **U5** ρ oculta | 0 coincidencias de `B2-` en workspace y copia temporal | ☑ 2026-10-22 |
| **U6** resto | `BUILD=1` · suite ≥ 360 · ruff · clave-scan · llamadas ≤ 10 | ☑ 2026-10-22 |
| **U7** grounding (nuevo) | trampa sintética: frame con objeto pintado vs su versión borrada → score ≥ 0.5 el primero y 0 la segunda (propuesta; forma final = diseño en §1) | ☑ 2026-10-22 |

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

1. ✔ Este plan se commiteó **como declaración** (`10ae417`): código 0,
   llamadas 0.
2. ✔ **Ratificación del dueño 2026-10-22** (este commit): opción B en §1 y
   §2 ☐→☑ — **antes** de implementar y de cualquier llamada al juez.
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

## §5 — Cierre 2026-10-22: **NO CUMPLE** (U4 ❌ medido; U7 sin medir por 503 del endpoint)

Corrida oficial ejecutada tras la implementación (`3cc9f0b`). El endpoint
`gemini-3.1-flash-lite` vía `generativelanguage` estaba degradado ese día
(~50% HTTP 503 medido con probes de diagnóstico), por lo que hubo **tres
intentos**; los dos primeros quedaron incompletos por 503 y se conservan
como evidencia con su coste. El dueño autorizó cada paso (re-corrida tras
F1; espera + corrida 3 sin tocar harness tras F2). **Umbrales intactos;
nada se tocó tras medir.**

| intento | archivo | causa del cierre | llamadas | tokens | log |
|---|---|---|---|---|---|
| F1 | `evals/results/result_fase2_b2_h17_f1.json` | incompleto: HTTP 503 ×2 en `idle` (→U4 sin medir) y `trampa_vacio` (→U7 sin completar); coste documentado | 7 | 36 554 | `evals/logs/h17_f1_run.log` |
| F2 | `evals/results/result_fase2_b2_h17_f2.json` | incompleto: HTTP 503 ×2 en `idle`, `trampa_con` y `trampa_vacio`; coste documentado | 9 | 34 736 | `evals/logs/h17_f2_run.log` |
| **F3 (oficial)** | `evals/results/result_fase2_b2_h17.json` | **NO CUMPLE con gates medidos** (ver abajo) | 8 | 65 314 | `evals/logs/h17_f3_run.log` |

Coste total de los tres intentos: **24 llamadas / 136 604 tokens** del
juez, más ~10 probes de diagnóstico de infraestructura (8 chat — 5 OK —
y 2 GET `/models`; sin rúbrica, no cuentan como medición).

### Veredicto por gate (F3)

- **U1 OK** — 15/15 ítems, scores ∈ {0, 0.5, 1}, justificaciones 15/15,
  intentos ≤2.
- **U2 OK — por construcción** — el prefiltro detectó los 14 frames
  planos del negro y **anuló el caso sin llamar al juez** (0 llamadas,
  Score_B2 = 0.0, 10/10 presencias en 0). El fallo de caucho de H16
  (0.7762 sobre negro puro) quedó **resuelto por diseño** en los tres
  intentos.
- **U3 OK** — default vs default2: ΔScore_B2 = 0.0 ≤ 0.1 (y Δ por
  categoría 0.0).
- **U4 ❌ MEDIDO** — `Score_B2(default) = 0.3096 − Score_B2(idle) =
  0.3096 = 0.0` (exigido ≥0.1). El juez puntuó **igual** la partida real
  y el juego idle: **sigue sin discriminar contenido**, exactamente como
  en H16. Este fallo es de medición, no de infraestructura.
- **U5 OK** — ρ bajo `evals/` (fuera de EG), 0 apariciones en workspace
  y en copia.
- **U6 OK** — BUILD = 1.0, M_B1 = 0.8333 (9/11), 8/10 llamadas ≤10.
- **U7 — SIN MEDIR** — las dos trampas recibieron HTTP 503 ×2 cada una
  (F1 sí midió `trampa_con`: Score_B2 = 0.675 ≥ 0.5 — el juez ve el
  contenido pintado). No altera el veredicto: U4 ya es fallo y los gates
  exigen U1-U7 **todos** OK.
- **Score_final** no publicado (D2 con el set completo U1-U7).

### Lectura (para el dueño; sin tocar nada ya medido)

La **Opción B cumplió su objetivo puntual**: el prefiltro elimina el
falso de caucho del negro con **0 llamadas** y U2 pasa por construcción.
Pero H16 no fallaba solo por caucho: **U4 confirma que el problema de
fondo es la insensibilidad del juez al contenido real** (0.3096 = 0.3096),
por lo que el instrumento B-2 **sigue sin validez de contenido** y el
scorer Capa B no puede declararse válido. Próximos pasos a decisión del
dueño (sin umbral tocado): opciones A/C de §1 (calibrar umbral del
prefiltro / replanteo del juez), o replanteo más amplio del juez B-2.
