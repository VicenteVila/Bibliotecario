# Diseno de la metrica de blueprints (primera tarea del Hito 2)

**Borrador, NO aprobado.** 2026-10-10. Escrito en paralelo con las runs del
Hito 1, como decidio el responsable (decision 4): este diseno **no castea
tokens** y Hito 2 arranca con metrica puesta en vez de con una semana de vacio.

El Hito 1 deja claro que `blueprint` e `implement` "no tienen ni metrica
definida: nadie ha escrito que seria un blueprint bueno". Eso es lo que se
resuelve aqui: **primero se define que es bueno, despues se mide.**

---

## 1. Lo que el sistema produce hoy (hechos del codigo)

Antes de proponer un umbral, hay que saber que hay. Todo sale de
`bibliotecario/agent/tools.py:183-217` y `bibliotecario/api.py:56-61`.

### 1.1 `build_blueprint` es UNA sola llamada al LLM

```python
procs = P.list_procedures(technique=technique) or P.list_procedures()
paths = PEARL.retrieve_evidence(f"{technique} {goal}", top_m=5)
prompt = (f"Guía accionable para implementar la técnica '{technique}' con objetivo: {goal}.\n"
          f"Procedimientos conocidos: {', '.join(names)}\nCadenas del grafo:\n{chain}\n\n"
          "Devuelve blueprint markdown: módulos, dependencias, orden, validación, riesgos.")
bp = generate(prompt, max_tokens=1500) or "(sin LLM: usa los procedimientos listados)"
```

Consecuencias que condicionan cualquier metrica:

| hecho | por que importa |
|---|---|
| **Una llamada, no un loop de 4 turnos** | Medir la capacidad de blueprint es **barato**: ~3-5k tokens por blueprint, no los ~30k de una pregunta del blind. |
| **El prompt NO pide citas** | A diferencia del QA, que exige `[doc:chunk]` en cada afirmacion, el blueprint **puede inventar módulos y dependencias sin que nada se note**. La fabricacion aqui es invisible por construccion. |
| **`list_procedures(technique) or list_procedures()`** | Si la tecnica **no existe**, cae en silencio al grafo **completo**: un blueprint para una tecnica inexistente listaria procedimientos de *otras* tecnicas como si le correspondieran. Bug de honestidad. |
| **`generate(...) or "(sin LLM...)"`** | Si todos los proveedores fallan, devuelve un texto fijo. Sin eso se contaria como blueprint valido. |
| El `blueprint` se guarda **crudo** | Es el markdown que el LLM devolvio, sin ninguna verificacion posterior. |

### 1.2 `instantiate_agent_template` genera un agente stub

```python
def run(context: dict) -> dict:
    trace = []
    for step in STEPS:
        trace.append({"step": step, "status": "todo"})
    return {...}
```

**Cada paso sale siempre `"todo"`**: el agente generado no hace nada, por
diseno. Esto descarta de raiz un criterio obvio — "¿el agente instanciado
funciona?" — porque se cumpliria siempre y no distinguiria nada.

~~Ademas `data/agents/` esta **vacia**: `implement` no se ha invocado nunca en
produccion. No hay un solo blueprint que evaluar.~~
**Actualizado 2026-10-11:** `data/agents/` ya no esta vacia. Ver §1.4.

### 1.3 Hay 5 tecnicas sembradas

`knowledge/seed.py` define el grafo procedural de: **Task-CoEvolve, PEARL,
WikiSkill, Procedural Graphs, ReASearch**. Son el universo conocido y el
material con el que se puede construir una referencia.

### 1.4 Primera ejecucion real (2026-10-11)

`implement "Task-CoEvolve" "validar mi agente antes de cada release"`.
Coste: **una sola llamada, ~1.5k tokens**. Salio en
`data/agents/task-coevolve/{BLUEPRINT.md,agent_template.py}`.

Todo lo que sigue esta **medido sobre esa salida**, no deduido del codigo.

| # | hallazgo | evidencia | ya se preveia? |
|---|---|---|---|
| **H1** | **El blueprint sale truncado a mitad de tabla** | `BLUEPRINT.md` (1.025 bytes) termina literalmente en `\| :---`. `generate(..., max_tokens=1500)` no alcanza y **el fichero se guarda igual, sin aviso** | No: `max_tokens=1500` se dio por suficiente |
| **H2** | **Promete lo que nuestra propia medicion contradice** | El blueprint dice *"manteniendo garantías estadísticas de precisión"* y encadena `[S-max Final Selection Gate] ──► [CI/CD Release Decision]`. `REPORT_COEVOLVE.md` dice: *"contra el baseline que importa… solo gana en el mejor de los casos… **Decisión: no se gasta**"* | Parcialmente — §1.1 ya avisaba de que "la fabricación aqui es invisible"; no de que **contradiria un veredicto interno del propio proyecto** |
| **H3** | **Cero citas, módulos generados de la nada** | `grep -c "doc:\["` → **0**. `Adaptive Harness Execution Engine`, `History Profiler` y demas no vienen de ninguna parte | **Sí, literalmente.** §1.1: *"el blueprint puede inventar módulos y dependencias sin que nada se note"* |
| **H4** | **El stub hace exactamente nada** | `run()` devuelve los 4 pasos en `"todo"` y termina | **Sí**, §1.2 |
| **H5** | **El fallback silencioso existe, pero el modelo lo salvo** | Pedida una tecnica inexistente, `list_procedures(technique) or list_procedures()` **tiro al grafo completo: 18 procedimientos ajenos** entraron en el prompt. El LLM **se nego** a escribir el blueprint y explico que la tecnica no existe | El bug **si**; la salvacion **no** — §1.1 lo daba por perdido |

**H5 es una correccion a mi propio documento y hay que dejarla escrita.**
El bug de codigo esta ahi exactamente como se predijo, pero el modelo no lo
explotó: se nego, y de paso dejo constancia de que estaba usando su
**conocimiento parametrico** (*"hasta la fecha de corte de mi conocimiento:
junio 2024"*), no el corpus. En esa ruta el sistema no esta leyendo los papers
que ingirio — y lo dice.

**H2 es el que importa para la metrica.** No es un error de forma: es un
blueprint que **recomienda conectar una tecnica a un release gate** cuando
nuestro propio informe la descarto con datos. Y al no haber citas (H3),
**no existe ninguna comprobacion mecanica que lo detecte**. Eso es exactamente
lo que §2.A llama *"ningun modulo inventado sin respaldo en el corpus"*,
y hoy es indetectable sin referencias escritas a mano (§3.3).

---

## 2. Que hay que medir

Un blueprint es bueno si **un ingeniero podria usarlo para implementar la
tecnica**. Eso se descompone en tres cosas que son critica y
separadamente verificables:

### A. Fidelidad — ¿refleja el paper?
- Los pasos reales de la tecnica aparecen, en orden razonable.
- **Ningun modulo o paso inventado** sin respaldo en el corpus.
- Los `procedures` citados existen **para esa tecnica** (cae la trampa del
  fallback silencioso de la seccion 1.1).

### B. Accionabilidad — ¿se puede empezar?
- Nombra componentes concretos, no "el sistema procesa los datos".
- Incluye **una validacion que se podria ejecutar** de verdad.
- Las dependencias son comprobables.

### C. Integridad — ¿cumple lo prometido?
- Los cinco apartados que el propio prompt exige: **modulos, dependencias,
  orden, validacion, riesgos**.

---

## 3. La metrica propuesta

Se mantiene la estructura del Hito 0/Hito 1: **suelo mecanico gratis + piso de
calidad con juez + referencias hechas a mano**. Lo que no se mide no se
puede declarar cumplido.

### 3.1 Suelo mecanico (gratis, determinista)

El equivalente al "fabricacion = 0%" del Hito 0: cosas que se pueden comprobar
sin tocar un LLM y que **no se pueden negociar**.

| # | comprobacion | falla si |
|---|---|---|
| **B1** | Los **5 apartados** estan en `BLUEPRINT.md` | falta alguno de modulos/dependencias/orden/validacion/riesgos |
| **B2** | `agent_template.py` **compila y `run()` ejecuta** sin excepcion | `py_compile` falla o `run()` levanta |
| **B3** | Todos los `procedures` **existen para esa tecnica** | algun procedimiento viene del fallback a "todas las tecnicas" |
| **B4** | El resultado **no es el placeholder** `"(sin LLM: usa los procedimientos listados)"` | los proveedores fallaron y nadie se entero |
| **B5** | *(decision)* **cada modulo/dependencia principal lleva `[doc:chunk]`** | se reclama una cita que el prompt nunca pidio |
| **B6** | `BLUEPRINT.md` **termina en una estructura markdown completa** | acaba en una tabla `| :---` sin filas, o en un ` ``` ` sin cerrar — es decir, `max_tokens=1500` no alcanzo y **nadie lo sabe** (medido: H1) |
| **B7** | *(propuesta §5.5-P3)* **`BLUEPRINT.md` lleva `[doc:chunk]`** — umbral `>= 3` distintas (§6 dec. 1) | da **0**, que es exactamente lo que midio **H3** |

**B5 es la decision importante.** Hoy el prompt no pide citas, asi que B5
fallaria al 100%: o se anade la exigencia de cita al prompt (y se mide de
nuevo, como en el Hito 0), o se declara que el blueprint es una guia de
orientacion y la fidelidad la juzga un modelo. **No se puede medir el
incumplimiento de una regla que nadie puso.**

`procedures` sale del grafo sembrado asi que B3 es literalmente gratis
(un `set` de nombres), y B1/B2/B4/B6 son gratis igual (B6 es leer las
dos ultimas lineas del fichero). B5 solo si se cambia el prompt.

### 3.2 Piso de calidad (juez, si)

Rubricas 1-5 con el mismo juez de siempre (`openai/gpt-oss-20b`, familia
distinta al agente), **declaradas antes de medir**:

| # | rubrica | lo que pregunta |
|---|---|---|
| Q1 | **fidelidad** | ¿los pasos corresponden a lo que el paper describe, o es relleno plausible? |
| Q2 | **accionabilidad** | ¿un ingeniero sabria por donde empezar mañana? |
| Q3 | **concrecion** | ¿nombra componentes o describe generico? |
| Q4 | **coherencia interna** *(propuesta, §6 dec. 6)* | ¿afirma algo que un `REPORT_*.md` del propio proyecto contradiga? H2 es el caso de prueba |

Umbrales propuestos (a confirmar — **borrador de §6 dec. 3**): suelo en
**B1-B7 = 100%**, juez `mean >= 4.0` en Q1-Q3 **y ninguna rubrica `< 3.0`**, y
**Q4 = 0 contradicciones** (binario). El 4.0 es mas bajo que el 4.50 del Hito 1
porque hay **3 rubricas en vez de una pregunta de 35 items**, o sea menos
muestra y mas ruido por item: bajar el umbral compensa el MDE peor.

### 3.3 Referencia escrita a mano (el trabajo que nadie ha hecho)

El problema real del Hito 2 **no es el score, es que no hay oro**: el juez no
sabe si el blueprint es correcto para PEARL, solo si suena bien. Lo mismo que
sin `golden_qa.jsonl` no se podria medir QA, sin referencias no se puede medir
fidelidad.

Propuesta: **escribir a mano 5 blueprints de referencia** (una por tecnica
sembrada), directamente de los papers, con lo que debe aparecer y lo que no
deberia. Son ~5 documentos de trabajo, **0 tokens**.

Con ellas la fidelidad pasa a ser comprobable de verdad: se cuentan los pasos
de referencia que el sistema **cubre**, los que **omite** y los que **inventa**.
Ese triple — *cubierto / omitido / inventado* — es la medicion, y es el
equivalente exacto de la fabricacion del Hito 0.

---

## 4. Coste (es la noticia buena)

Porque `build_blueprint` es **una llamada**, no un loop:

| que | estimacion |
|---|---|
| 5 tecnicas x 3 runs = 15 blueprints | **~60-75k** |
| juez sobre los 15 | **~30k** |
| referencias a mano | **0 tokens** (tiempo de diseño) |
| **total** | **~100k** |

Frente a los ~9-10M del Hito 1. **Hito 2 es dos ordenes de magnitud mas barato
que Hito 1**, y es el frente que el README promete como "la mitad del valor".

Ojo: eso mide la **capacidad** (`api.blueprint()` directo). Lo que cuesta de
verdad — y es una pregunta distinta — es si el agente **llama a la herramienta
cuando debe** en un `ask()` completo: ahi si hay loop de turnos y el coste se
acerca al del blind. Se plantea como segunda fase, no primero.

---

## 5. Propuesta: separar plan y build

Planteada por el responsable el 2026-10-11 a partir de H2/H3. **No aprobada** —
**recomendación en §5.7: sí, pero condicionada al A/B**.

### 5.1 El hecho que la sostiene

```python
def ask(question, max_turns=10):   return LOOP.run(question, max_turns)   # loop completo
def blueprint(technique, goal):    return build_blueprint(...)            # generate() directo
```

`build_blueprint` **se salta el loop entero**: no hay turnos, no hay
herramientas, no hay reglas de cierre, no hay obligacion de cita, no hay
abstencion. Es `generate(prompt, max_tokens=1500)` suelto.

O sea: **H3 (0 citas) no es un fallo del prompt de blueprint, es que ese prompt
nunca pasa por donde se exige la cita.** Todo lo que costo 11 M construir para
`ask()` **no llega a `blueprint()`**, y no porque las reglas sean inadecuadas
para diseno sino porque **no se aplican nunca**.

### 5.2 Las dos fases

La idea original era un *modo* que distingiera «responder/makear blueprints»
(precision) de «implementar arneses» (razonamiento y abstraccion). **Se descarta
como router**: clasificaria la peticion justo donde la linea es delgada —
*«lee el paper de PEARL y dime como implementarlo para mi caso»* es extractiva y
generativa en la misma frase — y un error de clasificacion seria **silencioso e
inmedible**, que es exactamente lo que el Hito 1 vino a eliminar.

Se propone en su lugar **secuenciar, no clasificar**:

| fase | que produce | regla de honestidad |
|---|---|---|
| **Plan** | especificacion anclada | `item -> [doc:chunk]`; si no esta, se abstiene |
| **Build** | implementacion / blueprint | cada decision **traza a un item del plan**; lo que no trace, va marcado como sintesis sin reclamar cita |

Toda peticion pasa por las dos, asi que **no hay que decidir de antemano si es
pregunta o implementacion**. La ambiguedad deja de ser un problema de
clasificacion y pasa a ser un orden de ejecucion.

Y la regla cambia de fase **sin que eso sea una puerta de escape**: las fases
estan separadas en el tiempo, no compiten por la misma peticion.

### 5.3 Por que la precision no baja en la fase build

Premisa a discutir: la implementacion necesitaria *menos* precision y *mas*
abstraccion. **No se sostiene con H2.** El blueprint de Task-CoEvolve uso
razonamiento y abstraccion para concluir *conectar a un release gate* — y
**estaba equivocado**, contradiciendo `REPORT_COEVOLVE.md`.

**Abstraccion sin anclaje es la misma fabricacion con otro sombrero.** Lo que
cambia no es cuanto se exige, sino **sobre que**: en QA es precision sobre un
*valor* (`89 tasks [3:20]`), en build es precision sobre un *mecanismo*
(*«este paso calcula X porque el paper dice Y»*).

### 5.4 El riesgo, y por que se cierra estructuralmente

El fallo clasico de plan/build: **el modelo escribe un plan impecable y luego
lo ignora.** El plan se vuelve decoracion.

No se cierra con una instruccion («sigue el plan»), sino **haciendo que las
citas del plan fluyan al resultado**: si el blueprint tiene que citar y las
citas vienen de la recuperacion de la fase plan, la trazabilidad no depende de
que el modelo sea disciplinado — **depende de por donde pasa el dato**.

### 5.5 Cambios concretos

| # | cambio | coste |
|---|---|---|
| **P1** | `build_blueprint` pasa por `LOOP.run()` en vez de `generate()` suelto | reutiliza lo construido; el blueprint pasa de ~1,5 k a ~20-30 k tokens |
| **P1'** | **Correccion de P1**: el loop **dirige**, pero el blueprint se escribe con la **tool** `build_blueprint`, que conserva su propio presupuesto | ver R5 |
| **P2** | El prompt de blueprint exige dos secciones: *lo que el paper dice* (con `[doc:chunk]`) y *mi propuesta de diseno* (marcada, sin cita) | cambia el prompt → obliga a re-medir, como en el Hito 0 y como `max_tokens` |
| **P3** | **B7** en el suelo mecanico: el blueprint **lleva `[doc:chunk]`** | gratis (mismo `grep` que dio 0 en H3) |
| **P4** | **Sin router.** Un solo regimen de honestidad, aplicado por afirmacion y no por peticion | — |

**P1 tal como estaba escrito estaba mal.** `loop.py:563` genera *cada turno* con
`max_tokens=1024`, y no hay un presupuesto mayor para la respuesta final: el
turno en que no se llama tool **es** la respuesta. Enrutar `build_blueprint` al
loop cambiaria el tope de **1500 a 1024** — o sea, **empeoraria H1**, que ya dice
que 1500 no alcanza. Por eso existe **P1'**: el loop orquesta la fase *plan*, y
el blueprint se escribe mediante la tool, que mantiene (y sube) su propio tope.

Coste del P1 medido sobre el presupuesto de §4: 5 tecnicas x 3 runs ≈
**400 k tokens** en vez de ~60-75 k. Sigue siendo **dos ordenes de magnitud**
por debajo del Hito 1, y es el precio de que las reglas lleguen al punto donde
se emiten las afirmaciones.

**B7 hoy daria 0.** Con P1 deja de darlo por construccion — que es la
diferencia entre comprobar un resultado y haber construido el sistema para que
pase.

### 5.6 Vuelta de tuerca: lo que puede salir mal

P1 no es gratis ni seguro, y decirlo antes de medir es lo que nos costo el
Hito 1:

| # | riesgo | por qué es real | mitigacion |
|---|---|---|---|
| **R1** | **El loop empeora el resultado** | Mas turnos = mas superficie para alucinar. H5 solo salvo el fallback porque el modelo se nego *por suerte*, no por diseno | **A/B obligatorio** — ver 5.7 |
| **R2** | **La varianza de blueprint sube** | Una `generate()` a `temperature=0.0` es casi determinista; un loop con recuperacion **no lo es**. En QA medimos ±0,46 de run a run, y aqui solo habria **15 muestras** (5 tecnicas x 3 runs): con esa n, cualquier umbral es papel mojado | Fijar la recuperacion del plan (mismos chunks en todas las runs) y declarar el MDE **antes** de la primera run, no despues |
| **R3** | **El loop no converge** | `max_turns` agotado sin producir blueprint, o el agente se va a buscar cosas que no son el blueprint | Acotar `max_turns=6`; **B4** ya detecta el placeholder silencioso |
| **R4** | **El plan se vuelve decoracion** (§5.4) | El caso no cubierto por B7: citas presentes pero desligadas de las decisiones | Q1 pasa a preguntar explicitamente si los pasos se apoyan en las citas citadas, no solo si "suenan" |
| **R5** | **P1 empeora H1** | `loop.py:563` acota **cada turno** a `max_tokens=1024` y no hay presupuesto mayor para la respuesta final. El tope actual de `build_blueprint` es **1500**, y H1 ya dice que **no alcanza** → enrutarlo al loop lo bajaria a 1024 | **P1'** (§5.5): el loop dirige, la tool escribe con su propio presupuesto, subido a partir de `1500` segun decida el punto 2 de §6 |

**R2 es el que decide el coste real.** Si la varianza sube al meter el loop,
la medicion de Hito 2 deja de poderse hacer con 3 runs y volvemos al mismo
problema que tuvo que arreglarse reescribiendo el umbral del Hito 1.

### 5.7 Recomendación — **Sí, condicionado**

> **Adoptar P1-P4, pero NO adoptarlos a ciegas.** Medir primero.

El proyecto completo tiene un unico principio que ha funcionado: *mide antes de
gastar*. P1 cambia la estructura de la llamada, asi que **toca medirlo igual
que se midio la temperatura en el Hito 0**.

**Diseno del A/B** — dos brazos nuevos sobre las mismas 5 tecnicas, mas el
baseline que ya existe (H3 = 0 citas, coste 0):

| brazo | que es | coste |
|---|---|---|
| **A** (ya hecho) | `generate()` actual, sin exigir cita → H3 = **0** | 0 |
| **B** | `generate()` + **P2** (exigir cita), sigue sin loop | ~10 blueprints ≈ **100-150 k** |
| **C** | **P1** (loop) + **P2** | ~10 blueprints ≈ **100-150 k** |

- **B vs A** aísla el efecto del **prompt**.
- **C vs B** aísla el efecto del **loop** — que es la pregunta que hace la propuesta.

**~200-300 k tokens en total**, comparable al coste de toda la medicion
propuesta en §4. Si **C no gana a B** en B7/Q1, **P1 se descarta** y nos
quedamos con el prompt en una sola llamada: mas barato y sin el riesgo R2.

Sin este A/B, P1 seria exactamente el error que documenta la Errata 1 del Hito
1: **un cambio que se adopta porque suena mejor, sin haberlo medido.**

---

## 6. Lo que decide el responsable antes de medir

**BORRADOR de propuestas — nada de lo que sigue está decidido.** Cada punto
trae un numero concreto para poder decir que sí o que no, no un "a ver". La
regla aprendida en el Hito 1 se respeta: **todo se fija ANTES de la primera run.**

### Decisión 0 — §5, plan/build (P1-P4)

**Propuesta: SÍ, condicionada al A/B de §5.7.** A-B aísla el prompt, C-B aísla
el loop; si C no gana a B en B7/Q1, **P1 se descarta** y nos quedamos con solo
P2 (más barato, sin riesgo R2). Coste del A/B: **~200-300 k**.

*Si se dice no:* B5/B7 quedan en comprobar un resultado que el sistema no está
diseñado para producir, y Hito 2 se mide con una métrica que ya sabemos que va
a dar 0 en el eje que importa.

### Decisión 1 — B5/B7, citas `[doc:chunk]` en el blueprint

**Propuesta: SÍ. Umbral `>= 3` citas distintas** (módulos, dependencias y orden
son tres secciones que afirman contenido del paper), **más el ratio**
`citas / afirmaciones técnicas` **como diagnóstico, sin gatear**.

Con P2 la exigencia va en el prompt, así que **B7 deja de ser imposible por
construcción** y pasa a ser comprobable — que es lo único que la vuelve útil.

*Si se gatea el ratio desde ya:* cae el riesgo de una cita decorativa de 300
palabras que salve B7 sin anclar nada. Por eso el ratio se **mide** primero y
se gatea después, con datos.

### Decisión 2 — presupuesto (`max_tokens`) y turnos

**Propuesta, dos números:**

| parametro | hoy | propuesto | razon |
|---|---|---|---|
| `max_tokens` de la tool de blueprint | `1500` | **`3000`** | H1 ya demostró que 1500 trunca |
| `max_turns` del blueprint | `10` (default de `ask`) | **`6`** | plan = recuperar → verificar → escribir; 10 sobra y multiplica R2/R3 |

**Con precondición declarada:** si en el **primer brazo** `B6 < 100%`, se sube
a `4000` y **se reinicia la run completa**. Nunca se mide sobre un blueprint
truncado. *Ese es el error de la Errata 2 del Hito 1: elegir el umbral
después de ver los números.*

### Decisión 3 — umbrales

**Propuesta:**

| eje | umbral |
|---|---|
| **B1-B7** (suelo mecánico) | **100%** — son deterministas, o pasan o se arregla el sistema |
| **Q1-Q3** (juez) | **`mean >= 4.0` Y ninguna rubrica `< 3.0`** |
| **Q4** (nueva, ver decisión 6) | **0 contradicciones** — binario |

**La condición `ninguna < 3.0` es nueva** y es la lección directa de H2: un
blueprint que contradice `REPORT_COEVOLVE.md` perfectamente pudo haber sacado
buena nota de media. **La media esconde exactamente el fallo que más importa**,
igual que la media de calidad del Hito 1 escondía que `r5` fabricaba.

### Decisión 4 — el fallback silencioso (§1.1)

**Propuesta: arreglarlo como bug.** Técnica inexistente → `list_procedures(technique) or list_procedures()` **tira las 18 técnicas ajenas al prompt**.

- **B3 lo detecta, pero después** — cuando ya se han pagado los tokens y el
  blueprint ya afirma procedimientos de técnicas que no son la suya.
- **H5 enseña que hoy lo salva el modelo, no el código**: se negó a escribir el
  blueprint *por suerte*, con las 18 técnicas metidas en el prompt. **Esa no es
  una garantía, es un golpe de suerte.**

**Fix:** si `technique` no existe, devolver **vacío** y que el prompt diga «no
existe». +1 test. **0 tokens.**

### Decisión 5 — referencias escritas a mano

**Propuesta: 5 ficheros en `evals/refs/`, uno por técnica sembrada, escritos por
el responsable — no por el modelo.** Ese es precisamente el punto: si las
escribe el modelo, Q1 se juzga a sí mismo.

Alcance acotado y **0 tokens**: por paper, los **4-6 pasos que deben aparecer**
y **lo que no debe aparecer**. Estimación ~1-2 h por técnica.

**Sin esto, Q1 no es falsable** y no se puede declarar cerrado Hito 2 — pasa a
medir si el blueprint *suena* bien, que es exactamente H3.

### Decisión 6 — H2, el problema de fondo

**Propuesta: nueva rubrica Q4 — coherencia con la evidencia interna.**

El juez recibe el **extracto del informe interno relevante** para esa técnica
(para Task-CoEvolve, `REPORT_COEVOLVE.md`) y se le pregunta: *«¿el blueprint
afirma algo que este documento contradiga?»* → **0 contradicciones**.

Coste: ~2-3 k tokens de contexto × 15 runs ≈ **45 k**.

Es la **misma forma de gate que la fabricación del Hito 1** (0 = pasa, >0 = no
pasa), aplicada al eje que H2 demostró estar **completamente sin medir**. Y es
lo único de §6 que **no se arregla con un umbral**: no hay nota que compense un
blueprint que contradice nuestros propios datos.

---

---

## 7. Como se sabra que Hito 2 esta cerrado

La misma estructura: tabla *criterio / umbral / medido* con el valor real de la
run final, coste real en tokens, y la seccion de erratas si algo resulta estar
mal medido. Y **el suelo mecanico se declara ANTES de la primera run**, no
despues de ver los numeros.
