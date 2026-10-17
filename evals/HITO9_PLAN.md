# HITO 9 — H1 intento 6: los 3 arreglos medidos del intento 5

Fecha de declaración: 2026-10-17. Commitear ESTE archivo ANTES de escribir
código (§4). Arm: `H16`.

## §0 Por qué — diagnóstico tras el intento 5 (HITO8, cerrado NO CUMPLE)

HITO8 §5 midió, con 0 generaciones y la máscara fija funcionando:

1. **La edición gira la queja** (primera vez en 5 intentos): máscara de la
   línea citada → la cita desaparece del texto y el juez pasa a la siguiente
   fabricación. El juez lee el doc fresco.
2. **Pero es whack-a-mole**: cada ronda revela la siguiente fabricación
   (ReASearch: 4 quejas distintas en 4 rondas; base H1R nunca aprobada →
   doc con muchas fabricaciones). Con 3 rondas × ≤2 frases no drena.
3. **WikiSkill murió de formato**: r0 efectivo y después **4 salidas
   `sin líneas parseables` seguidas** — la pre-normalización de
   flechas/viñetas no bastó; la salida cruda nunca se guardó (no se puede
   diagnosticar el drift a posteriori).
4. **M5b jamás disparó (0 secciones vaciadas)**: el prompt del localizador
   PROHÍBE encabezados («no empieza por #») y el runner solo acciona el
   parse final — los encabezados detectados en intentos previos se pierden.
   Las quejas ancladas en encabezados (l9/l18 de ReASearch) quedaron intactas.

Lo que NO cambia: mismo juez (temp 0, prompt intacto), mismas guardas
(G1/G2/V1/V2/C1'), misma plantilla `MASCARA`, misma disciplina. Base =
mejor estado aprobado conocido (H14 → H13 → H1R → H1).

## §1 Los 3 arreglos

**A — M5b real: encabezados con eco.**
- `parse_localizador`: apuntar a un encabezado **con eco válido deja de ser
  inválido** y pasa a `encabezados` (además de resuelta: no reintentable).
  Umbral del eco en encabezado: `min(20, longitud_del_encabezado_normalizado)`
  y debe aparecer literal en la línea del encabezado — un encabezado corto
  exige eco prácticamente completo, uno largo exige ≥20 chars reales.
  Encabezado sin eco suficiente o con eco que no aparece = inválido (reintento
  igual que hoy). Línea vacía = inválido, sin M5b. **Solo encabezados con
  eco válido alimentan a M5b** (evidencia fuerte antes de vaciar una sección;
  no se acumulan encabezados sin eco entre intentos — se descarta esa vía).
- Prompt del localizador: la regla «no apuntes a encabezados» se sustituye
  por «si la frase se ancla en un encabezado, apunta al encabezado con su
  eco; si no, apunta a la línea de contenido».
- El runner ya alimenta `editar_m5(bp, validas, encabezados)` — con este
  arreglo `encabezados` deja de ser sistemáticamente vacío.

**B — Localizador robusto + diagnóstico.**
- **Persistir la salida cruda** del último intento en `loc["salida"]`
  (recortada a 800 chars): el drift de formato queda diagnosticable aunque
  la corrida falle de nuevo.
- Normalizaciones deterministas añadidas al parse (el eco ≥20 real sigue
  decidiendo la verdad; nada de relajar la validación):
  - separadores `->`, `→`, `⇒`, `—`, `–` y `:` entre frase y línea;
  - prefijos opcionales `frase`/`Frase`/`línea`/`linea`/`Línea`;
  - negrilla alrededor de los números (`**1**` → `1`);
  - prefijo del eco `eco:` / `(eco:` fuera del eco.
- `LOC_MAX_TOKENS` 600 → 800 (truncación como hipótesis de «sin parseables»).

**C — Rondas y presupuesto acordes al whack-a-mole.**
- `MAX_ROUNDS` 3 → **6**; `MAX_LOC` 12 → **28**.
- Coste declarado: **≤ 17 juicios** (3 arneses que aprueban en r0 + 2 × (1+6))
  **+ ≤ 28 localizadores = ≤ 45 llamadas**. Causas registradas intactas
  (`presupuesto_localizador_agotado`, `sin_frases_del_juez`,
  `validacion_tras_edicion`).

## §2 Umbrales (a ratificar antes de la corrida)

Idénticos a HITO7/HITO8 §2 — no se re-baja nada:

- **H5' 5/5** · **G1 5/5** · **G2 5/5** · **C1'** = suite **≥ 320** verdes +
  finales ≥ 50% de la base + **ningún arnés `ok=False`**. **Global = los
  cuatro.**
- Mismo env del juez que los intentos anteriores.

**Riesgos pre-declarados (no se maquillan si ocurren):**
- **Whack-a-mole infinito**: si ReASearch drena sus 6 rondas sin converger
  (base H1R nunca aprobada), H5' ≤ 4/5 → NO CUMPLE, registrado tal cual.
- WikiSkill puede seguir fallando de formato (la salida cruda quedará
  almacenada: esta vez se sabrá por qué).
- Vaciar secciones grandes podría activar V1 (causa
  `validacion_tras_edicion`); protección declarada, riesgo estimado bajo.

## §3 Runner

`evals/run_fase1_h16.py` → `evals/result_fase1_h16.json` (filas `H16`) y
juicios `arm="H16"` en `evals/result_q1_r4r5.json` (H1…H15 sin tocar).
Base, M4, validación tras edición, causas, idempotencia y env obligatoria:
igual que HITO8 §3, con `MAX_ROUNDS=6` y `loc["salida"]` cruda.

## §4 Disciplina

1. Commit de ESTE archivo solo, antes de escribir código.
2. Implementación + tests (suite completa verde) + ruff.
3. Ratificación explícita del dueño de §2 (incluidos riesgos de §2 y coste
   ≤ 45) y del env.
4. Corrida oficial única; resultados en §5 de este archivo + hallazgo 26 en
   CONOCIMIENTO, en el commit de cierre.
5. NO CUMPLE se cierra igual; un intento 7 exigiría declaración nueva.

## §5 Cierre — 2026-10-17 · NO CUMPLE (evidencia)

- **Resultado**: H5' **3/5** · G1 **5/5** · G2 **5/5** · C1' **SÍ** → NO CUMPLE.
  Coste **17 juicios + 20 localizadores = 37** de ≤45 (juicios exactamente en
  el tope declarado); **0 generaciones**; **ningún arnés `ok=False`**
  (V1/V2 nunca fallaron, incluso con 6 vaciados de sección). Suite: **322**.
  PEARL/PG/TCE aprueban r0 estables.
- **Arreglo A (M5b) — SÍ disparó**, primera vez: ReASearch vacía las
  secciones **[9, 18]** en r0 (exactamente los anclajes vivos de H7/H8) y
  luego [11] y [1, 13] (el título «…Validación Pre-Release»): 5 secciones
  vaciadas + 6 líneas enmascaradas en total. La base cae 5196 → 3326 (64%,
  V1 intacto).
- **Arreglo C (6 rondas) — drenó más moles, no alcanzó**: las quejas siguen
  **evolucionando con cada edición efectiva** (whack-a-mole confirmado a
  escala: ReASearch ≥7 quejas distintas; WikiSkill 4 máscaras → 4 quejas
  distintas). Las rondas sin edición efectiva repiten queja idéntica
  (temp 0).
- **Arreglo B (formato) — INSUFICIENTE, y la salida cruda lo prueba** (el
  arreglo de diagnóstico cumplió su función): la deriva real es el modelo
  escribiendo **`[1] -> …`** con corchetes (imitando la lista `[i]` del
  prompt). 5 salidas no-parseables almacenadas lo muestran; ninguna de las
  normalizaciones declaradas (flechas, viñetas, negrilla, prefijos, `:`)
  cubre los corchetes. **Mata fuego en potencia**: en ReASearch r5/r6 el
  modelo señaló la línea 26 mole («Diseñar el advisory como bloqueo suave…»,
  la queja viva de las rondas 4-6) y el encabezado-título con eco completo —
  ambos objetivos existían y no se pudieron aplicar.
- **Límite económico observado**: WikiSkill consumió 12 localizadores en 6
  rondas (formato fallido en 4 de ellas); ReASearch 8. Los juicios llegaron
  exactos a 17/17: cualquier reintentación de juez habría abortado el tope.
- **Lección para un eventual intento 7** (exige declaración nueva): (i)
  normalizar **corchetes alrededor del número de frase** — la deriva medida,
  un caso de prueba directo con las 5 salidas almacenadas; (ii) revisar si
  el whack-a-mole tiene techo (el último mole de WikiSkill apareció en r6
  sin margen de ronda; ReASearch drenó 4 rondas efectivas seguidas y paró
  por fallo de formato, no por agotamiento de moles — señal de que puede
  **converger** con formato correcto + rondas); (iii) coste: juicios en el
  tope → presupuesto de juicios acorde a más rondas si se amplía MAX_ROUNDS.
  La enmienda del juez sigue descartada (comparabilidad, §0).
