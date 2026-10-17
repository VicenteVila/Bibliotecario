# HITO 11 — Cierre de H1 · Intento 8: «máscara quirúrgica del eco» (brazo `H18`)

Declaración escrita ANTES de implementar y ANTES de medir (2026-10-17).
Umbrales y riesgos de §2 a ratificar por el dueño antes de la corrida
oficial. Patrón obligatorio por intento: plan SOLO → implementación + tests
+ suite verde + ruff → ratificación → corrida oficial única → §5 + hallazgo
26 + clave-scan + commit+push.

## §0 Evidencia que declara este intento

Resultado del Hito 10 (intento 7, arm `H17`, cerrado NO CUMPLE): **H5' 4/5**,
G1 5/5, G2 5/5, C1' NO; **WikiSkill aprobado en run5 (primera vez)** — los
corchetes `[N]` eliminaron todos los `sin parseables` y 5 máscaras
consecutivas drenaron sus 5 quejas. ReASearch se topó con los dos riesgos
pre-declarados: cola de moles ≥8 pares distintos evolucionando hasta run7, y
**V1 a 36 chars del suelo** (vaciados 5196→2994; edición r8 → 2562 < 2598 →
`validacion_tras_edicion`, `ok=False`).

**Errata de medición** (corrige el §5 del HITO10_PLAN): allí se estimó
«solo-máscaras ≈50 chars/mole → decenas de moles». Medido en H17, las
máscaras de línea COMPLETA en ReASearch cuestan **213-416 chars cada una**
(r4: 3583→3207 con 1 máscara; r7: 3207→2994 con 1 máscara) — las líneas de
ReASearch son prosa densa de 250-400+ chars. Con ese costo el presupuesto V1
(2598 chars) alcanza para **≈8-12 moles**, justo donde murió: el problema NO
era solo M5b; **la máscara de línea completa también es cara aquí**.

**La vía barata ya existe y está validada**: `parse_localizador` exige hoy
que el eco aparezca literalmente en la línea destino
(`attribution.py:557`, «el eco no aparece en la línea»). El eco (≥20 chars,
pedido exacto al localizador) **es la cita de la fabricación dentro de la
línea**. Reemplazar SOLO ese span por MASCARA retira ≈ `len(eco)-40` chars
por mole (≈20-100), en vez de toda la línea: presupuesto 2598 ÷ ≈60 ≈
**40 moles** → V1 blindado por matemática durante 10 rondas, sin tocar
umbrales ni el instrumento.

## §1 Cambios (los únicos, todos sobre H17)

- **A — Máscara quirúrgica del eco** (`attribution.py`):
  1. `parse_localizador` devuelve además `ecos: {línea: eco_norm}` (clave
     **aditiva**; consumidores actuales intactos).
  2. `editar_m5(blueprint, lineas, encabezados, ecos=None)`: para cada línea
     con eco, reemplaza **solo la ocurrencia** del eco por `MASCARA`
     (búsqueda literal primero; si solo difieren en espacios, regex `\s+`
     sobre el eco escapado). Si no se encuentra → **fallback = máscara de
     línea completa** (comportamiento H10 intacto).
  3. Encabezados → **M5b se mantiene** (vaciado): en H17 mató los anclajes
     de encabezado de ReASearch (run0→run1 y run2→run3 cambiaron) y es
     raro; la cola de moles vive en líneas de cuerpo, donde entra el span.
  4. V1+V2 (`validate_structure`) tras cada edición, igual que siempre.
- **B — Techo**: `MAX_ROUNDS` 10 (de 8), `MAX_LOC` 32 (de 36). Coste
  declarado **≤20 juicios + ≤32 localizadores = ≤52** (r0: 5; ReASearch ≤10;
  Wiki ≤5; reintentos de parseo ya contemplados en LOC). Menor que el ≤57
  de H10 pese a más rondas: sin flujos nuevos.
- **C — Base WikiSkill** = su **estado aprobado en H17 run5** (4213 chars,
  R4/R5 verdes) — regla existente (mejor estado aprobado conocido), ahora
  con primer aprobado de WikiSkill. ReASearch mantiene su cadena
  H14→H13→H1R→H1 (5196, nunca aprobado). PEARL/PG/TCE intactos (bytes
  H13). `M4` en ronda 0 intacto.

## §2 Umbrales, coste y riesgos (a ratificar)

- Umbrales **idénticos a HITO7/8/9/10 §2**: **H5' 5/5** (r4 y r5 por
  juez, misma base y ronda 0), **G1 5/5**, **G2 5/5**, **C1'** (suite
  ≥323 verdes + finales ≥50% de la base + **ningún arnés `ok=False`**);
  **global = los cuatro**. Instrumento intacto: `gemini-3.1-flash-lite` @
  Google, temp 0, prompt `eval_q1_r4r5`, env obligatoria; M4, V1/V2,
  causas de fallo declaradas, infra = aborta y re-ejecuta (idempotente).
  Umbrales solo se mantienen o endurecen; filas `H1`…`H16` intocables.
- Coste ≤52 llamadas (§1.B).
- **Riesgos pre-declarados**:
  1. **Residuo del span**: si la frase fabricada sobrevive al quitar el eco
     (parcial de la línea), la queja persiste en la misma línea — cuesta
     ≈60 chars por ronda extra (V1 no), pero puede agotar las 10 rondas →
     NO CUMPLE.
  2. **Cola de ReASearch >10 moles** → NO CUMPLE con más evidencia de moles
     infinitos (entonces: enmienda o cierre de H1 — decisión del dueño,
     ya que H5' 5/5 no se alcanza sin ReASearch).
  3. **Eco espurio** (el eco aparece de casualidad en otra zona de la
     misma línea) → span equivocado; mismo riesgo que la máscara de línea
     actual, no nuevo.
  4. **V1 con sec-vacates grandes**: si la cola de moles resulta ser
     mayoritariamente de encabezados, los vaciados de sección vuelven a
     consumir chars (~500 por sección) → el blindaje es parcial;
     pre-declarado y medible por fila.
  5. **WikiSkill con base nueva** puede no aprobar r0 → sus rondas
     propias dentro del presupuesto.

## §3 Runner

- `evals/run_fase1_h18.py` (copia del h17): `ARM = "H18"`, OUT
  `result_fase1_h18.json`, `MAX_ROUNDS = 10`, `MAX_LOC = 32`, textos Hito 11
  / intento 8 / HITO11 §2-§3. Cadena de base + M4 + bucle + causas +
  escrituras idempotentes **iguales a HITO10**; único cambio de flujo:
  `editar_m5(..., ecos=parse.get("ecos"))`.
- Filas: `evals/result_fase1_h18.json`; juicios `arm="H18"` en
  `evals/result_q1_r4r5.json` (H1…H17 sin tocar).

## §4 Disciplina

1. Este plan SOLO commiteado antes que el código.
2. Implementación + tests (span encontrado / no encontrado → fallback /
   `ecos` aditivo / encabezados sin cambio / M5b intacto) + suite ≥324 +
   ruff + abort sin env.
3. Ratificación del dueño vía question tool (§2).
4. Corrida oficial única con la env del juez.
5. NO CUMPLE se cierra igual; un intento 9 exigiría declaración nueva.

## §5 Cierre

(pendiente de la corrida oficial)
