# HITO 7 — Declaración: H1 intento 4 (brazo `H14`), «reparación solo por edición»

2026-10-17 · escrito ANTES de implementar y ANTES de medir.
Patrón idéntico a HITO3-HITO6: este archivo se commitea solo, luego la
implementación + tests, luego la ratificación del dueño de §2, luego la
corrida oficial. Umbrales aquí fijados: no se re-bajan después de medir.

## §0 Por qué — diagnóstico tras el intento 3 (HITO6, cerrado NO CUMPLE)

- Las guardas ya funcionan: **G1 5/5 · G2 5/5** (primeras veces), 0 stubs
  aceptados, PG restaurado (485 rechazado → 2243 aprueba). El cierre cae a
  **H5' 3/5** porque ReASearch y WikiSkill no convergen en 2 intentos de
  regeneración (pierden `## Bibliografía`, truncan <50%) y WikiSkill r1
  pasa la validación y lo suspende el juez — su reparación LLM **introduce
  fabricaciones nuevas** (base R4=OK → tras reparar R4=FALLA).
- Patrón de toda la historia: **lo único que degrada es regenerar el
  documento completo** (P3 3/3, stubs H12, truncos H13); lo único que nunca
  degrada es la **edición determinista** (H13: cero reescrituras aceptadas
  fuera de línea). HITO5 §6 ya declaró «marcado in-place» como candidato y
  nunca se construyó: este intento lo construye.
- **Sonda de viabilidad (2026-10-17, antes de declarar):** la localización
  literal frase-del-juez ↔ línea de la base **no es viable**: LCS máximo
  medido sobre los pares reales de H13 = 8–27 chars (umbral previsto 40).
  Las frases del juez son paráfrasis con anotaciones propias. Transparencia
  con el boceto ratificado: donde el boceto decía «0 generate()», el diseño
  final usa **un localizador LLM pequeño** (solo números de línea + eco,
  validado mecánicamente). **La prohibición de reescritura se mantiene
  intacta**: la llamada no puede devolver texto del blueprint, solo apuntar
  a líneas. Coste total sigue dentro de lo ratificado (≤35).

## §1 Mecanismo

**M1 — Localizador guiado (1 llamada LLM pequeña por ronda fallida):**

- Entrada: frases del último juicio (R4+R5) + blueprint numerado por línea.
- Salida estricta, por frase: `N -> M | eco` (frase M del listado → línea
  número M, con un eco literal de esa línea) o `N -> -` (no localiza).
- **Validación mecánica de cada entrada**: M entero en rango, la línea destino
  no es encabezado ni vacía, y el eco (normalizando espacios) aparece como
  subcadena de la línea real. Una entrada inválida = **1 reintento** con el
  listado de fallos; tras él, solo se aplican las entradas válidas y las
  inválidas quedan como evidencia (`frases_no_localizadas`) — nunca se marca
  a ciegas. Vacío/«(» = error de infraestructura (aborta y se re-ejecuta),
  criterio intacto de HITO5-HITO6.

**M2 — Aplicación determinista (0 tokens, `marcar_lineas`):**

- Cada línea localizada recibe «(propuesta del blueprint)» al final de su
  propia línea. Edición de línea, jamás de frase; sin dedupe doble; líneas
  de encabezado inmunes. Los contadores salen en la fila.

**M3 — Sin reescritura:**

- **Cero `generate()` de blueprint en todo el intento.** La regeneración
  completa queda fuera de alcance declarado (medida degradando en 4/4
  intentos históricos). Sin reescritura no hay truncos ni pérdida de
  encabezados posibles: V1/V2/V3 del HITO6 se recalculan igualmente al
  cierre y deben pasar **por construcción** — si no pasan, es bug y NO
  CUMPLE.

**M4 — Disco saneado en ronda 0:**

- Si `BLUEPRINT.md` del arnés existe y mide < 50% de su base (condición V1),
  se restaura con la base. Hoy: solo ReASearch (517 chars, stub heredado de
  H12). Nada más se toca fuera de corrida.

**Base del intento (declarada):** por arnés, **el mejor estado juzgado y
aprobado conocido** — los textos de H13 que aprueban (PEARL r2, PG r1,
TCE r0) y, para ReASearch y WikiSkill, `H1R`/`H1` (nunca un artefacto
suspendido de H13). Mismo texto + juez temp 0 = veredicto estable (§8.12:
0 parpadeos); si alguno parpadea, sus frases alimentan las rondas de
marcado. G1/G2 se miden contra esta base: **la barra sigue siendo 5/5 en
los cuatro criterios** — no se relaja nada, se empieza desde lo ya probado.

## §2 Umbrales (a ratificar antes de la corrida)

| criterio | umbral | base |
|---|---|---|
| H5' r4_ok y r5_ok por arnés | 5/5 | último juicio `H14` |
| G1 resueltas finales >= base | 5/5 | base §1 (mejor estado aprobado) |
| G2 encabezados base incluidos | 5/5 | ídem |
| C1' | suite 301 verde + cada final >= 50% de su base + ningún arnés en fallo | |
| **Global** | **H5' y G1 y G2 y C1'** | |

- Coste declarado: **≤ 20 juicios + ≤ 12 localizadores = ≤ 32 llamadas LLM**
  (dentro del ≤35 ratificado); **0 `generate()` de reescritura**.
- Juez congelado: `gemini-3.1-flash-lite` @ Google vía endpoint OpenAI, temp
  0, prompt `eval_q1_r4r5` intacto, env obligatoria (la misma que el dueño
  confirmó en HITO5/HITO6). El localizador usa el `generate()` estándar del
  sistema — **no es el juez** y no toca su instrumento.
- HITO3-HITO6 e historial intactos: esta corrida solo AÑADE filas
  `arm="H14"`. Nada se re-mide, nada se re-baja.

## §3 Runner

`evals/run_fase1_h14.py` → `evals/result_fase1_h14.json` (filas `H14`) y
juicios `arm="H14", run=ronda` en `evals/result_q1_r4r5.json` (H1, H1R,
H12, H13 sin tocar).

- Ronda 0: guardado + juicio fresco de la base §1 + saneo de disco M4.
- Si aprueba, arnés cerrado. Si no, unidad de reparación = **M1 localizador
  + M2 marcado**; la nueva ronda juzga el resultado. Hasta **3 rondas** de
  reparación; tres fallos seguidos = arnés fallo (sin ronda 4).
- Presupuesto global: si se agotan los 12 localizadores, las rondas
  siguientes fallan con causa `presupuesto_localizador_agotado` (registrada,
  no maquillada).
- Idempotente (retoma por el último juicio/fila); disco solo con M4 y con
  estados aceptados por el flujo.
- Apertura obligatoria con la env del juez (aborta sin ella).

## §4 Disciplina

1. Commit de ESTE archivo solo, antes de escribir código.
2. Implementación + tests (suite completa verde) + ruff.
3. Ratificación explícita del dueño de §2 (incluida la desviación §0 del
   boceto: localizador con LLM en vez de matching literal) y del env.
4. Corrida oficial única; resultados en §5 de este archivo + hallazgo 26 en
   CONOCIMIENTO, en el commit de cierre.
5. NO CUMPLE se cierra igual; un intento 5 exigiría declaración nueva.
