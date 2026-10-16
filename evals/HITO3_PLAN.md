# Hito 3 — arneses válidos: diseño y evaluación

**Estado: RATIFICADO 2026-10-16 — Fase 0 cerrada.**
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

### Fase 1 — Cerrar el hueco A *(el más barato)*

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

### Fase 2 — Cerrar el hueco B *(el que define el hito)*
Que `run()` ejecute la técnica. Aquí hay que decidir **qué es un arnés en
este proyecto**, y esa decisión es la que abre el hito:

- ¿el arnés es una **secuencia de herramientas del loop ReASearch**?
- ¿es un **programa con precondiciones** que el harness ya sabe ejecutar?
- ¿es la **composición de las 4 capas** (`harness/layers.py`) parametrizada
  por la técnica?

**Esta elección no se delega a un LLM en caliente.** Se decide aquí, se escribe
y se mide contra ella.

### Fase 3 — Cerrar el hueco C *(bug real, no deuda)*
Arreglar el estado que llega a `apply_pfs` en `loop.py:607-608` para que los
PFs puedan casar, y medir H3.
**Declaración:** si al arreglarlo los PFs disparan *demasiado*, **se ajusta el
umbral H3 antes de publicar, con su propia decisión** — no se esconde el dato.

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
