# Hito 3 — arneses válidos: diseño y evaluación

**Estado: RATIFICADO 2026-10-16 — Fase 0 ✅ cerrada · Fase 1 ✅ ejecutada
(hueco A cerrado; H1 medida: NO CUMPLE, ver resultado) · Fase 2 ✅ ejecutada
(hueco B cerrado; H2 medida: CUMPLE, ver resultado) · Fase 3 ✅ ejecutada
(hueco C cerrado — estado real a `apply_pfs`; H3 medida: NO CUMPLE, 0 fires
en 10 runs limpios, ver resultado y lectura).****
**Decisión del dueño:** «Ratificar H1-H4 tal cual» · «Camino 1».
H1-H4 quedan fijos tal como se proponen; **nada se mide hasta ahora y a
partir de ahora no se re-bajan.** Camino de la §7 = **1** (diseñar sobre las
5 técnicas ya sembradas; los papers de arneses quedan para un experimento
aparte con línea base propia). Esta es la misma regla que abrió el Hito 1 y
el Hito 2.

---

## 1. Qué es este hito

README:2-5 dice que el agente *«produce **blueprints de implementación**
(+ plantillas de agente instanciables) para aplicar las técnicas de esos papers
en agentes nuevos»*.

El Hito 2 midió la **primera mitad** — el blueprint. El Hito 3 ataca la
segunda: **que el arnés resultante sea válido y que se pueda evaluar.**

No es «que compile». La dimensión D ya lo cerró en el Hito 2 (5/5 · 5/5 ·
18/20). Es que **haga algo** y que **se pueda comparar con otro**.

---

## 2. Estado actual — medido, no opinado

Resultado de la exploración del 2026-10-13. Todo esto **existe y está testeado**:

| pieza | dónde | estado |
|---|---|---|
| `implement` → `agent_template.py` | `agent/tools.py:409-454` | **Implementado.** Escribe `STEPS` + `run()`. Tests y dimensión D verdes. |
| Harness de 4 capas | `harness/layers.py` | **Implementado.** Calibración de tools, skills, validación de llamadas, regulación de trayectoria. |
| `RuntimeHarness` + runs persistidas | `harness/runtime.py` | **Implementado y en uso.** `record_score` escribe 0-1 desde la eval. |
| `validation_tasks` / `task_outcomes` | `core/storage.py:54-69`, `coevolve/task_pool.py` | **Implementado y poblado** por `eval_end2end.py`. |
| PFs con precondiciones | `harness/pfs.py` | **Implementados y testeables.** |
| selector / estimator / wiki | `coevolve/` | **Implementados y testeados.** Sin llamantes **por decisión** (`REPORT_COEVOLVE.md`). |
| Eval del loop completo | `evals/eval_end2end.py` | **Sólida** — juez ciego, IC 95%, ruido medido. |
| Eval de la plantilla | `evals/run_dimension_d.py` | **Mínima** — compila + estado, no calidad. |

---

## 3. Los cuatro huecos

### Hueco A — `implement` se salta todo lo que el Hito 2 construyó

`instantiate_agent_template` llama a `build_blueprint` **crudo**
(`tools.py:411`). Las rutas que sí verifican — `blueprint_loop`
(`api.py:80-83`), `blueprint_verified` (`api.py:85-93`), `blueprint_p4`
(`api.py:96-105`), `blueprint_route5` (`api.py:135-158`) — **no se usan en
esta ruta**.

Tampoco pasan por `verify_and_repair` (`tools.py:344-379`), `verify_and_mark`
(`tools.py:382-406`) ni `critic_and_demote` (`agent/attribution.py`).

**Consecuencia:** un arnés puede salir con **peor** integridad que el blueprint
que ya medimos. Las reglas R1-R8, B5, R4 y R5 del Hito 2 **no llegan al
arnés**. Es como medir la calidad del pan y hornear el pan con otra receta.

### Hueco B — la plantilla no ejecuta la técnica

El `run()` generado (`tools.py:418-452`) hace **una sola cosa por paso**: llama
`deep_sweep(f"{step} {objetivo}")` y marca `done/empty/error`. No usa el loop
ReASearch, no llama herramientas, no valida nada contra el blueprint.

El propio diseño lo decía antes de existir la medición D
(`BLUEPRINT_METRIC_DESIGN.md:117-128`): *«Nadie ha ejecutado nunca
`data/agents/task-coevolve/agent_template.py` sobre nada»*. La medición D
posterior prueba que **compila** y que los pasos cambian de estado — no que
produzca valor.

Además los `BLUEPRINT.md` en `data/agents/*` son un **placeholder de 5
líneas**, porque la última regeneración (`run_dimension_d.py:55`) estancó
`generate` a propósito. El blueprint largo solo sobrevive en un directorio de
prueba.

### Hueco C — los PFs **nunca disparan en producción**

`loop.py:607-608` pasa a `apply_pfs` siempre el mismo estado:

```python
{"last_action": {"status": "ok"}, "task": {"type": "research"},
 "attempt_count": turn, "max_attempts": max_turns}
```

Y los 4 built-ins exigen:

| PF | precondición | ¿casa con `status="ok"`? |
|---|---|---|
| `RetryPF` | `status ∈ error\|failure\|failed` | **no** |
| `FallbackPF` | `status ∈ timeout\|exhausted\|error\|rate_limit` | **no** |
| `ValidateBeforeActPF` | `status` de fallo **y** `error_count ≥ 3` | **no** |
| `DecomposePF` | `task.complexity ∈ high\|complex\|…` | **no** — `complexity` no existe en el estado |

README:26 dice *«PFs cableados al loop»* y es **verdad mecánica**: la llamada
existe. Pero **ninguno se ejecuta jamás** en la ruta productiva. Los tests solo
ejercitan el registry con estados que sí casan (`tests/test_harness.py:22-45`).

`evolve_from_failures` (`pfs.py:142-154`) y `ProceduralSkillLayer`
(`layers.py:71-88`) **tampoco tienen callers** fuera de tests.

### Hueco D — no existe evaluación de arneses como variable

Ningún script hace un A/B de **configuraciones de arnés**. Lo más cercano:

- `eval_end2end.py` — evalúa el loop **con** el arnés como sujeto pasivo, sin variarlo.
- `run_dimension_d.py` — evalúa la plantilla, pero solo compila/estado.

El corpus **ya trae la metodología**: *Stop Comparing LLM Agents Without
Disclosing the Harness* y *Evo-Bench* están ingeridos. Se usan como material
de QA ciego, **no para fundamentar cómo se evalúa**.

---

## 4. Umbrales propuestos — **fijarlos ANTES de medir**

> **☑ RATIFICADOS 2026-10-16 (dueño: «Ratificar H1-H4 tal cual»).** Los cuatro
> son ya umbrales vigentes: se miden tal cual y **no se re-bajan después**.

### H1 — La ruta del arnés no es peor que la del blueprint

| | |
|---|---|
| criterio | `implement` **no** puede usar `build_blueprint` crudo: pasa por la ruta verificada |
| umbral propuesto | **100%** de los arneses generados pasan **R4 ≥ 8/15 y R5 ≥ 10/15** con el juez reproducible del Hito 2 |
| por qué 100% | es la misma razón que la dec. 17: si un arnés puede salir sin pasar las reglas que ya existen, la regla no es una regla |

### H2 — El arnés ejecuta la técnica, no solo retrieval

| | |
|---|---|
| criterio | el `run()` generado hace algo que **no** sea llamar `deep_sweep` una vez por paso |
| umbral propuesto | **≥ 3 pasos por arnés** que usen herramientas del loop o validen contra el blueprint; y **≥ 1 paso** que no dependa de `deep_sweep` |
| por qué ahí | 3 es lo mínimo para que la técnica se pueda reconocer; con 1 el arnés es un `for` con nombre de paper |

### H3 — Los PFs disparan de verdad

| | |
|---|---|
| criterio | al menos un PF built-in se ejecuta en la ruta productiva, con estado que llega del loop real |
| umbral propuesto | **≥ 1 PF fire por cada 10 runs** medidas; y **0** runs donde el estado de entrada sea idéntico al de las anteriores 10 |
| por qué medirlo así | si el estado es constante, el harness es decoración; contando fires se ve sin leer código |

### H4 — Existe evaluación de arneses como variable

| | |
|---|---|
| criterio | un script A/B que compare ≥ 2 configuraciones de arnés sobre el mismo golden set, con el mismo juez |
| umbral propuesto | corre de punta a punta, devuelve **n, media e IC 95%** por brazo, y **separa** dos arneses con diferencia real. Validado con un **placebo**: dos brazos idénticos **no** deben dar diferencia significativa |
| por qué el placebo | ya se aprendió en el Hito 1 que sin control negativo una run ruidosa parece un descubrimiento |

---

## 5. Las cuatro fases

### Fase 0 — Ratificar *(sin tokens)* ✅ **CERRADA 2026-10-16**
El responsable fija o cambia H1-H4. **Nada se mide antes.**
**Hecho:** H1-H4 ratificados tal cual + **camino 1** elegido (§7).

### Fase 1 — Cerrar el hueco A *(el más barato)* ✅ **EJECUTADA 2026-10-16**
**Hueco A cerrado** (`instantiate` ya no usa `build_blueprint` crudo).
**H1: NO CUMPLE** — primer intento R4 1/5 · R5 1/5; reparación R1 → **R4 3/5
· R5 1/5**; umbral 100% intacto y cerrado como no cumplido (hallazgo 26).

**Declaración previa — escrita ANTES de generar nada (2026-10-16):**

- **Ruta elegida:** `verify_and_mark(LOOP.run_blueprint(...))` — la misma
  composición que `api.blueprint_p4` (brazo E: P1' + P2 + P4, **sin
  reescritura**), implementada en `tools.build_blueprint_p4`. Motivos
  medidos, uno por candidata descartada:
  1. `blueprint_verified` (D = loop + `verify_and_repair`): la reescritura
     midió **empeorar** el blueprint (§5.8.3) y D queda en R4 **7/15 < 8**
     con el juez calibrado (§8.13). Descartada.
  2. `blueprint_route5` (crítico + degradar puntero): descartada en §8.4.1
     (B8 7,40 → 2,87 · R4 4/15). Descartada.
  3. `blueprint_loop` (G): cumple ambas reglas con el juez calibrado
     (**R4 8/15 · R5 13/15**, §8.12/§8.13), pero no pasa por ningún paso de
     verificación de atribución: es la misma receta de texto que p4
     (`verify_and_mark` no toca el texto), con **menos** verificación.
  4. **Elegida: p4.** Verifica sin reescribir (P3 en modo informe), su texto
     es el mismo que el de G (único con las dos reglas medidas bajo el juez
     calibrado), y satisface literalmente el criterio de H1 («pasa por la
     ruta verificada»). Coste: 0 `generate()` extra sobre el loop.
- **n = 5** arneses (una instancia por cada una de las 5 técnicas sembradas,
  regenerando `data/agents/<slug>`), como dice esta fase. Coste real
  estimado: **~25 `generate()`** (5 arneses × [4 turnos de loop + 1
  blueprint]) + **5 juicios**. *La estimación original «~5 llamadas» era por
  arnés; se corrige aquí, antes de correr.*
- **H1 operativo — ambigüedad resuelta ANTES de medir.** El texto de H1 dice
  «100% de los arneses generados pasan R4 ≥ 8/15 y R5 ≥ 10/15», pero con
  n = 5 la escala /15 no es evaluable (Hito 2 juzga 15 por brazo; por eso
  «≥ 8/15» y «≥ 10/15» son los nombres con que se citan las reglas en todo
  el documento). **Lectura declarada:** vinculante = **100% de los 5
  arneses pasan `r4_ok` Y `r5_ok`** con el juez — es la cláusula con
  justificación propia en la ficha (misma razón que la dec. 17). Los
  recuentos x/5 se reportan al lado, y si se quisiera la escala /15 de
  verdad, se haría con n = 15 como serie nueva y declarada. Si el 100% no
  se alcanza al primer intento: **se declara la errata y se repara, sin
  tocar el umbral** (previsto en esta propia fase).
- **Juez:** `gemini-3.1-flash-lite` @ Google, `temperature=0`, mismo prompt
  que §8.10 (`evals/eval_q1_r4r5.py`), vía `Q1_BASE_URL`/`Q1_API_KEY`
  (mecanismo de la dec. 18). Instrumento con 0% de flips medido (§8.12).
- **Runner y ficheros:** generación en `evals/run_fase1.py` →
  `evals/result_fase1_h1.json` (filas `arm="H1"`) → juicio con
  `evals/eval_q1_r4r5.py --arm=H1 --file=evals/result_fase1_h1.json`.
- **Generación:** sin pin de proveedor — la rotación por defecto (Groq →
  NVIDIA → Gemini) y las temperaturas por defecto, exactamente como
  `api.blueprint_p4`; la generación de todos los brazos del Hito 2 corrió
  sin pin declarado. Si un proveedor cae, se registra en la fila.

Pasos: `instantiate_agent_template` pasa por `tools.build_blueprint_p4` y se
regeneran los 5 arneses con `evals/run_fase1.py`. Después se juzga H1.

#### Resultado del primer intento — **H1 NO CUMPLE** *(medido 2026-10-16)*

Generación: 5/5 arneses con blueprint completo (25 `generate()`, rotación por
defecto). Juicio con el instrumento declarado (`gemini-3.1-flash-lite` @
Google, temp 0); el juez devolvió 503 de demanda durante rato y se esperó —
**sin cambiar de instrumento**.

| arnés | R4 | R5 | veredicto del juez (resumen) |
|---|---|---|---|
| Task-CoEvolve | ✅ | ✅ | cita correctamente y declara los parámetros de las tablas |
| PEARL | ✗ | ✗ | atribuye «GPT-4» como LLM; rellena «Hits@10 ≥ 0,70» |
| Procedural Graphs | ✗ | ✗ | inventa módulos («failure-vs-success refiner»…) y criterios (95%, p < 0,05) |
| ReASearch | ✗ | ✗ | inventa módulos y protocolos («tool-driven optimization loop»…) |
| WikiSkill | ✗ | ✗ | inventa «stratified trace sampling» y una validación pre-release |

**R4 1/5 · R5 1/5 — umbral 100%: NO CUMPLE.** El resultado del primer intento
queda grabado en `result_q1_r4r5.json` (filas `arm="H1"`); no se reescribe.

**Diagnóstico — leído ANTES de declarar la reparación:**

- Los cuatro fallos comparten modo: **componentes y umbrales inventados
  presentados como del paper** (R4 fabrica + R5 rellena).
- `verify_and_mark` no lo ve: P3 solo compara las citas **con puntero** contra
  su chunk; una fabricación sin puntero no tiene nada que comprobar. ReASearch
  salió `verificado=True` (0 violaciones) y el juez lo suspende igual.
- Defecto mecánico aparte, anotado sin maquillar: **3 de 5 arneses tienen
  0 de sus punteros resueltos** (punteros inventados). El juez no los suspendió
  por eso — Task-CoEvolve pasó con 0/10 resolución —, así que H1 mide lo que
  promete (atribución, no resolución); la resolución queda como hallazgo.

#### Reparación declarada — **antes de ejecutarla** (2026-10-16)

- **R1 — qué se hace.** Para **cada arnés suspendido**, una sola vuelta con
  evidencia: el mismo juez devuelve sus `r4_fabricaciones` y `r5_rellenados`
  concretos; un `generate()` recibe esas frases **y la fuente** y debe
  corregir **solo lo señalado** — quitar, apuntar al chunk correcto de la
  fuente o marcar «(propuesta del blueprint)» (R6) —, **sin reescribir el
  resto**: a diferencia de P3 (§5.8.3), aquí no se pide «el documento completo
  ya corregido» (eso destruyó bibliografía y silencios en 3 de 3). Después,
  re-juzgar los reparados con el mismo instrumento (filas `arm="H1R"` en
  `result_fase1_h1r.json`).
- **R2 — tope.** **1 vuelta por arnés.** Si tras ella queda algún
  `r4_ok=false` o `r5_ok=false`, H1 queda **definitivamente NO CUMPLE** para
  esta fase: no hay segunda tirada de dados.
- **R3 — umbral intacto, primer intento intacto.** El 1/5 y el 1/5 no se
  reescriben. El estado final se reporta como «1 pasó sin reparar + X de 4
  reparados», no como un resultado limpio.
- **R4 — coste aparte.** ~4 `generate()` de reparación + 4 re-juicios, con su
  propia fila de coste.

#### Resultado de la reparación R1 — **H1 queda definitivamente NO CUMPLE** *(2026-10-16)*

| arnés | 1er intento (H1) | tras R1 (H1R) | estado final |
|---|---|---|---|
| Task-CoEvolve | R4 ✓ · R5 ✓ | no se toca | **✓ ✓** |
| PEARL | R4 ✗ · R5 ✗ | R4 ✓ · R5 ✗ | ✓ ✗ |
| WikiSkill | R4 ✗ · R5 ✗ | R4 ✓ · R5 ✗ | ✓ ✗ |
| Procedural Graphs | R4 ✗ · R5 ✗ | R4 ✗ · R5 ✗ | ✗ ✗ |
| ReASearch | R4 ✗ · R5 ✗ | R4 ✗ · R5 ✗ | ✗ ✗ |

**Estado final: R4 3/5 · R5 1/5 — umbral 100% NO CUMPLE, cerrado (tope R2:
una sola vuelta).** El umbral no se toca y el primer intento sigue grabado en
`result_q1_r4r5.json` (filas `H1`); las reparaciones, en `H1R` +
`result_fase1_h1r.json`.

**Lecturas para la Fase 2** (descripciones, no re-miden H1):

- La reparación con las frases concretas del juez **arregla R4 a veces** —
  PEARL y WikiSkill quedaron con 0 fabricaciones tras una vuelta: el juez sirve
  de crítico accionable, que es lo que P3 intentó y no logró.
- **R5 no se movió** (1/5 → 1/5): el modo «extrapolar aplicación práctica /
  protocolo operativo» sobrevive a la corrección dirigida. Mismo patrón que en
  el Hito 2: los silencios cuestan más que las fabricaciones puntuales.
- Procedural Graphs y ReASearch **reinciden** en los mismos componentes
  inventados («failure-vs-success refiner»): una vuelta no basta cuando el
  blueprint confabula la misma familia de vocabulario.
- **Coste total de la fase:** ~29 `generate()` (25 + 4 de reparación) + 9
  juicios (5 + 4) + reintentos ante 503 del juez (espera, sin output).

### Fase 2 — Cerrar el hueco B *(el que define el hito)*

**Decisión del dueño (2026-10-16, question tool): «Composición de las 4
capas».** Un arnés en este proyecto = la composición de `harness/layers.py`
(`RuntimeHarness`) **parametrizada por la técnica**: no una lista de tools
suelta ni un programa de precondiciones a mano.

**Forma concreta del `run()` generado — declarada antes de escribirla
(2026-10-16):**

- Por **cada procedimiento** de la técnica (los `STEPS` del grafo, ya
  deterministas): una llamada **real** a una herramienta del loop, en
  rotación `deep_sweep → search_papers → retrieve_evidence → get_subgraph`
  — todas locales, **sin LLM dentro de `run()`**. La llamada pasa por
  `EnvironmentContractLayer.calibrate` (schemas), `validate_call`
  (`ActionRealizationLayer`), `record_action` + `regulate`
  (`TrajectoryRegulationLayer`); los errores incrementan `record_error` y no
  tumban la traza.
- **Paso final de validación contra el blueprint**: cobertura de los
  procedimientos en `BLUEPRINT.md` (presentes / totales, con los que faltan
  a la vista). Es un check real, no decorativo.
- El estado `done/empty/error` sigue anclado al umbral **0.30** del gate de
  la 2ª enmienda de dec. 13 sobre las tools que traen `score`; las tools sin
  campo `score` se declaran con su recuento de items y el detalle dice que
  el gate numérico no aplica a ellas.
- **PFs: no en esta fase.** H3 es la Fase 3 y se arregla en `loop.py`
  (estado real a `apply_pfs`); la plantilla no se adelanta a su propio
  camino hacia H3.
- **Regeneración de las 5 plantillas SIN LLM**: `instantiate` acepta un `bp`
  opcional ya construido (procedimientos del grafo + `BLUEPRINT.md` de la
  Fase 1, texto intacto); la medición D y los tests siguen en verde.

**H2 operativo** (medición gratuita, sin tokens): `evals/run_fase2_h2.py`
ejecuta cada arnés y cuenta pasos con herramienta-del-loop o validación, y
pasos sin `deep_sweep`. Umbral intacto: **≥ 3** y **≥ 1**.

**Resultado (2026-10-16, umbral leído antes de la corrida): H2 CUMPLE —
5/5 arneses.**

| técnica | pasos herramienta/validación | sin `deep_sweep` | errores | verdicto |
|---|---|---|---|---|
| PEARL | 5 | 4 | 0 | CUMPLE |
| Procedural Graphs | 3 | 2 | 0 | CUMPLE |
| ReASearch | 6 | 4 | 0 | CUMPLE |
| Task-CoEvolve | 5 | 4 | 0 | CUMPLE |
| WikiSkill | 5 | 4 | 0 | CUMPLE |

Cada arnés usa la rotación entera de tools que le toca por número de
procedimientos y cierra con el paso de validación de cobertura. El menor de
los cinco es Procedural Graphs (3 = 2 procedimientos + validación), justo en
el umbral — no se redondea hacia arriba: su grafo solo tiene 2 nodos.
Medición en `result_fase2_h2.json` (`arm="H2"`), regeneración de plantillas
sin LLM con `run_fase2_h2.py --regen` (procedimientos del grafo + blueprint
juzgado de la Fase 1, reparado si lo hubo, tal cual se juzgó).

### Fase 3 — Cerrar el hueco C *(bug real, no deuda)*
Arreglar el estado que llega a `apply_pfs` en `loop.py:607-608` para que los
PFs puedan casar, y medir H3.
**Declaración:** si al arreglarlo los PFs disparan *demasiado*, **se ajusta el
umbral H3 antes de publicar, con su propia decisión** — no se esconde el dato.

**Reparación aplicada (2026-10-16, antes de medir H3):** el estado que llega
a `apply_pfs` deja de ser un dict escrito a mano (`last_action.status="ok"`,
`task.type="research"`) y pasa a salir del recorrido real del bucle:

- `last_action.status`: `"error"` en cada `record_error`, `"ok"` tras una
  tool ejecutada; `last_action.tool`: la última tool que corrió.
- `error_count`: contador real de errores de la run; `attempt_count` /
  `max_attempts`: turno y techo reales; `stagnation`: el `flat` del bucle;
  `evidence_count`: evidencia acumulada; `question`: los primeros 200
  caracteres (estado real: la run los conoce).
- **No se inventa `task.complexity`** — DecomposePF no dispara si no la hay.
  Los campos fabricados desaparecen; lo que queda es solo lo que el bucle
  sabe.
- Los fires quedan en el resultado (`pf_fires`, `pf_states`) y en los
  metadatos de la run (`harness_runs.metadata.pf_fires`).

**H3 medición declarada antes de correrla (2026-10-16):** `evals/run_fase3_h3.py`
corre **10 runs reales** de `loop.run(question, isolated=True)` sobre
`golden_qa.jsonl` (questions 1-10, sin juez: H3 no mide calidad) y cuenta
fires y variación de estado. Criterio intacto del §5: **≥ 1 PF fire por cada
10 runs** y **0 runs cuyo estado sea idéntico al de alguna de las 10
anteriores** (fingerprint del `pf_states` completo de la run). Coste estimado:
~10 runs × ~4 turnos = ~40 llamadas al LLM en rotación free tier.

**Resultado (2026-10-16, umbral leído antes de la corrida): H3 NO CUMPLE —
0 fires en 10 runs · 0 estados repetidos.**

| criterio | umbral | medido | verdicto |
|---|---|---|---|
| ≥1 PF fire / 10 runs | ≥1 | **0** (0 de 10 runs con fire) | NO CUMPLE |
| 0 runs con estado idéntico a los 10 anteriores | 0 | **0** (10 fingerprints distintos) | CUMPLE |

**Lectura honesta (descripción, no re-mide):** el cableado ya funciona — el
estado que llega a `apply_pfs` es real (la variación entre runs lo prueba) y
el test de regresión (`test_pfs_disparan_con_estado_real`) demuestra que un
error real dispara `retry_on_failure`. Pero los tres PFs built-in que pueden
casar en la ruta del loop (Retry, Fallback, Validate) **solo casan ante
`last_action.status` en `error|failure|failed|timeout|exhausted|rate_limit`**,
y en estas 10 runs el bucle no falló ni una vez: `generate()` devolvió
siempre y las tools no lanzaron `TypeError`. Sin fallo no hay fire — los PFs
built-in son reactivos, no proféticos. DecomposePF no cuenta: exige
`task.complexity`, que no se inventa (dec. de la reparación).

**El umbral no se toca** (regla de Fase 0). La decisión de si H3 se relee
(«fires cuando hay fallos»), se reformula («el PF dispara en runs con fallo
inducido») o se mantierra tal cual es **del dueño**, con su enmienda y fecha.
Lo medido queda en `result_fase3_h3.json` (filas `arm="H3"`, con
`pf_states` por run).

### Fase 4 — Construir el hueco D *(la evaluación)*
Nuevo `evals/run_harness_ab.py` al estilo de `run_blueprint_ab.py`:
- ≥ 2 configuraciones de arnés
- mismo golden set, mismo juez
- `n`, media, IC 95% por brazo
- **placebo** de dos brazos idénticos como control negativo
- umbrales declarados antes de la corrida

---

## 6. Lo que este plan **no** incluye, y por qué

| descartado | motivo |
|---|---|
| **Cablear `coevolve/selector.py` y `estimator.py`** | `REPORT_COEVOLVE.md` ya lo midió: gana 1,2-1,7× en RMSE pero **contra «no hacer nada» solo gana a ρ=0,5** por 1,45 M de tokens para detectar 0,043. **Decisión tomada con datos.** Se reabre solo con hipótesis nueva. |
| **Cablear `coevolve/wiki.py`** | Está **sin medir**, no descartado. Es un candidato aparte, con su propia declaración. |
| **Sembrar los papers de arneses (docs 6-10)** | Cambia el corpus y el grafo: `seed.py:15-60` solo siembra 5 técnicas. Sembrar más **destruye la comparabilidad** de los brazos B-H y de todos los umbrales del Hito 2. **Si se hace, es un experimento nuevo con línea base propia.** Ver §7. |
| **Cambiar el juez otra vez** | El del Hito 2 (`gemini-3.1-flash-lite`) está medido: 0% de flips en 180 juicios. Su único defecto es compartir familia con el agente, y eso es la decisión **abierta del Hito 2**, no del 3. |

---

## 7. La cuestión de los papers de arneses — **decisión que abre el hito**

Los documentos 6-10 son papers de arneses (`Harness as a Language`,
`Evo-Bench`, `Stop Comparing…`, dos surveys). Están **ingeridos pero sin nodo
en el grafo**: `seed.py` solo siembra 5 técnicas, y `build_blueprint` sobre
ellos devuelve el rechazo N1 (`tools.py:275-280`).

Es decir: **el corpus ya contiene la literatura de arneses y el sistema no
puede usarla para diseñar arneses.**

Hay dos caminos, y **hay que elegir uno antes de empezar la Fase 2**:

| | camino 1 — diseñar sobre las 5 técnicas ya sembradas | camino 2 — sembrar los papers de arneses |
|---|---|---|
| coste | 0 (ya está todo) | cambia el corpus y el grafo |
| comparabilidad | intacta: los brazos B-H siguen siendo referencia | **se rompe**; hay que declarar línea base nueva |
| fidelidad al README | parcial — las técnicas no son de arneses | completa — se diseñan arneses **con** papers de arneses |
| decisión previa necesaria | ninguna | **sí: nueva declaración con umbrales propios** |

**Mi lectura:** el camino 1 cierra el hito sin romper nada y se puede medir
ya. El camino 2 es más fiel al espíritu pero es un hito dentro del hito. Lo
dejo **para decidir en la Fase 0**, junto con la ratificación de H1-H4.

**☑ Decidido en la Fase 0 (2026-10-16): CAMINO 1** — diseñar sobre las 5
técnicas ya sembradas, con los brazos B-H intactos. El camino 2 no se
descarta: si se abre, va como experimento aparte con su propia declaración y
línea base (misma regla que la §6 aplica a sembrar papers).

---

## 8. Cómo se sabrá que está cerrado

La misma estructura que HITO0, HITO1 e HITO2: tabla *criterio / umbral /
medido*, erratas propias numeradas, coste real en tokens.

**Y con la regla de siempre:** si algún umbral no se alcanza, **se dice ahí y
no se maquilla con una media.** El Hito 2 tuvo que declarar R5 como *no
medible* durante toda una sección antes de poder medirla, y el resultado fue
mejor por haberlo hecho así.
