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
