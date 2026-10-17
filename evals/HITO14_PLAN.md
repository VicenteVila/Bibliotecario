# HITO 14 — H1 intento 9 redeclarado: puerta forense (brazo `H21`)

**Declaración escrita ANTES de medir.** Evidencia ya registrada sin tocar nada:
E13 (Hito 13, `evals/result_q1_r4r5.json`, 2026-10-17) y su forense en
`evals/HITO13_PLAN.md` §5. Este plan solo redeclara la puerta y el intento 9
tras la decisión **A** del dueño («intento 9 con puerta forense»).

## §0 — Por qué se redeclara la puerta (nada de umbrales del resultado baja)

E13 con fuente completa (`FUENTE_MAX=160000`, PROMPT intacto) midió **3/4**:
PEARL/TCE/Wiki aprueban (restaurados — sus quejas E12 eran falsas) · **PG
FALLA R4+R5** · ReASearch (diag) FALLA. La puerta 4/4 de HITO13 §1.D rechazó
la enmienda 2, pero el forense muestra que **el único fallo de los
obligatorios es de PG y es verdadero**:

- **PG**: `lesson` 0× y `persist` 0× en 131.899 chars → la queja de
  «lessons persistence» es **verdadera**; su aprobación en H17/H18 (ventana
  0,9%) era **artefacto** — PG nunca aprobó a un juez que viera su fuente.
  Sus otras 2 quejas (`refiner` 23×, `mutation` 11×) son **falsas**
  (nombre-exacto: el paper sí las tiene con otros nombres).
- **ReASearch**: con fuente completa su cola se encoge a **1 R4 + 1 R5,
  ambas verdaderas** (`refiner` 0×, `pre-release` 0×) — los moles de las
  rondas tiny (stagnation advisory, search-tree…) existen en la fuente y ya
  no se acusan. **Cola finita de 1-2 reparaciones (primera vez).**

**Puerta forense declarada (sustituye a la 4/4 de HITO13 §1.D, sin tocar
nada medido):** E13 es la recalibración de la enmienda 2 **ya ejecutada y
registrada**; el gate del intento 9 es la **aserción del patrón E13** —
PEARL/TCE/Wiki **OK** (los 3 restaurados, eximen r0) y PG + ReASearch
**FALLA** (los 2 entran al bucle de reparación como arneses que fallan r0).
Si alguna fila E13 falta o el patrón no encaja → **abort sin filas H21**.
Ningún umbral H5'/G1/G2/C1' se re-baja; los juicios E13 se reutilizan tal
cual (0 llamadas nuevas de recalibración).

## §1 — Qué corre el intento 9

- Runner `evals/run_fase1_h21.py` (copia de `run_fase1_h20.py`, que ya
  juzga con fuente completa vía `fuente_completa`):
  - `ARM = "H21"`, `OUT = result_fase1_h21.json`, textos «Hito 14».
  - **Gate**: en vez de `_calibracion` nueva, **aserción E13** (patrón de
    §0; 0 juicios nuevos; si no encaja → abort 1).
  - Cadena `_base()` intacta (H18 → H17 → H14 → H13 → H1R → H1): **PG usa
    su base H18 (2243) y ahora cae en r0 → repara**; ReASearch sigue en
    H1R 5196 → repara; PEARL/TCE/Wiki bases aprobadas → r0 aprueban.
  - M4 (disco <50%), M1 (localizador + 1 reintento), M5 span del eco,
    causas declaradas, escrituras idempotentes por (arm, técnica, ronda).
  - `MAX_ROUNDS = 10`, `MAX_LOC = 32`; fuente por técnica cacheada
    (`fuente_completa`); `_fuente_y_doc` (restos de la ventana vieja)
    eliminado del runner.
  - Juicios por ronda con `q1(fuente, bp)` — `FUENTE_MAX=160000` vigente,
    PROMPT intacto, temp 0, modelo `gemini-3.1-flash-lite`.

## §2 — Umbrales (idénticos a HITO7-13 §2; ninguno se re-baja) y riesgos

| criterio | umbral | medida |
|---|---|---|
| H5' — r4_ok y r5_ok por arnés | **5/5** | último juicio `H21` |
| G1 — punteros resueltos | **5/5** | `verify_and_mark` |
| G2 — estructura | **5/5** | `encabezados`/V2 |
| C1' — sin degeneración | suite **≥338** + finales ≥50% base + **ningún `ok=False`** | pytest + V1 |
| **Global** | **H5' y G1 y G2 y C1'** | |

**Coste declarado: ≤25 juicios** (5 r0 + PG ≤10 + ReASearch ≤10) **y ≤32
localizadores.** Env del juez obligatoria (`JUDGE_MODEL`,
`Q1_BASE_URL`, `Q1_API_KEY`); sin ella el runner aborta.

Riesgos pre-declarados (§3 C1'/H5' NO CUMPLE o errata si se queman):

- **(a)** cola de PG con quejas **falsas** por nombre-exacto
  (`refiner`/`mutation`) encadenando whack-a-mole >10 rondas → NO CUMPLE y
  cierre del hilo con la evidencia.
- **(b)** enmascarar por quejas falsas elimina contenido **verdadero**
  (degradación en dirección inversa a la fabricación; V1 solo guarda la
  longitud) → el forense de cierre revisa qué spans se enmascararon y con
  qué queja.
- **(c)** cuota/429 con entradas de 19-40K tokens → reintentos + re-ejecución
  idempotente (mismo arm reutiliza filas y juicios ya escritos).
- **(d)** ReASearch: esperadas 2 quejas verdaderas → 1-2 ediciones de span
  (V1 blindado); si el juez enlonguece la lista (recorre más texto),
  hereda el riesgo (a) con tope 10 rondas.
- **(e)** `MAX_TOKENS=3600` del juez con fuentes de 160K: enumeración
  truncada posible → si `q1` devuelve `error`, juicio registrado y parada
  idempotente (sin filas falsas), re-ejecutable.

## §3 — Implementación prevista (post-ratificación)

1. Copiar `run_fase1_h20.py` → `run_fase1_h21.py`; sustituir el bloque de
   calibración por la aserción E13 de §0; textos/arm/salida a Hito 14/`H21`;
   eliminar `_fuente_y_doc`; docstrings HITO14.
2. Sin cambios en librería → suite actual **338** se mantiene; ruff gate
   (`bibliotecario/ evals/run_fase1_h21.py evals/eval_q1_r4r5.py tests/`);
   abort-check sin env (`JUDGE_MODEL`/`Q1_BASE_URL`/`Q1_API_KEY` desunset →
   exit 1).
3. Ratificación del dueño (§2: umbrales, coste, riesgos, env) → corrida
   oficial única.
4. Cierre §5 + hallazgo 26/10 en `CONOCIMIENTO.md` (tabla planes + índice)
   + clave-scan + commit+push.

## §4 — Disciplina

Plan commiteado SOLO antes que código → implementación + ruff + abort-check
→ ratificación (umbrales + env + coste + riesgos) → corrida oficial única →
cierre §5 + CONOCIMIENTO + clave-scan + commit+push. Filas `H1`…`H18`,
`E12`, `E13` e historial intactos; solo adiciones `arm="H21"` en
`result_q1_r4r5.json` y `result_fase1_h21.json` nuevo. Commit messages en
español ASCII sin acentos.

## §5 Cierre — 2026-10-17 · NO CUMPLE (intento 9, brazo `H21`)

- **Puerta forense OK** (aserción E13, 0 llamadas nuevas) → corrida oficial
  única. **H5' 3/5 · G1 5/5 · G2 5/5 · C1' NO** (PG `ok=False`) → **NO
  CUMPLE**. Coste: **18 juicios** de los ≤25 · **21 localizadores** de los
  ≤32 · 0 generaciones · suite 338 (se confirma aparte). PEARL/TCE/Wiki
  aprueban r0 con fuente completa.
- **PG — riesgos (a)+(b) quemados**: r0 con 4 quejas (2 falsas por
  nombre-exacto: `refiner`/`mutation`; 2 verdaderas: lessons + extracción) →
  máscara de 4 líneas → r1 el juez gira a quejas **estructurales**
  («Módulo 1-3», «Dependencias» — verdaderas: el paper no describe esa
  arquitectura modular) → r2/r3 vacíos de sección (1858→1902) → edición r4
  → **227 chars < suelo 1121 (50% de la base 2243) →
  `validacion_tras_edicion`, `ok=False`** → C1' NO. La cadena de quejas
  (mezcla de falsas y verdaderas) y los vaciados de sección mataron un
  arnés con base pequeña; sin maquillaje (la fila de fallo no escribe).
- **ReASearch — riesgo (d) quemado**: la cola **no era de 1-2** — son
  **2 quejas por ronda × 10 rondas** de la misma familia **estructural**:
  «Módulo 1/2/3», «Orden de Ejecución», umbrales/validación pre-release —
  el paper (optimizador de artefactos) no define esa arquitectura de
  módulos, así que la fabricación es **pervasiva** y enmascarar menciones
  individuales no la mata. 5196 → 2993 (suelo 2598 intacto). **6 de 10
  ediciones fueron no-op** (M1: salida sin parseables ×3, frase ausente,
  número fuera de rango, eco corto) — con ediciones no-op el juez repite
  queja idéntica (r2–r5 == r1). `NO APRUEBA tras 10 reparaciones`.
- **Ambas caídas bajo el instrumento honesto**: con la fuente completa a la
  vista, PG y ReASearch son **fabricación estructural de su arquitectura de
  módulos** — sus aprobaciones H17/H18 eran artefacto de la ventana ciega
  (hallazgo 10); la reparación por máscaras + V1/V2 **no puede converger**
  donde la fabricación atraviesa todo el documento.
- **Rotación LLM operó** (groq devolvió vacío, gemini agotada/aparcada 15
  min) sin abortar la corrida (riesgo (c) mitigado por §8.12). Anomalía
  registrada: en r2 de PG el juez devolvió prosa de aviso de la API
  («Direct use of automatic function calling…») antes del JSON — parseado
  como FALLA con quejas legibles; fila válida.
- **Balance final de H1 tras 9 intentos + 2 enmiendas**: H5' nunca por
  encima de 4/5 con instrumento ciego, y **3/5 con instrumento honesto**;
  G1/G2 5/5 y C1' SÍ se sostienen. **H1 NO CUMPLE y los dos arneses que
  fallan lo hacen por contenido, no por falta de rondas** (PG por V1,
  ReASearch por fabricación estructural). Decisiones del dueño: cerrar el
  hilo definitivamente con esta evidencia, o declarar una vía nueva (p. ej.
  regeneración de PG/ReASearch con el juez honesto en el bucle de
  generación — enmienda de generación, no de edición).
