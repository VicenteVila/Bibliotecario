# HITO 10 — H1 intento 7: corchetes medidos + techo de rondas

Fecha de declaración: 2026-10-17. Commitear ESTE archivo ANTES de escribir
código (§4). Arm: `H17`.

## §0 Por qué — diagnóstico tras el intento 6 (HITO9, cerrado NO CUMPLE)

HITO9 §5 midió:

1. **M5b funciona** (5 secciones vaciadas, anclajes de H7 incluidos) y las
   **6 rondas drenan moles**: whack-a-mole confirmado (ReASearch ≥7 quejas
   distintas, WikiSkill 4→4), pero cada ronda sin edición efectiva repite
   queja idéntica (temp 0) y consume presupuesto.
2. **La deriva de formato está identificada por la salida cruda almacenada**:
   el modelo escribe **`[1] -> …` con corchetes** alrededor del número de
   frase (imita la lista `[i]` del prompt). 5 salidas no-parseables lo
   prueban. Ninguna normalización declarada en H8/H9 lo cubre. Daño
   concreto: ReASearch r5/r6 señaló la **línea-mole viva** («Diseñar el
   advisory como bloqueo suave…» — la queja de 3 rondas) y el
   encabezado-título con eco completo: dos objetivos válidos muertos por
   corchetes.
3. **Señal de techo**: las quejas dejaron de evolucionar justo cuando
   fallaba el formato — la cola de moles podría estar cerca de agotarse y no
   se pudo comprobar. Los juicios acabaron **exactos en 17/17**: sin margen
   para más rondas.

Lo que NO cambia: mismo juez, mismas guardas, misma plantilla `MASCARA`,
mismo flujo de runner (cero cambios de flujo en este intento — solo lo
declarado en §1), misma base (H14 → H13 → H1R → H1).

## §1 Arreglos

**A — Corchetes (la deriva medida, nada más).**
- `pat_cab` acepta `[`/`]` alrededor del número de frase y del destino:
  `[1] -> [26] | eco`, `[1] -> 3 | eco`, con o sin espacios.
- La viñeta inicial también admite corchete tras ella: `- [1] -> …`.
- **Solo corchetes**: no se agregan formatos especulativos (H8/H9 enseñó
  que las normalizaciones adivinadas fallan y la evidencia manda; las 5
  salidas almacenadas muestran únicamente esta deriva). El eco ≥20 real
  sigue siendo lo único que decide la verdad; encabezados-eco de H9 intactos.

**B — Techo de rondas y presupuesto (acorde al whack-a-mole).**
- `MAX_ROUNDS` 6 → **8**; `MAX_LOC` 28 → **36**.
- Coste declarado: **≤ 21 juicios** (3 en r0 + 2 × (1+8)) **+ ≤ 36
  localizadores = ≤ 57 llamadas**. Causas registradas intactas.
- Sin cambios de flujo: cada ronda juzga como hasta ahora (no se reutilizan
  juicios — se declara explícitamente para no sorprender al cierre).

## §2 Umbrales (a ratificar antes de la corrida)

Idénticos a HITO7-HITO9 §2 — no se re-baja nada:

- **H5' 5/5** · **G1 5/5** · **G2 5/5** · **C1'** = suite ≥ 322 verdes +
  finales ≥ 50% de la base + **ningún arnés `ok=False`**. **Global = los
  cuatro.** Mismo env del juez.

**Riesgos pre-declarados (no se maquillan si ocurren):**
- **Cola de moles infinita**: si con formato correcto las quejas de
  ReASearch/WikiSkill siguen evolucionando sin converger en 8 rondas →
  H5' ≤ 4/5 → NO CUMPLE, y esa corrida cerraría la evidencia de que la
  base/ instrumento no permite H5' 5/5 sin enmienda (decisión del dueño).
- V1 con vaciados acumulados (base ReASearch ya en 3326): activar
  `validacion_tras_edicion` queda registrado.
- Los juicios en el techo superior (21) dejan menos margen que nunca ante
  reintentos de red; un fallo de juez = re-ejecución idempotente, no
  maquillaje.

## §3 Runner

`evals/run_fase1_h17.py` → `evals/result_fase1_h17.json` (filas `H17`) y
juicios `arm="H17"` en `evals/result_q1_r4r5.json` (H1…H16 sin tocar).
Igual que HITO9 §3 con `MAX_ROUNDS=8`, `MAX_LOC=36`; `loc["salida"]` cruda
se mantiene; sin más cambios de flujo.

## §4 Disciplina

1. Commit de ESTE archivo solo, antes de escribir código.
2. Implementación + tests (suite completa verde) + ruff.
3. Ratificación explícita del dueño de §2 (incluidos riesgos y coste ≤ 57)
   y del env.
4. Corrida oficial única; resultados en §5 de este archivo + hallazgo 26 en
   CONOCIMIENTO, en el commit de cierre.
5. NO CUMPLE se cierra igual; un intento 8 exigiría declaración nueva.
