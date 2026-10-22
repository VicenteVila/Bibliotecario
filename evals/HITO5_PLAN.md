# Hito 5 — Cierre de H1: que la verificación vea lo que el juez ve

**Estado: CERRADO 2026-10-17 — declarado ANTES de tocar código (`6f17a6a`),
implementado con tests antes de medir (`c5d5691`), umbrales ratificados por el
dueño y env del juez confirmada antes de la corrida oficial. Resultado:
H5 ✅ · G1 ✗ · G2 ✗ · C1 ✅ → HITO5 NO CUMPLE, ver §6.**

**Objetivo:** cerrar el **hilo H1 / hallazgo 26** de `CONOCIMIENTO.md`. La
lectura vinculante de H1 (declarada en `HITO3_PLAN.md` §5 Fase 1 antes de
medir) es **«100% de los 5 arneses pasan `r4_ok` Y `r5_ok`»** con el juez
`gemini-3.1-flash-lite` @ Google, temp 0, prompt de `eval_q1_r4r5.py`. El
intento 1 quedó **NO CUMPLE** (1/5·1/5 → R1 → 3/5·1/5) con su propio tope
(«no hay segunda tirada») y así queda registrado: **ni `HITO3_PLAN.md` ni las
filas `H1`/`H1R` se tocan**. Este plan es un intento nuevo con declaración
propia (precedente: la enmienda re-lee el umbral con el dueño; aquí el umbral
ni siquiera se relee — se repite tal cual).

---

## 0. Diagnóstico — el estado medido que se ataca

| arnés | H1 (r4·r5) | H1R (r4·r5) | generación: `verificado` / violaciones | resueltas (H1) |
|---|---|---|---|---|
| Task-CoEvolve | ✔ ✔ | *(no re-juzgado)* | False / 10 | **0/10** |
| PEARL | ✘ ✘ | ✔ ✘ | False / 12 | **0/12** |
| WikiSkill | ✘ ✘ | ✔ ✘ | False / 5 | **0/5** |
| Procedural Graphs | ✘ ✘ | ✘ ✘ | False / 7 | 5/5 |
| ReASearch | ✘ ✘ | ✘ ✘ | **True / 0** | 2/2 |
| **suma** | **1/5 · 1/5** | **3/5 · 1/5** | | |

Tres hechos de los que parte el diseño:

1. **Modo A — fabricaciones sin puntero.** `check_attributions` solo examina
   frases que llevan `[doc:id:chunk]`: «sin puntero no hay a qué verificar».
   ReASearch salió `verificado=True` con 2/2 citas resueltas y el juez lo
   suspendió por inventar módulos y protocolos presentados como del paper. El
   informe de la ruta miente en falso — no detecta la mitad del fallo.
2. **Modo B — resolución ≠ atribución.** Tres arneses salieron con **0
   punteros resueltos** (punteros inventados) y el juez no los suspendió por
   eso (TCE aprobó con 0/10). Queda **fuera del alcance de este intento**:
   aquí solo se mide y se protege con la guarda G1; el arreglo generativo de
   resolución es sub-hilo abierto del hallazgo 26.
3. **R5 sobrevive a la reparación dirigida (0 de 4).** R1 reparaba solo los
   ejemplos que el juez listó, pero el juicio es sobre **todo el documento**:
   el barrido de la reparación tiene que ser documental, y la evidencia tiene
   que sumar la que el juez no da — las violaciones mecánicas, que R1 no
   usaba.

## 1. Qué se va a cambiar (diseño, no medición)

1. **Detección de afirmaciones huérfanas** — `check_orphan_claims(blueprint)`
   en `bibliotecario/agent/attribution.py`: una línea que (a) no lleva puntero
   `[doc:…]`, (b) no lleva marca R6 en esa línea ni en la inmediatamente
   siguiente, y (c) contiene algún término del detector existente (`_TECH`:
   CamelCase, kebab/snake, entrecomillado de 6+, decimales, porcentajes,
   `metrica@n`, ficheros), es una afirmación atribuible sin ancla → huérfana.
   Encabezados (`#…`) no cuentan. **Cuesta 0 tokens y no reescribe nada.**
2. **`verify_and_mark` la informa** — las huérfanas entran en `violaciones`
   con `tipo: "huerfana"`, junto a `termino_ausente` y `puntero_roto`. El
   informe deja de devolver `verificado=True` cuando hay fabricaciones sin
   puntero (defecto A del hallazgo 26). **El texto no se toca** — la garantía
   §5.8.3 (nunca reescribir prosa en la ruta) sigue intacta; la reparación
   del texto es cosa del runner, en su sitio declarado.
3. **Runner con juez en el bucle** — `evals/run_fase1_h12.py`, brazo
   **`H12`** (H1 intento 2). Por arnés: **ronda 0 = juicio base** del estado
   actual (TCE desde su fila `H1`; las otras cuatro desde `H1R`) y, si
   suspende, hasta **3 rondas** de reparación, cada una con su juicio.
   Juzgar → reparar → juzgar, hasta aprobar o agotar rondas.
4. **Evidencia de reparación (completa vs R1).** El prompt de ronda lleva:
   (a) las frases concretas del último juicio (`r4_fabricaciones`,
   `r5_rellenados`), (b) las violaciones mecánicas del verificador extendido
   (huérfanas + `termino_ausente` + `puntero_roto`), (c) la fuente, (d) el
   blueprint. Instrucciones: **barrido de TODO el documento**, no solo de los
   ejemplos listados — cifra, umbral, protocolo, recomendación o módulo que no
   esté literal en la fuente → marca «(propuesta del blueprint)» en su línea
   (R6) o se quita; puntero señalado → re-apuntar al chunk correcto de la
   fuente si está en ella, si no quitar el puntero y marcar R6; conservar
   estructura, bibliografía y las citas que ya funcionan; no inventar nada.
5. **Fuera de alcance declarado:** el prompt de generación R1-R8 no se toca
   (confundiría la intervención); el juez y su rúbrica no se tocan
   (`eval_q1_r4r5.PROMPT` intacto); **no se regenera desde cero** — el intento
   2 avanza sobre los blueprints actuales, que son el producto real en disco;
   el modo B (resolución) no se intenta arreglar aquí; `HITO3_PLAN.md` no se
   reescribe.

## 2. Hipótesis y umbrales — DECLARADOS ANTES DE MEDIR

| id | hipótesis | umbral (intacto, nunca re-bajable) |
|---|---|---|
| **H5** | el intento 2 cierra la lectura original de H1 | **5/5** arneses con `r4_ok=true` Y `r5_ok=true` en su último juicio |
| **G1** | la reparación no vacía las anclas (anticipo del vaciado de §8.4) | por arnés: `citas_resueltas` final ≥ ronda 0, con el mismo `score()` local |
| **G2** | la reparación no rompe la estructura | los encabezados `##` de la ronda 0 siguen todos presentes al final, por arnés |
| **C1** | controles (no romper lo existente) | ningún blueprint final vacío ni de emergencia (no empieza por `(`); suite completa en verde |

- **H5 es el 100% de H1 sin redefinirlo.** G1/G2 son salvaguardas
  anti-degeneración **de este intento**, con precedente en el suelo
  B8 ≥ 2,00 de §8.4 («ruta 5 arreglaba R4 a medida que vaciaba el documento»).
  **H5 cumple solo si 5/5 Y G1 Y G2 Y C1.**
- Si tras las 3 rondas no llega → **«NO CUMPLE — intento 2»** con la causa en
  §6. No hay ronda 4, no se cambia de juez, no se baja ningún umbral.
- Ningún umbral es estadístico: son recuentos sobre las 5 técnicas sembradas,
  con juez declarado, exactamente como el intento 1.

## 3. Diseño de medición — `evals/run_fase1_h12.py`

- **Campaña única, ambas escrituras idempotentes:**
  - `evals/results/result_fase1_h12.json` — una fila por arnés y ronda (`arm="H12"`,
    `round=0..3`): blueprint, informe mecánico (huérfanas, violaciones),
    `score()` (punteros y resueltas), `dir`. Re-ejecutar retoma por la última
    fila.
  - `evals/results/result_q1_r4r5.json` — los juicios se escriben **allí mismo**
    (`arm="H12"`, `run=round`) vía `q1()` importado; las filas `H1`/`H1R` no
    se tocan y `eval_q1_r4r5.py --arm=H12` no re-juzga lo ya juzgado.
- **Algoritmo por arnés:** si no hay juicio de la ronda actual → juzgar la
  ronda actual; si aprueba → arnés cerrado (no se toca más); si suspende y
  `round < 3` → reparar con la evidencia de §1.4, escribir la fila siguiente y
  repetir; si `round == 3` → arnés fallo. Cualquier arnés que suspenda en base
  entra al bucle (incluido TCE si fallara).
- **Instrumento idéntico al de H1:** `q1()` de `evals/eval_q1_r4r5.py`,
  `JUDGE_MODEL=gemini-3.1-flash-lite` @ Google vía `Q1_BASE_URL`/
  `Q1_API_KEY`, temperatura 0, sin truncar la respuesta. Ante 503/429 se
  espera y se reintenta **sin cambiar de instrumento**. Las filas de ronda 0
  son juicio fresco con la misma campaña: los números de H1/H1R de §0 son
  diagnóstico histórico, no se reusan como fila del intento 2.
- **Reparación:** `generate()` con la rotación por defecto (sin pin de
  proveedor, temperatura por defecto), tope `BLUEPRINT_MAX_TOKENS`. Tras cada
  ronda se actualiza `data/agents/<slug>/BLUEPRINT.md` (como hizo R1).
- **Informativo por ronda (no es umbral):** huérfanas, violaciones por tipo,
  punteros totales y resueltas, marcas R6 aplicadas, longitud.
- **Coste declarado esperado:** ≤ 5 juicios base + 12 juicios + 12
  `generate()` = **≤ 29 llamadas LLM** (+ reintentos). `score()`,
  `verify_and_mark` y la estructura de ficheros son locales (0 tokens).

## 4. Reglas de disciplina (las del proyecto)

- Umbrales antes de medir; **no se re-bajan**; el resultado se publica tal
  cual (el intento 1 ya cerró NO CUMPLE y este puede cerrar igual).
- Cualquier divergencia entre este diseño y el script se declara **errata con
  fecha en §6** antes de dar el resultado por bueno; el histórico no se
  reescribe (`HITO3_PLAN.md`, filas `H1`/`H1R`, hallazgo 26 hasta que §6 lo
  amplíe).
- **Nada se genera ni se juzga antes de la ratificación del dueño sobre §2**
  (el juicio base ya es medición).
- El prompt de reglas R1-R8, la rúbrica del juez y las filas existentes de
  `result_q1_r4r5.json` quedan congelados como estaban al declarar este plan.

## 5. Cómo se sabrá que cierra

Tabla *criterio / umbral / medido* en §6 tras la corrida oficial, erratas
propias numeradas y coste real — la misma estructura que HITO0-HITO4. Cierre
del hilo: §6 actualiza el **hallazgo 26** de `CONOCIMIENTO.md` **sin borrar
su texto histórico** (se le añade el intento 2 con su veredicto) y el índice
§9 gana la fila del Hito 5. Si H5 cumple, el hilo «verificación de atribución»
del listado de abiertos pasa a cerrado; si no, queda abierto con la nueva
causa medida.

---

## 6. Resultado — 2026-10-17 — **HITO5: NO CUMPLE** (H5 ✅ · G1 ✗ · G2 ✗ · C1 ✅)

Corrida oficial `evals/run_fase1_h12.py` tras la ratificación del dueño
(question tool: «Ratificar y medir ya») y con el env del juez confirmada por
él (`gemini-3.1-flash-lite` @ endpoint OpenAI-compat de Google con
`GEMINI_API_KEY`). **Ningún umbral se tocó.** Datos: filas `arm="H12"` en
`evals/results/result_fase1_h12.json` + juicios en `evals/results/result_q1_r4r5.json`
(las filas `H1`/`H1R` quedan intactas).

| criterio | umbral (ratificado) | medido | veredicto |
|---|---|---|---|
| **H5** cierre de la lectura H1 | **5/5** con `r4_ok` y `r5_ok` | **5/5** (PEARL r2 · PG r1 · ReASearch r1 · TCE r0 · WikiSkill r2) | **CUMPLE** |
| **G1** no vaciar las anclas | resueltas finales ≥ base, por arnés | **4/5** — ReASearch 2 → 0 | **NO CUMPLE** |
| **G2** conservar la estructura | `##` de ronda 0 ⊆ finales, por arnés | **2/5** — pierden `##` PEARL, ReASearch y WikiSkill | **NO CUMPLE** |
| **C1** controles | sin blueprint vacío/`(` + suite | sin emergencias; **291 tests verdes** | **CUMPLE** |
| **global** | H5 **y** G1 **y** G2 **y** C1 | — | **NO CUMPLE** |

Por arnés, tal cual salió:

| arnés | base (r0) | rondas | final | len final | marcas R6 | resueltas | G1 | G2 |
|---|---|---|---|---|---|---|---|---|
| PEARL | R4 ✔ R5 ✘ | 2 | r2 ✔ ✔ | 5.973 | 22 | 0 → 0 | ✔ | ✘ (pierde `## 5. Checklist…` y `## 6. Bibliografía`) |
| Procedural Graphs | ✘ ✘ | 1 | r1 ✔ ✔ | **488** | 1 | 0 → 0 | ✔ | ✔* (*base sin `##`: pase vacío) |
| ReASearch | ✘ ✘ | 1 | r1 ✔ ✔ | **440** | 2 | **2 → 0** | ✘ | ✘ (pierde `## Bibliografía`) |
| Task-CoEvolve | ✔ ✔ | 0 | r0 ✔ ✔ | 6.743 | 0 | 0 → 0 | ✔ | ✔ |
| WikiSkill | ✔ ✘ | 2 | r2 ✔ ✔ | 7.191 | 3 | 0 → 0 | ✔ | ✘ (renombra los `##` con numeración) |

**Lo que esta corrida demuestra, sin adornos:**

- **La cláusula de H1 se alcanzó:** los 5 arneses aprueban `r4_ok` y
  `r5_ok` en su último juicio (H1 empezó en 1/5 · 1/5 y H1R en 3/5 · 1/5).
  El bucle juez → reparación con evidencia completa (frases del juez +
  violaciones mecánicas + huérfanas + fuente, barrido documental con R6)
  funciona para la rúbrica R4/R5.
- **Y las guardas existían justo para esto y saltan.** ReASearch pagó el
  veredicto con sus dos citas resolubles (2 → 0) y su `## Bibliografía`;
  PEARL perdió la bibliografía (R7) en la ronda 2; WikiSkill vació sus 5
  punteros y renombró todos los encabezados (`## Bibliografía` →
  `## 5. Bibliografía`: con la igualdad literal declarada, renombrar es
  fallar — no se reinterpreta a posteriori).
- **Degeneración medida, no maquillada:** dos de los cinco pasos de H5 son
  sobre documentos degenerados — PG final **488 chars** (base 3.988) y
  ReASearch final **440 chars** (base 5.196), y este además ni siquiera es
  un blueprint: es el borrador de razonamiento del propio modelo («Let's
  check if there were pointers…»). **El juez los aprobó `R4=OK R5=OK`**,
  y en cambio rechazó el stub de WikiSkill en ronda 1 (575) por
  «incompleto»: su detección de integridad es inconsistente. C1 como se
  declaró (no vacío, no `(`) no los caza, y **la longitud mínima no se
  inventa ahora como umbral** — queda como contenido declarable del
  siguiente intento. El veredicto global ya es NO CUMPLE por G1/G2.
- PG: sus 0 citas vienen del estado H1R (R1 ya las había quitado antes de
  este intento; la base aquí medía 0), y su G2 pasa vacíamente porque esa
  base no tenía ningún `##`. TCE aprobó en ronda 0 sin tocarse.
- El informe con huérfanas funcionó (base: 3/3/0/3/5) y nutrió cada
  reparación; al final quedan 12 huérfanas en WikiSkill y el juez aprobó
  igual — no es su rúbrica.

**Erratas:** ninguna de medición; ninguna desviación entre diseño y script
(marcas R6 y longitud, que §3 dejó como informativos, se calculan aquí desde
las filas guardadas). **Notas de corrida:** la SDK de Gemini imprimió en
consola un aviso de «automatic function calling» durante la reparación de PG
— no tocó la fila (juzgada tras, ✔ ✔) y ningún output quedó vacío.

**Coste real: 11 juicios + 6 reparaciones = 17 llamadas LLM** (declarado
≤ 29); juicios 3-20 s, reparaciones 8-25 s; suite 291 en verde.

**Qué queda abierto (el hilo NO se cierra — hallazgo 26 ampliado):**

1. **Comprar el veredicto a costa del documento es el modo de fallo nuevo:**
   la siguiente declaración necesita reparación que no degenere — marcado
   in-place línea a línea (estilo `demote`, que nunca reescribe prosa) o
   validación mecánica del draft con rechazo y reintento, en vez de aceptar
   cualquier texto que el `generate()` devuelva.
2. **Validar la salida de la reparación:** hoy solo se descarta vacío o con
   `(`; un borrador de 440 chars de razonamiento pasó el filtro y hasta el
   juez. Longitud/estructura mínima es candidata obvia a umbral declarado.
3. **El juez no cubre integridad/estructura** (su rúbrica es R4/R5): dos
   stubs aprobados y uno rechazado — refuerza el hilo del juez ciego
   (hallazgo 10).
4. **Modo B (resolución) empeoró:** al final del intento **0 de 5 arneses
   con punteros resueltos** (ReASearch perdió los suyos). Sigue siendo un
   fallo distinto del de H1, declarado fuera de alcance aquí, y ya con
   coste medido.
