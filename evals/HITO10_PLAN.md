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

## §5 Cierre — 2026-10-17 · NO CUMPLE (evidencia)

- **Resultado**: H5' **4/5** (récord de la serie) · G1 **5/5** · G2 **5/5** ·
  C1' **NO** → NO CUMPLE. Coste **17 juicios + 18 localizadores = 35** de ≤57;
  **0 generaciones**. Suite al cierre: **323**.
- **WikiSkill CERRADO — primera aprobación en 7 intentos**: los corchetes
  `[N]` (arreglo A) eliminaron **todos** los `sin parseables` de la corrida
  (0 en todo el run, contra 5+ en H9) → **5 máscaras consecutivas**
  (filas r1..r5), 5 quejas evolucionadas (estratificado → filtrado →
  Validación pre-release → propuesta → latencia/herramientas) →
  **R4=OK R5=OK en run5**. La mecánica completa (localizador + máscara +
  whack-a-mole drenable) queda demostrada de punta a punta.
- **ReASearch: se quemaron LOS DOS riesgos pre-declarados, sin maquillaje**:
  1. **Cola de moles profunda (riesgo a)**: las quejas **evolucionaron en
     cada ronda efectiva hasta run7** (≥8 pares distintos; run5==run6 solo
     porque la edición r6 fue no-op). La lista no estaba cerca de agotarse.
  2. **V1 (riesgo b)**: los vaciados de sección consumieron el presupuesto
     de longitud — 5196 → 4210 → 3656 → … → **2994** en 7 rondas; la edición
     de r8 (2 máscaras → 2562) cayó a **36 chars del suelo V1 (2598)** →
     rechazada, causa `validacion_tras_edicion` registrada, arnés
     `ok=False` → **C1' NO** (ningún otro arnés falló; V1/V2 correctos en
     todos los anteriores).
- **Lección clave para un eventual intento 8**: la **vaciación M5b es cara en
  chars y probablemente innecesaria** — en H15 (solo-máscaras, por bug) las
  quejas ancladas en encabezados mueren con máscaras de cuerpo (r0→r1
  cambiaron), y en H17 Wiki mata quejas de sección con máscaras de UNA línea.
  Con solo-máscaras (~50 chars/mole) el presupuesto V1 de 2598 chars alcanza
  para decenas de moles: ReASearch arrancaría cada intento con la base 5196
  y V1 blindado. Si aun así la cola no drena en ~10 rondas, la evidencia de
  moles infinitos queda cerrada (entonces: enmienda o cierre definitivo de
  H1 — decisión del dueño).
- Ruido de red observado sin efecto: reintentos `groq devolvio vacio` y
  `gemini2 esperando` dentro de juicios (rotación declarada §8.12; env y
  modelo intactos; ningún juicio falló).
- **ERRATA (2026-10-17, medición posterior)**: la lección de arriba
  estimaba «solo-máscaras ≈50 chars/mole → decenas de moles». Medido en
  H17, las máscaras de línea completa en ReASearch cuestan **213-416 chars
  cada una** (líneas de 250-400+ chars): el presupuesto V1 (2598) alcanza
  para ≈8-12 moles, no decenas. La vía barata es la **máscara quirúrgica
  del eco** (ya validado literal dentro de la línea en
  `parse_localizador`) — declarada en `evals/HITO11_PLAN.md` §0-§1.
