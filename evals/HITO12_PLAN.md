# HITO 12 — Cierre de H1 · Intento 9: enmienda 1 de verificación «ventana rica» (brazo `H19`)

Declaración escrita ANTES de implementar y ANTES de medir (2026-10-17).
Ratificación obligatoria del dueño antes de la corrida oficial (§1.D
incluida: enmienda al instrumento de entrada con recalibración). Patrón por
intento: plan SOLO → implementación + tests + suite verde + ruff →
ratificación → corrida oficial única → §5 + hallazgo 26/10 + clave-scan +
commit+push.

## §0 Evidencia que declara este intento

Resultado del Hito 11 (intento 8, arm `H18`, NO CUMPLE): H5' 4/5 · G1 5/5 ·
G2 5/5 · **C1' SÍ** (la máscara quirúrgica blinda V1: 2828 > 2598 tras 10
rondas, ediciones de 12-158 chars) y Wiki aprueba r0 con su base propia.
**Lo único que falta es ReASearch**, cuya cola de moles resultó **>10**
(11 juicios con quejas todas distintas hasta agotar rondas).

Forense de H11 §5 (**hallazgo 10 cuantificado**): la ventana de fuente que
recibe el juez para verificar es de **0,86% para ReASearch (1.195 de
138.667 chars)** y ≤10,4% en las 5 técnicas (PEARL 6,1% · PG 0,9% ·
ReASearch 0,9% · TCE 10,4% · Wiki 7,9%) — `_source_for` selecciona chunks
con `LIKE` sobre etiquetas de procedimiento **en español** contra papers
**en inglés**. El juez declara «el texto fuente no menciona…» contra ≥90%
de fuente invisible: **una cola bottomless es exactamente lo que produce un
juez sin fuente**. Dos lecturas posibles (no adjudicadas): (i) juez ciego y
el doc en gran parte fiel → ventana correcta hace finita la cola y H1 se
alcanza; (ii) doc genuinamente fabricado (ya hay indicios: `pre-release`
aparece **0 veces** en los 138.667 chars de la fuente) → con fuente a la
vista la cola se agota y H1 es inalcanzable por edición. **Ambas se
discriminan con esta misma enmienda.**

Medido antes de declarar: recuperación híbrida (0,5 densa + 0,3 keyword,
embeddings locales sin cuota, `all-MiniLM-L6-v2`) restringida al documento
propio de la técnica, con query = los primeros 2500 chars del blueprint,
trae en su top-6 los chunks de `stagnation` / `search tree` / `advisory` /
`validation` — la ventana actual solo lleva chunk 65. Coste: ~4,5s locales
por blueprint, 0 llamadas LLM.

## §1 Enmienda (input-windowing; el instrumento no se toca)

- **A — `fuente_verificable(tech, bp)`** (nueva, en
  `bibliotecario/agent/tools.py`, al lado de `_source_for`):
  1. chunk 0 del documento de la técnica (título/autores), siempre;
  2. chunks citados por `bp` (`[doc:X:Y]`), en orden de aparición, dedup;
  3. top-10 chunks del **documento propio** de la técnica por score híbrido
     0,5·densa + 0,3·keyword contra `bp[:2500]` (retriever local, sin LLM);
  4. dedup en ese orden, formato `[chunk i]` como hoy, **pre-recorte a
     9000 chars** (el cap de `q1` — `evals/eval_q1_r4r5.py` queda
     **byte-idéntico**: misma plantilla, modelo, temp 0, env).
- **B — Cambio de flujo**: el runner construye la fuente **por blueprint**
  (`fuente_verificable(tech, bp)`) en vez de por técnica
  (`_fuente_y_doc`); `q1(fuente, bp)` idéntico.
- **C — Comparabilidad declarada (enmienda 1, §8.13)**: filas `H1`…`H18`
  quedan como históricas bajo la ventana vieja; solo `E12` y `H19` son
  juzgados con la ventana nueva. Hallazgo 26/10 lo registran.
- **D — Recalibración OBLIGATORIA `E12` (fase 0 del runner, antes que
  cualquier fila de H19)**: re-juzgar con la ventana nueva los 4 estados
  aprobados actuales (PEARL r0 · PG r0 · TCE r0 · Wiki r0, bytes H18) +
  diagnóstico ReASearch r0 (informativo, sin requisito). **Si alguno de los
  4 deja de aprobar, la enmienda se RECHAZA, el runner se aborta antes de
  H19 y la decisión vuelve al dueño** (no se mide el intento 9).

## §2 Umbrales, coste y riesgos (a ratificar)

- Umbrales idénticos a HITO7-§11 §2: **H5' 5/5 · G1 5/5 · G2 5/5 · C1'**
  (suite ≥328 + ≥50% base + ningún `ok=False`); **global = los cuatro**.
  Instrumento: mismo `q1` byte-idéntico, mismo modelo/temp/env; M4, V1/V2,
  causas declaradas, idempotencia intacta; filas `H1`…`H18` intocables.
- Coste ≤ **25 juicios** (E12: 5 + corrida ≤20) **+ ≤32 localizadores**.
- **Riesgos pre-declarados**:
  1. **Alguno de los 4 aprobados falla con ventana rica** → enmienda
     rechazada, corrida abortada sin filas H19 (registrado; decisión del
     dueño).
  2. **ReASearch con más chunks visibles queja AUN MÁS** → NO CUMPLE con
     evidencia de doc fabricado → cierre de H1 documentado.
  3. **ReASearch converge** (cola finita de fabricaciones verdaderas) → H5'
     5/5 y posible CIERRE de H1 en este intento.
  4. **Retrieval pobre** (MiniLM es EN; query ES): términos clave de las
     quejas ausentes de la ventana → medible por fila (presencia de términos
     en la ventana); residuo declarado.
  5. **Truncación 9000**: top-10 + citados pueden exceder el cap → chunks
     finales sin ver (orden de prioridad declarado en §1.A).

## §3 Runner

- `evals/run_fase1_h19.py` (copia de h18): `ARM = "H19"`, OUT
  `result_fase1_h19.json`, `MAX_ROUNDS = 10`, `MAX_LOC = 32`, textos Hito
  12 / intento 9 / enmienda E12 / HITO12 §2-§3. Cadena de base, M4,
  bucle, M1+M5 span, causas e idempotencia **iguales a H18**; cambios:
  fuente por blueprint (§1.B) y **fase E12 con abort** (§1.D; juicios
  `arm="E12"` en `result_q1_r4r5.json`, re-ejecutable).
- Filas: `evals/result_fase1_h19.json` + juicios `arm="H19"`.

## §4 Disciplina

1. Este plan SOLO commiteado antes que el código.
2. Implementación + tests (`fuente_verificable`: chunk0 primero, dedup,
   orden, top-k propio, pre-recorte 9000; E12 abort; runner) + suite ≥330 +
   ruff + abort sin env.
3. Ratificación del dueño (§1 enmienda + §2).
4. Corrida oficial única (E12 → H19).
5. NO CUMPLE / rechazo de enmienda se cierran igual; intento 10 exigiría
   declaración nueva.

## §5 Cierre — 2026-10-17 · ENMIENDA RECHAZADA EN E12 (el intento 9 no corrió)

- **Resultado**: fase E12 con la ventana enmendada → **0/4 obligatorios
  aprueban** (PEARL R4 · PG R4 · TCE R4+R5 · Wiki R4+R5; diagnóstico
  ReASearch R4+R5 como siempre) → **§1.D: ENMIENDA RECHAZADA, abort
  ANTES de cualquier fila H19** — 0 filas `H19`, 0 localizadores, coste
  **5 juicios**. Riesgo (1) pre-declarado, sin maquillaje.
- **Forense determinista de los 5 juicios (0 llamadas nuevas): TODAS las
  quejas nuevas de los 4 obligatorios son FALSAS contra la fuente
  COMPLETA** de su técnica:
  - PEARL R4 cita «converges faster… highest validation performance» →
    **2× y 2× en la fuente (85K)**.
  - PG R4 «graph mutation» → «mutation» **11×** en la fuente (132K).
  - TCE R4 λ=0,025 / ℓ=0,125 → **0.025 y 0.125 exactos**; R5 «Tabla D/E» →
    **Table D 2×, Table E 4×, 7% 24×, 20% 30×** (fuente 63K).
  - Wiki R4 gating → **gating 16×, rbest 10×**; R5 bibliografía →
    **qwen 98×, gemma 18×, vllm, gepa** (fuente 99K).
  ReASearch (diagnóstico) sí mezcla quejas verdaderas (`pre-release` **0×**
  en 139K) y falsas (`re-emission` **1×**).
- **Lección (hallazgo 10, salto cualitativo)**: los veredictos R4/R5 son
  **función de la ventana** — ventana tiny (0,86%-10,4%): inverificable en
  ReASearch y 4/5 estables; ventana rica-por-recuperación (aún solo
  ~7-13%): **0/4 con falsos positivos** en los cuatro. Ninguna ventana
  corta probada es estable: el juez no puede responder «¿está esto en la
  fuente?» sobre un sliver. La recuperación híbrida NO sirvió para esto.
- **Opciones declaradas al dueño** (§5, decisión): **A** cerrar H1 con
  hallazgo 26/10 en su estado actual (NO CUMPLE permanente, 8 corridas +
  1 enmienda rechazada); **B** enmienda 2 = **fuente completa por
  técnica** (63-139K chars por llamada, coste de tokens ×10-15 declarado,
  con recalibración E13 de los mismos 4 — forense respalda que sus quejas
  desaparecerían con fuente completa); **C** verificación mecánica
  determinista de citas (R1/B8) sin juez para el núcleo de R4.
