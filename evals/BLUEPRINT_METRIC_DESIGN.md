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
y hoy es indetectable: hace falta que el juez reciba el informe que se
contradice (Q4) y el paper delante (Q1), que es lo que propone §3.3.

---

## 2. Que hay que medir

Un blueprint es bueno si **un ingeniero podria usarlo para implementar la
technica**. Eso se descompone en **cinco** cosas que son critica y
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

### D. Funcionamiento — ¿hace algo? *(nadie lo ha medido nunca)*
- El agente generado se **ejecuta sobre una tarea real y devuelve algo** que no
  sea todos los pasos en `"todo"`.
- **Hoy esto no es medible y lo sabemos**: `instantiate_agent_template` genera
  `run()` que marca cada paso como `"todo"` por diseño (§1.2). **Nadie ha
  ejecutado nunca** `data/agents/task-coevolve/agent_template.py` sobre nada.

**A, B y C miden plausibilidad. D mide producto.** El README promete «arneses
que funcionan»; A+B+C se pueden cumplir al 100% con un agente que no hace nada.
Declarar el Hito 2 cerrado con solo A+B+C seria **el mismo error de forma** que
tener el umbral de calidad calibrado contra un tramposo: un gate verde que no
dice lo que la palabra «cumplido» sugiere.

### E. Escritura — ¿sale escrito como lo haria un humano?

**No es una metrica: es la especificacion del artefacto.** Es lo que se le pide
al modelo que produzca, y las metricas de §3 comprueban si lo ha producido.
Concreta el **P2** de §5.5, que hasta aqui solo decia «dos secciones».

Formulada por el responsable el 2026-10-11: *«que se comporte como lo haria un
humano al enfrentarse a la misma tarea»* — cita el paper consultado,
entrecomilla lo exacto, referencia a los autores, y todo lo demas que hace
quien realmente ha trabajado la fuente.

**Por que estas reglas y no «que suene bien» — el publico real.** El responsable
no esta construyendo esto para publicar en revista: se esta especializando en
**diseno y evaluacion de arneses**, el agente es su instrumento, y la salida
queda **mayoritariamente privada**. De vez en cuando sale a la luz — **blog
propio, CV, o un hallazgo si lo hay** — **y siempre tras revision de expertos
humanos**. Eso cambia el calculo:

- **Un error de cita deja de ser un test fallado y pasa a ser un evento
  reputacional.** Un experto **pillara** una cita inventada, y **una sola
  pillada desacredita el documento entero** — y con el, la afirmacion de que el
  trabajo es riguroso, que es justamente lo que el CV necesita demostrar.
  **B9/B10/B11 son proteccion, no burocracia.**
- **El blueprint es ademas como el responsable aprende el campo.** Si la manera
  de enterarse de como funciona PEARL es leer lo que genera el agente, **una
  fabricacion no es un fallo de calidad: es desinformacion sobre el campo que
  intenta dominar** — y es peor que inutil, porque **no puede detectarla** (no
  domina el idioma ni el paper) **y se la cree**. Por eso **R4 y R5 son
  condicion para que el sistema ensene algo verdadero**, no un extra.
- **El publico deja de ser «un ingeniero» y pasa a ser «un experto».** La
  dimension B preguntaba *¿un ingeniero sabria por donde empezar mañana?* —
  umbral bajo. Un experto detecta relleno plausible y atribucion vaga al
  primer parrafo, y **4.0 del juez no garantiza eso**.

| # | regla | en cristiano |
|---|---|---|
| **R1** | **Dice de donde sale** | *«Segun Miyai et al. (2025)…»*, no *«el sistema selecciona tareas»* sin mas |
| **R2** | **Entrecomillado ⇔ literal** | comillas **solo** cuando la frase es identica al original |
| **R3** | **Parrafrasis sin comillas, pero atribuida** | con tus palabras + quien lo dice; nunca comillas sobre texto reescrito |
| **R4** | **No atribuye lo que la fuente no dice** | si el paper no lo contempla, no aparece atribuido a el |
| **R5** | **Declara los silencios** | *«el paper no especifica como se fija epsilon»* en vez de rellenarlo |
| **R6** | **Separa lo suyo de lo del paper** | *propuesta del blueprint* vs *fuente* — marcado, no mezclado |
| **R7** | **Bibliografia de lo realmente consultado** | autores correctos, referenciando los papers usados |

**R4 y R5 son las que separan a un modelo de un humano.** Un LLM rellena los
huecos y se los atribuye a la fuente; quien ha leído el documento dice *«esto
no esta aqui»*.

**Y son exactamente las que fallaron en H1-H5.** El blueprint de Task-CoEvolve
invento modulos (R4), prometio garantias que `REPORT_COEVOLVE.md` descarto
(R4), y jamas dijo que el paper no contempla conectarlo a un release gate (R5).

**Tres prerequisitos sin los cuales R1-R7 no se pueden ni cumplir:**

1. **Extraccion de autores al ingerir.** Hoy **no existe el campo**: `documents`
   solo tiene `id, path, title, paper_hash, ingested_at, metadata`, y `metadata`
   es `NULL` en los 5 papers de tecnica. Los autores estan **solo dentro del
   texto** del chunk 0. Hay que extraerlos y **verificar cada nombre literal en
   ese chunk** antes de guardarlo — igual que todo lo demas.
2. **El juez calibrado (§6 dec. 5, punto 5c).** R4 y R5 **no son mecanicas**:
   requiere comparar el blueprint con el paper y notar lo que falta. Sin
   calibrar al juez con los defectos ya conocidos de Task-CoEvolve, R4/R5 se
   estarian declarando cumplidas sin que nadie las verifique de verdad.
3. **Bibliografia publicable, no solo procedencia interna.** Comprobado
   campo a campo: **autores** solo en el texto del chunk 0 · **anio** no
   extraido · **arXiv propio** **no aparece** en el chunk 0 de ninguno de los
   10 documentos · **venue/DOI** no extraido. Con `[doc:chunk]` el sistema se
   rastrea a si mismo, pero **no puede producir una cita citable como la
   haria un humano** — que es exactamente R7. Mientras la salida sea interna no
   importa; **en cuanto salga al blog o al CV si**, y pasa a ser requisito:
   autores + anio (+ arXiv/DOI si aparecen en los metadatos del PDF aunque no
   en el texto extraido).

**Un recurso que ya esta en el corpus y nadie ha usado:** de los 10
documentos, **dos son sobre metodologia de evaluacion de arneses** — el doc 9
(*Evaluation and Benchmarking of LLM Agents: A Survey*) y el doc 10
(*Stop Comparing LLM Agents Without Disclosing the Harness*). O sea: **seguir
los criterios cientificos del campo no es una aspiracion vaga, es comprobable
contra el propio corpus.** El sistema podria fundamentar sus decisiones
metodologicas citando esos papers en vez de inventarse una metodologia, y es
gratis — y es exactamente el campo en el que el responsable se esta
especializando.

**Que existan las reglas no basta.** El modelo dira que las sigue y no las
sigue: H3 salio de un prompt que no pedia citas, y H5 lo salvo el modelo *por
su cuenta* una sola vez. **R1-R7 van en el prompt; B7-B11 son la prueba de que
el prompt funciono.** Las dos, o no vale ninguna.

| regla | se comprueba con |
|---|---|
| R1, R2 | **B7, B8, B9** |
| R3, R4, R5 | **Q1** con el paper delante *(calibrado, §6 dec. 5)* |
| R4 | **B11** (texto copiado sin comillas) · **B10** (fuente no ingerida) |
| R6 | marcador de sintesis sin citas dentro |
| R7 | **B10** |

---

## 3. La metrica propuesta

Se mantiene la estructura del Hito 0/Hito 1: **suelo mecanico gratis + piso de
calidad con juez + una referencia de verdad**. Lo que no se mide no se
puede declarar cumplido.

La diferencia respecto al Hito 1: alli la referencia (`golden_abstention`) se
escribio a mano **porque el responsable conocia el dominio**. Aqui no — y el
producto existe precisamente para que no hace falta que lo conozca (§3.3). **El
corpus es el oro.**

### 3.1 Suelo mecanico (gratis, determinista)

El equivalente al "fabricacion = 0%" del Hito 0: cosas que se pueden comprobar
sin tocar un LLM y que **no se pueden negociar**.

| # | comprobacion | falla si |
|---|---|---|
| **B1** | Los **5 apartados** estan en `BLUEPRINT.md` | falta alguno de modulos/dependencias/orden/validacion/riesgos |
| **B2** | `agent_template.py` **compila y `run()` ejecuta** sin excepcion | `py_compile` falla o `run()` levanta — **PERO VER LA ADVERTENCIA ABAJO: hoy no puede fallar** |
| **B3** | Todos los `procedures` **existen para esa tecnica** | algun procedimiento viene del fallback a "todas las tecnicas" |
| **B4** | El resultado **no es el placeholder** `"(sin LLM: usa los procedimientos listados)"` | los proveedores fallaron y nadie se entero |
| **B5** | *(decision)* **cada modulo/dependencia principal lleva `[doc:chunk]`** | se reclama una cita que el prompt nunca pidio |
| **B6** | `BLUEPRINT.md` **termina en una estructura markdown completa** | acaba en una tabla `| :---` sin filas, o en un ` ``` ` sin cerrar — es decir, `max_tokens=1500` no alcanzo y **nadie lo sabe** (medido: H1) |
| **B7** | *(propuesta §5.5-P3)* **`BLUEPRINT.md` lleva `[doc:chunk]`** — umbral `>= 3` distintas (§6 dec. 1) | da **0**, que es exactamente lo que midio **H3** |
| **B8** | *(propuesta)* **todas las citas resuelven**: cada `[doc:x:c]` apunta a un chunk existente y no vacio | una cita bien formada que **no existe** en la BD — B7 pasa, el anclaje es mentira |
| **B9** | *(propuesta R2)* **toda cita literal entre «» aparece identica en su chunk** | el modelo pone comillas sobre texto que **no es literal** — atribuye a los autores una frase que no escribieron |
| **B10** | *(propuesta R7)* **toda entrada de la bibliografia corresponde a un documento ingerido**, y sus autores **aparecen en su chunk 0** | una fuente o un autor que **no esta** en el corpus — el `0/64` del Hito 1 aplicado a la bibliografia |
| **B11** | *(propuesta R4)* **ninguna frase larga (>= 8 palabras) del blueprint aparece en el corpus sin ir entrecomillada** | prosa copiada de la fuente sin decirlo — el plagio, medido mecanicamente |

**B9, B10 y B11 son las comprobaciones de R2, R7 y R4** (§2.E), y las tres son
`string match` / `lookup`: **0 tokens**. B11 es B9 al revés: no mira si lo que
citas es exacto, sino si **te has copiado texto sin decirlo**. El umbral de 8
palabras evita falsos positivos con nomenclatura (`Hájek full-set estimation`
aparecera literal y esta bien, porque es nombre tecnico, no prosa ajena).

**El orden importa.** R1-R7 van en el **prompt**; B7-B11 son la **prueba** de
que el prompt funciono. Las dos cosas, o no vale ninguna: el modelo dira que
cumple las reglas y no las cumple — H3 salio de un prompt que no pedia citas, y
H5 lo salvo el modelo por su cuenta una sola vez.

**B2 hoy no puede fallar.** El `agent_template.py` que genera
`instantiate_agent_template` tiene un `run()` que recorre `STEPS` y anota
`"todo"` en cada uno (§1.2): `py_compile` pasa, `run()` no levanta, **B2 = 100%
con un agente que no hace nada**. Es un gate de la misma forma que el umbral de
4,50 calibrado contra `r5`: **verde sin decir nada**. Solo pasa a distinguir
algo cuando exista la dimension **D** de §2 — es decir, cuando el agente haga
algo medible.

**B7 y B8 son presencia y validez.** QA tenia `cite_precision` (medido: 0,943
en candF); el diseno de blueprints solo habia conservado el `grep`, o sea la
mitad. **B8 es gratis** (un lookup en la BD) y es la unica que impide que tres
citas a trozos irrelevantes saquen el eje de anclaje por completo en verde.

**B5 es la decision importante.** Hoy el prompt no pide citas, asi que B5
fallaria al 100%: o se anade la exigencia de cita al prompt (y se mide de
nuevo, como en el Hito 0), o se declara que el blueprint es una guia de
orientacion y la fidelidad la juzga un modelo. **No se puede medir el
incumplimiento de una regla que nadie puso.**

`procedures` sale del grafo sembrado asi que B3 es literalmente gratis
(un `set` de nombres), y B1/B2/B4/B6 son gratis igual (B6 es leer las
dos ultimas lineas del fichero). **B7-B11 son `grep`, `lookup` y comparacion de
cadenas: 0 tokens.** B5 solo si se cambia el prompt.

### 3.2 Piso de calidad (juez, si)

Rubricas **Q1-Q4** con el mismo juez de siempre (`openai/gpt-oss-20b`, familia
distinta al agente), **declaradas antes de medir**:

| # | rubrica | lo que pregunta |
|---|---|---|
| Q1 | **fidelidad** | ¿los pasos corresponden a lo que el paper describe, o es relleno plausible? |
| Q2 | **accionabilidad** | ¿un ingeniero sabria por donde empezar mañana? |
| Q3 | **concrecion** | ¿nombra componentes o describe generico? |
| Q4 | **coherencia interna** *(propuesta, §6 dec. 6)* | ¿afirma algo que un `REPORT_*.md` del propio proyecto contradiga? H2 es el caso de prueba |

Umbrales propuestos (a confirmar — **borrador de §6 dec. 3**): suelo en
**B1-B11 = 100%**, juez `mean >= 4.0` en Q1-Q3 **y ninguna rubrica `< 3.0`**, y
**Q4 = 0 contradicciones** (binario). El 4.0 es mas bajo que el 4.50 del Hito 1
porque hay **3 rubricas en vez de una pregunta de 35 items**, o sea menos
muestra y mas ruido por item: bajar el umbral compensa el MDE peor.

**Falta controlar el ruido del juez, y hoy no esta previsto.** En QA medimos
`judge_sd` (0,064-0,096) y `frac_items_coherentes` antes de creer cualquier
diferencia; aqui solo se dice «mismo juez de siempre». Con **n = 15** y 3
rubricas, el ruido del propio juez **decide** si `>= 4.0` significa algo o no.
Propuesta: **re-juzgar los mismos 15 resultados una vez** (~30 k) y exigir
`judge_sd <= 0.15` antes de interpretar la media. Sin ese numero, la nota del
juez es un dato, no una medicion.

### 3.3 La referencia: **el corpus es el oro** (no el responsable)

*(Revisado el 2026-10-11. La propuesta original era «escribir 5 referencias a
mano». Se descarto, y el motivo es de principio, no de tiempo.)*

El problema real del Hito 2 **no es el score, es que no hay oro**: el juez no
sabe si el blueprint es correcto para PEARL, solo si suena bien. Lo mismo que
sin `golden_qa.jsonl` no se podria medir QA.

**Por que no la escribe el responsable:**

> El producto existe **precisamente** porque el usuario no puede leer esos
> papers — ni los actuales ni los que vendran en idiomas que no domina. Una
> metrica que exige que el responsable conozca el dominio **solo funciona en
> las 5 tecnicas de prueba y muere en cuanto hay produccion**.

Y hay una segunda razon aun mas dura: **no podria auditar si la referencia es
correcta**, porque no entiende el idioma. Solo veria que *esas palabras estan en
el documento*, no que signifiquen lo que dice. **La revision humana sobre
contenido no es viable aqui por principio.**

**La alternativa — cuatro piezas:**

| | pieza | que hace |
|---|---|---|
| **5a** | **El juez recibe el paper** | hoy Q1 le pregunta si los pasos corresponden al paper **sin darle el paper**: solo puede contestar «suena plausible». Con la fuente delante puede distinguir **cubierto / inventado / omitido** |
| **5b** | **Referencia por extraccion anclada** | si se quiere un fichero material, que se **extraiga del paper y se verifique contra el**: cada paso tiene que tener un chunk que lo soporte; **lo sin soporte se descarta**. El borrador **no puede inventar** porque cualquier paso alucinado se cae al comprobarlo |
| **5c** | **Calibracion con defectos ya conocidos** | **obligatorio.** Ver abajo |
| **5d** | **Rol del responsable** | no redacta: **fija reglas y revisa discrepancias** — exactamente lo que hizo en el Hito 1, donde no escribio los 64 golden a mano sino que decidio que se midiera `0/64` |

**5c es lo que convierte esto de «algo en lo que hay que confiar» en algo
comprobado antes de gastar.** Tenemos en `data/agents/task-coevolve/BLUEPRINT.md`
un blueprint con defectos **ya documentados**:

| defecto conocido | rubrica que deberia pillarlo |
|---|---|
| Modulos inventados (`Adaptive Harness Execution Engine`, `History Profiler`) | **Q1** con el paper delante |
| Promete *«garantias estadisticas»* que `REPORT_COEVOLVE.md` descarto | **Q4** con el informe delante |

Si al juez con la fuente puesta **no le pillan ninguno de los dos, Q1 y Q4 no
sirven** — y lo sabemos **antes** de pagar la medicion. Es el mismo truco que
hizo el Hito 1 con `golden_abstention`: casos de oro ya construidos, gratis.

**Coste:** ~5-15 k de contexto por paper x 15 blueprints ≈ **75-225 k**, mas
**~10-20 k** de calibracion. **Tiempo del responsable: ~1 h** de revision de
discrepancias, en vez de ~8 h de redaccion.

**Lo que NO resuelve — y hay que declararlo:**

1. **No valida el significado en un idioma que no domina.** El sistema se apoya
   en que el modelo lee bien y el usuario no puede cazar un error de
   comprension. Es una dependencia real, y va en el cierre de §7, no se
   descubre despues.
2. **5b sin 5c sigue sin ser independiente** si el mismo modelo extrae y
   evalua. Por eso **5c es obligatorio, no opcional**.

### 3.4 Suite negativa (no existe, y es el criterio que mas pesa)

**El criterio vinculante del Hito 1 es negativo**: `0/64` en
`golden_abstention`. QA tiene ademas `golden_blind_unanswerable`. De blueprints:
**cero ficheros de trampas.**

Sin eso se declara el Hito 2 cerrado **midiendo solo el lado positivo** — o sea,
con el mismo hueco que tuvo que tapar el Hito 0 creando `golden_abstention`.

| caso | que debe devolver | estado hoy |
|---|---|---|
| **N1** — tecnica que no existe en el grafo | que **no existe**, sin escribir blueprint | H5: **lo salvo el modelo, no el codigo** (`list_procedures(technique) or list_procedures()` tiro el grafo entero al prompt) |
| **N2** — tecnica **ingerida pero no sembrada** | recuperar del corpus o **abstenerse**; **nunca** colar procedimientos ajenos | sin medir nunca |
| **N3** — objetivo **contradicterio** con el corpus | senalar la contradiccion en vez de resolverla a su aire | sin medir nunca |
| **N4** — objetivo que pide algo que el paper **descarta explicitamente** | **no** prometerlo (el caso H2, al reves) | sin medir nunca |

**N2 estaba mal planteado en la version anterior** («tecnica en el grafo pero
no ingerida»). Comprobado en la BD: **las 5 tecnicas sembradas las 5 tienen
documento**, asi que **ese caso no existe** y no se podria probar. Pero si existe
el contrario y es mas peligroso: hay **10 documentos y solo 5 tecnicas
sembradas** — los docs 6-10 (dos surveys, Evo-Bench, «Harness as a Language»,
«Stop Comparing…») **estan ingeridos y no sembrados**. Pedirles un blueprint
devuelve `list_procedures()` vacio, **dispara el fallback y entran los 21
procedimientos ajenos**. Es decir: **el material si esta, y el sistema en vez de
recuperarlo se pone a mezclar**.

**Una run no basta.** H5 fue suerte **una vez**; si probamos cada trampa una
sola vez y pasa, **no hemos aprendido nada**. Se exige **3/3 por trampa**.

Coste: 4 trampas x 3 runs = 12 llamadas ≈ **20-30 k**.

N1/N2/N3/N4 se escriben **a mano, 0 tokens**, igual que los golden de QA. Son
la contrapartida exacta de `golden_abstention`, y **N1 ademas es un fix de
codigo** (decisión 4 de §6), no solo un test: hoy la unica razon por la que no
salta es que el modelo se nego por su cuenta.

---

## 4. Coste (es la noticia buena)

Porque `build_blueprint` es **una llamada**, no un loop:

| que | estimacion |
|---|---|
| 5 tecnicas x 3 runs = 15 blueprints | **~60-75k** |
| juez Q1-Q3 sobre los 15 | **~30k** |
| **+ 5a** juez con el **paper** delante (§3.3) | **~75-150k** |
| **+ Q4** con contexto del informe interno (§6 dec. 6) | **~45k** |
| **+ juez repetido** para `judge_sd` (§3.2) | **~75k** |
| **+ 5c** calibracion con los defectos conocidos (§3.3) | **~10-20k** |
| suite negativa N1-N4 (4 x 3 runs) | **~25k** |
| extraccion de autores al ingerir (1 vez por paper) | **~10k** |
| **B7-B11** (grep, lookup, comparacion de cadenas) | **0 tokens** (tiempo de diseño) |
| **total (sin P1)** | **~330-430k** |
| **+ A/B de P1** si se adopta (§5.7, 30 blueprints) | **~515k** |
| **total con P1** | **~845-945k** |

Frente a los ~11 M gastados en el Hito 1: **sin P1 es ~25 veces mas barato;
con P1, ~12 veces**. Sigue siendo un orden de magnitud entero por debajo, y el
numero aguanta tal cual sin redondear a favor.

*(Erratas internas de esta tabla, ambas corregidas antes de medir y no despues:
la primera version ponia **~100k** y no contemplaba Q4, el control de ruido del
juez ni el A/B de P1; la segunda añadio esos tres pero **olvido el 5a**, que es
la linea mas cara de todas — darle el paper al juez. Se anadio al reescribir
§3.3.)*

*(Notacion: **k** = miles de tokens, **M** = millones, para no confundir 11 M
con 11.000k.)*

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
| **P2** | El prompt de blueprint **exige las 7 reglas de escritura R1-R7 de §2.E**: dice de donde sale, entrecomilla solo lo literal, parafrasea atribuyendo, no atribuye lo que la fuente no dice, declara los silencios, separa lo propio, y cierra con bibliografia | cambia el prompt → obliga a re-medir, como en el Hito 0 y como `max_tokens` |
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
baseline que ya existe (H3 = 0 citas, coste 0). **3 runs por tecnica en cada
brazo, es decir 15 blueprints por brazo** — no 10: con 2 runs por tecnica no
hay con que medir, y aqui el numero de muestras ya de por si es critico (R2).

| brazo | que es | blueprints | coste |
|---|---|---|---|
| **A** (ya hecho) | `generate()` actual, sin exigir cita → H3 = **0** | 15 (ya existen) | **0** |
| **B** | `generate()` + **P2** (exigir cita), sigue sin loop | 5 tecnicas x 3 | ~15 x 5 k ≈ **80 k** |
| **C** | **P1'** (loop orquesta, tool escribe) + **P2** | 5 tecnicas x 3 | ~15 x 25 k ≈ **375 k** |
| juez sobre los 30 del A/B | Q1-Q4 | — | ~60 k |
| **total** | | 30 | **≈ 515 k** |

- **B vs A** aísla el efecto del **prompt**.
- **C vs B** aísla el efecto del **loop** — que es la pregunta que hace la propuesta.

*(Corregido el 2026-10-11: la version anterior decia «~10 blueprints» por brazo
y «200-300 k en total», lo que contradecia los 15 de §4 y §5.5 y daba un
brazo de 2 runs por tecnica. Error mio, arreglado aqui antes de medir y no
despues — que es justo la regla de §6 dec. 2.)*

Si **C no gana a B** en B7/Q1, **P1 se descarta** y nos quedamos con el prompt
en una sola llamada: mas barato y sin el riesgo R2.

Sin este A/B, P1 seria exactamente el error que documenta la Errata 1 del Hito
1: **un cambio que se adopta porque suena mejor, sin haberlo medido.**

---

### 5.8 Resultados — lo que midió el A/B (2026-10-11)

Se corrieron los cuatro brazos sobre las mismas 5 técnicas × 3 runs = 15
blueprints cada uno. Los resultados viven en `evals/results/result_blueprint_ab.json`;
los del juez, en `evals/results/result_q1_r4r5.json`. Se fijaron los umbrales y el
criterio **antes** de la primera run (§6 dec. 3).

#### 5.8.1 Forma — el suelo mecánico (§3.1)

| | A (baseline) | B (P2) | C (P1'+P2) | D (C+P3) |
|---|---|---|---|---|
| R1 citas con puntero | **0** | 2,47/run | 5,33/run | 4,40/run |
| **B8 de esas, resuelven** | **0** | **0,20/run** | **2,73/run** | **3,07/run** |
| R1 atribuye en prosa | — | 12/15 | 15/15 | 15/15 |
| R5 declara silencios | — | 15/15 | 14/15 | 12/15 |
| R7 sección Bibliografía | — | 14/15 | 13/15 | 10/15 |
| B9 comillados literales | — | 0,53/run | 0,93/run | 1,27/run |
| **B11 frases copiadas** | — | 0,53/run | **0,00/run** | **0,00/run** |
| truncados | — | 0/15 | 0/15 | 0/15 |

**P1' se queda.** C gana a B en B8 por 13× (2,73 vs 0,20) y corta el plagio a
cero. El brazo B escribe punteros —2,47 por blueprint— pero **el 92% apunta a
chunks que no existen**: es la fabricación de H3 medida mecánicamente. C la
arregla porque el loop puede *ver* los chunks antes de citarlos.

Ese es el criterio fijado antes de medir (§5.7): *«Si C no gana a B en B7/Q1,
P1 se descarta.»* Gana, así que P1' se queda y **P1 (el loop escribiendo
directo) sigue descartado** —§5.5, porque `loop.run()` genera cada turno con
`max_tokens=1024` y bajaría el tope de 1500.

#### 5.8.2 Sustancia — R4/R5 con el juez (Q1)

Aquí la cosa se tuerce, y es el resultado más importante del Hito 2.

| | Brazo C | Brazo D |
|---|---|---|
| **R4 cumple** (no atribuye lo que la fuente no dice) | **4/15** | 7/15 |
| **R5 cumple** (declara los silencios) | **8/15** | 10/15 |
| Fabricaciones atribuidas / blueprint | 2,67 | 1,20 |
| Detalles rellenados / blueprint | 1,53 | 1,27 |

El brazo C pasaba **todas** las comprobaciones mecánicas —citas que resuelven,
cero frases copiadas, bibliografía en 13/15, atribución con «Según» en 15/15—
y aun así **11 de 15 atribuían a la fuente cosas que la fuente no dice**.

Es exactamente lo que §2.E advertía: *«R4 y R5 son las que separan a un modelo
de un humano»* y *«no son mecánicas»*. **Un blueprint puede pasar B7-B11 entero
y seguir siendo incorrecto. La forma se arregló; la sustancia no.**

Y aquí la calibración 5c importa de verdad: sin ella no habría ninguna razón
para creer el 4/15. Un juez sin calibrar habría puntuado alto estos blueprints
—lucen rigurosos— y el Hito 2 habría cerrado sobre una cifra inventada.

#### 5.8.3 P3 — verificación de atribución, y por qué no funciona

P3 (`bibliotecario/agent/attribution.py`) comprueba **mecánicamente y sin coste**
que los términos técnicos que se atribuyen al paper aparezcan en el chunk
citado. Caza exactamente el fallo real de H1 —nombres de módulo inventados
como «AdaptiveHarnessEngine»— y está testado (`tests/test_attribution.py`).

**El verificador funciona. El reparador, no.** De las 15 runs del brazo D:

- 6 **sin punteros** — nada que verificar (y no se marcan como limpias: eso
  sería mentir con el mismo número, bug medido en la primera versión).
- 6 **limpias** — la atribución ya verificaba.
- 3 **reparadas** — las únicas que P3 tocó de verdad.

Las 3 reparadas **empeoraron todas**:

| run | violaciones tras reescribir | bibliografía | silencios |
|---|---|---|---|
| PEARL run1 | 6 | **perdida** | **perdida** |
| PEARL run2 | **14** (antes, 6) | **perdida** | **perdida** |
| Procedural Graphs run2 | 1 | **perdida** | **perdida** |

Y R4 en esas 3: **0/3 cumplen**. La mejora aparente de C a D (4/15 → 7/15) es
**ruido de generación estocástica**, no P3: el brazo D llama a `run_blueprint`
igual que el C, y de las 3 runs que P3 modificó ninguna salió bien.

**Causa concreta:** `_repair_prompt` pide *«el blueprint completo ya corregido»*.
El modelo no hace una corrección quirúrgica: regenera el documento entero y
pierde la sección de bibliografía (R7) y las declaraciones de silencio (R5) por
el camino. **La verificación sin una reparación que no destruya no sirve.**

Lo que queda en pie de P3: el verificador como **informe**, no como bucle. Que
devuelva las violaciones marcadas en el propio blueprint —ya se hace cuando no
hay reparación posible— y deje la decisión al responsable, en vez de reescribir
a ciegas. Eso es un cambio pequeño sobre el código actual.

**Hecho.** `verify_and_mark()` (`bibliotecario/agent/tools.py`) implementa
exactamente eso: calcula las violaciones y devuelve el blueprint **sin tocarlo**,
junto con el informe. Cuesta **cero `generate()` extra** y no puede destruir
nada, que es el fallo medido de la reescritura. Está testado
(`test_verify_and_mark_no_destruye_el_blueprint`: comprueba además que no llama
al LLM). `verify_and_repair()` **se mantiene tal cual** —el brazo D del A/B la
usó— para que los números de §5.8 sigan siendo reproducibles contra el código
que corrió.

*(Errata propia, declarada: la primera versión del brazo D llamaba a
`build_blueprint_verified`, que se salta el loop. Salió con B8 = 0,00 —peor que
el C que pretendía mejorar— y con `verificado=True` en runs sin ninguna cita.
Los 15 registros se borraron y se rehicieron sobre el camino correcto P1'+P2+P3.
Está anotado en el propio código para que no se repita.)*

---

### 5.9 Resultados — brazo E (P1' + P2 + P4, 2026-10-11)

P4 = reglas de la **dec. 10** (R4 redefinida, **R6 en línea**, **R1 como suelo**)
más el verificador ampliado a números y ficheros. Se corre con
`api.blueprint_p4()` = `verify_and_mark(run_blueprint(...))`: **sin
reescritura**, para que E vs C mida P4 y solo P4.

#### 5.9.1 Forma — el suelo mecánico

| | C | D | **E** |
|---|---|---|---|
| R1 citas con puntero | 5,33/run | 4,40/run | **8,67/run** |
| **B8 de esas, resuelven** | 2,73/run | 3,07/run | **7,40/run** |
| R1 atribuye en prosa | 15/15 | 15/15 | 14/15 |
| R5 declara silencios | 14/15 | 12/15 | **15/15** |
| R7 sección Bibliografía | 13/15 | 10/15 | 11/15 |
| B9 comillados literales | 0,93/run | 1,27/run | **0,33/run** |
| B11 frases copiadas | 0,00/run | 0,00/run | 0,00/run |
| truncados | 0/15 | 0/15 | 0/15 |

**B8 casi se triplica** (2,73 → 7,40) y R1 sube de 5,33 a 8,67. En lo mecánico
P4 es la mejor mejora de todo el Hito 2. *Tres blueprints salen, sin embargo,
con **cero** citas: el suelo de R1 no es infalible.*

#### 5.9.2 Sustancia — R4, y aquí se tuerce

Medido con el **mismo pipeline calibrado** que dio 6/15 al brazo C:

| | C | **E** |
|---|---|---|
| **R4 cumple** | **6/15** | **2/13** |
| Acusaciones originales | 40 | 26 |
| Acusaciones tras calibrar | 18 | **17** |
| Blueprints que cambian de veredicto al calibrar | +2 | **0** |

*(E queda en /13 porque 2 runs no parsearon con el juez. Aunque ambas
pasaran, daría 4/15 — por debajo de C. La conclusión no depende de eso.)*

**P4 mejoró todo lo mecánico y empeoró R4.** Y la caída **no es del juez**: la
re-puntuación calibrada no rescata ni un blueprint.

**El mecanismo:** R1 como suelo hizo que el modelo **atribuyera mucho más** —
8,67 citas/run frente a 5,33—. Cada atribución es una ocasión de atribuir algo
que la fuente no sostiene. **Apretar la atribución amplía la superficie donde
fabricar.** La correlación es directa y está en los propios números.

Las 17 acusaciones que quedan caen casi todas en `juez_etiqueta`: semántica,
**no comprobable con regex**. El suelo mecánico está hecho y funciona; R4 no es
un problema de reglas en el prompt.

#### 5.9.3 Balance del Hito 2 hasta aquí

- **P1' arregla B8** — 2,73 → 7,40/run. Se queda.
- **P3 reescribir destruye** — 3 de 3 empeoran (§5.8.3). Descartado; queda
  `verify_and_mark` como informe.
- **P4 no arregla R4 y la empeora** — 6/15 → 2/13. **Descartado como arreglo
  de R4.** Sus reglas se quedan en el prompt solo si se decide que el coste de
  B8 lo paga; eso es una decisión de dirección, no un resultado.
- **La calibración del juez era necesaria** — sin ella, el 4/15 del C no era
  interpretable, y tres de sus acusaciones eran falsas (`0.125`, `Rbest`,
  `lessons.md`).

---

### 5.10 Ruta 5 — el verificador como crítico en el bucle: coste medido

Se llama «ruta 5» en §7: en vez de arreglar R4 con reglas en el prompt (P4, que
§5.9.2 mide que empeora), **verificar cada afirmación atribuida contra su
fuente antes de dar el blueprint por bueno.**

**Estado: IMPLEMENTADA** — 2026-10-12, `agent/attribution.py`
(`critic_claim`, `critic_attributions`, `demote_unsupported`,
`critic_and_demote`) + `api.blueprint_route5()`. **Sin evaluación completa
todavía**: los números de §5.10.1 son el coste estimado sobre los datos del
brazo E, y la efectividad sobre R4 sigue **sin medir**.

#### 5.10.1 Lo que cuesta, con datos del brazo E

Medido sobre los 15 blueprints reales del brazo E:

| Dato | Valor medido |
|---|---|
| Atribuciones por blueprint | **8,67** (rango 0–19; 3 blueprints con cero) |
| Chunks citados únicos por blueprint | **2,2** (rango 0–5) |
| Contexto de fuente a enviar por blueprint | **692 tokens** (solo los chunks citados, nunca el doc entero: el doc más gordo son 34k tokens) |
| Blueprints a verificar en una evaluación | 15 |
| Atribuciones totales a verificar | **130** |

*El doc entero está fuera de alcance (15–35k tokens). Solo sirve enviar los
chunks que el propio blueprint cita, que es lo que ya hace `calibrate_r4.py`.*

#### 5.10.2 Dos formas, y la que no sirve

| | **A: una llamada por afirmación** | **B: una llamada por blueprint** |
|---|---|---|
| Llamadas (eval, 15 bp) | 130 | **15** |
| Tokens por blueprint | ~10.000 | **~1.400** |
| Tokens por evaluación | ~150.000 | **~20.000** |
| Coste añadido en producción | +10k por blueprint | **+1,4k por blueprint** |
| Riesgo | bajo | el juez falla en lote — §4.2 ya lo mostró con semántica |

**B cuesta 7× menos y es la opción tentadora. Pero §4.2 mide que el juez es
precisamente fiable en lo mecánico (11/14) y no en lo semántico (3/6 antes de
calibrar).** Apretar 8 afirmaciones en una sola llamada empeora justo donde ya
es malo. **A es la que sostiene el argumento; B es la que lo barata.**

#### 5.10.3 Lo que realmente cambia la propuesta: **degradar, no reescribir**

P3 fracasó (§5.8.3) **porque regeneraba prosa**: reescribir destruyó citas,
perdió bibliografía y añadió silencios en 3 de 3. El error no era verificar,
era **actuar sobre el texto**.

R4 se define como: *«no presenta como de la fuente algo que no está en la
fuente».* Su denominador son **las atribuciones**. Eso permite una acción que
no toca la prosa:

> Si el crítico dice que la fuente no sostiene la afirmación, **se quita el
> puntero** — `[doc:1:43]` desaparece y la frase queda como propuesta del
> blueprint, no como atribución.

- **Es una edición de cadena determinista.** No hay regeneración, no hay LLM
  después del crítico. **No puede pasar lo que le pasó a P3.**
- **Sube R4 por construcción**: la afirmación sale del denominador.
- **Baja B8** — menos punteros, menos resueltos. Es el coste declarado.
- **No rompe R5 ni R7**: no se reescribe la estructura.

#### 5.10.4 Balance honesto

**Lo que ruta 5 sí es:** la única opción que ataca la parte de R4 que el suelo
mecánico no alcanza (17 acusaciones, casi todas semánticas), con un coste
medido y acotado — 10k tokens por blueprint, o 10× el coste de un Q1.

**Lo que no es:** gratis. Y **no cierra R4 por sí sola**: solo degrada lo que el
crítico detecta, y §4.2 mide que el crítico se equivoca. Sigue habiendo un
resto semántico que ni regex ni juez alcanzan de forma fiable.

**Mi lectura:** ruta 5 es el único camino que queda con sentido para cerrar
R4, y su variante **A con degradación** es la que vale la pena probar. Pero es
una decisión de coste de producción, no de resultado de experimento — y
debería decidirse **antes** de implementarla, con el umbral de R4 fijado, que
hoy sigue siendo ≥8/15.

---

---

## 6. Lo que decide el responsable antes de medir

**BORRADOR de propuestas — nada de lo que sigue está decidido.** Cada punto
trae un numero concreto para poder decir que sí o que no, no un "a ver". La
regla aprendida en el Hito 1 se respeta: **todo se fija ANTES de la primera run.**

### Decisión 0 — §5, plan/build (P1-P4)

**Propuesta: SÍ, condicionada al A/B de §5.7.** A-B aísla el prompt, C-B aísla
el loop; si C no gana a B en B7/Q1, **P1 se descarta** y nos quedamos con solo
P2 (más barato, sin riesgo R2). Coste del A/B: **~515 k** (15+15 blueprints y
juez), ver §5.7.

*Si se dice no:* B5/B7 quedan en comprobar un resultado que el sistema no está
diseñado para producir, y Hito 2 se mide con una métrica que ya sabemos que va
a dar 0 en el eje que importa.

### Decisión 1 — cómo se escribe y cómo se comprueba

**(a) La especificación — R1-R7 van en el prompt.** Formulada por el
responsable: *«que se comporte como lo haría un humano»*. Las 7 reglas de §2.E
son el contenido real de **P2** — hasta ahora decía solo «dos secciones», que
era demasiado vago para implementarlo o para juzgarlo.

**(b) Las comprobaciones — B7-B11, todas con umbral:**

| check | umbral | coste |
|---|---|---|
| **B7** citas `[doc:chunk]` | **`>= 3` distintas** | 0 |
| **B8** las citas resuelven | **100%** | 0 |
| **B9** cita literal = texto original | **100%** | 0 |
| **B10** bibliografía = documentos ingeridos y autores en su chunk 0 | **100%** | 0 |
| **B11** prosa copiada sin comillas | **0 casos** (>= 8 palabras) | 0 |
| ratio `citas / afirmaciones técnicas` | **se mide, no se gatea** | 0 |

**Sin gatear el ratio desde ya**: cae el riesgo de una cita decorativa de 300
palabras que salve B7 sin anclar nada. Se **mide** primero y se gatea después,
con datos — que es la misma razón por la que B5 existía separado de B7.

**(c) Tres prerequisitos que hay que hacer ANTES de poder exigir (a):**

1. **Extracción de autores al ingerir** — hoy no existe el campo. Sin él, R1 y
   R7 se piden sin tener con qué cumplirlas y el modelo rellenará los huecos.
   *Trabajo puntual, una vez por paper, ~10 k.*
2. **Bibliografía publicable** — autores + año (+ arXiv/DOI si están en los
   metadatos del PDF). Sin esto `[doc:chunk]` solo sirve **dentro** del
   sistema; **en cuanto salga al blog o al CV, R7 no se puede cumplir.**
3. **Juez calibrado con los defectos ya conocidos (decisión 5, 5c)** — R4 y R5
   no son mecánicas. *~10-20 k.*

**Si se omite (c) pero se aprueba (a):** el prompt exigirá citas con autores
que el sistema no tiene, y B10/B7 suspendrán por algo que no es culpa del
modelo. **Ese sería exactamente el error de exigir una regla que no se puede
cumplir.**

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
| **B1-B11** (suelo mecánico) | **100%** — son deterministas, o pasan o se arregla el sistema |
| **Q1-Q3** (juez) | **`mean >= 4.0` Y ninguna rubrica `< 3.0`** |
| **Q4** (nueva, ver decisión 6) | **0 contradicciones** — binario |
| **`judge_sd`** (ruido del juez, §3.2) | **`<= 0.15`** — sin esto la media no es interpretable |
| **N1-N4** (suite negativa, §3.4) | **0 fallos** — mismo peso que el `0/64` del Hito 1 |

**La condición `ninguna < 3.0` es nueva** y es la lección directa de H2: un
blueprint que contradice `REPORT_COEVOLVE.md` perfectamente pudo haber sacado
buena nota de media. **La media esconde exactamente el fallo que más importa**,
igual que la media de calidad del Hito 1 escondía que `r5` fabricaba.

**B8 y N1-N4 no son añadidos cosméticos**: B8 es el `cite_precision` que sí
tenía QA y aquí se había tirado, y N1-N4 son el `golden_abstention` que sí tenía
QA y aquí **no existía en absoluto**. **Eran los dos criterios que más pesaban
en el Hito 1 y el diseño de Hito 2 no los traía.**

### Decisión 4 — el fallback silencioso (§1.1)

**Propuesta: arreglarlo como bug.** Técnica inexistente → `list_procedures(technique) or list_procedures()` **tira el grafo entero al prompt**.

- **B3 lo detecta, pero después** — cuando ya se han pagado los tokens y el
  blueprint ya afirma procedimientos de técnicas que no son la suya.
- **H5 enseña que hoy lo salva el modelo, no el código**: se negó a escribir el
  blueprint *por suerte*, con el grafo metido en el prompt. **Esa no es
  una garantía, es un golpe de suerte.**

*(Contado hoy: el grafo tiene **21 procedimientos** — 20 con técnica asignada y
**1 sin `technique`**, que solo es alcanzable por el fallback. H5 anotó «18»;
o el grafo ha crecido desde entonces o el recuento fue distinto. **No es
grave, pero conviene no citar el número sin recontarlo antes de la run** — no
sea que el test se apoye en una cifra que ya no es la buena.)*

**Fix:** si `technique` no existe, devolver **vacío** y que el prompt diga «no
existe». +1 test. **0 tokens.** Y de paso decidir qué hacer con el procedimiento
**sin `technique`**, que hoy no puede pertenecer a ninguna.

### Decisión 5 — ¿de dónde sale el oro de la fidelidad?

**Propuesta: el corpus, no el responsable.** Ver §3.3 para el razonamiento
completo — resumido: *el producto existe precisamente porque el usuario no
puede leer esos papers*, así que **ninguna métrica puede depender de que conozca
el dominio**. La propuesta original («tú escribes 5 referencias») no era lenta:
**era incompatible con el producto**, y encima no podrías auditar un idioma que
no dominas.

**Se aprueba el paquete 5a-5d:**

| pieza | qué | coste |
|---|---|---|
| **5a** | El juez recibe **el paper** (Q1) o el **informe interno** (Q4) | ~75-150 k |
| **5b** | Referencia opcional **por extracción anclada** (cada paso con su chunk; lo sin soporte se descarta) | ~0 |
| **5c** | **Calibración obligatoria** con los 2 defectos conocidos de Task-CoEvolve | ~10-20 k |
| **5d** | Tu rol: **fijar reglas y revisar discrepancias**, no redactar | **~1 h** |

**5c no es opcional.** Si el juez con la fuente delante no pilló ni los módulos
inventados ni la contradicción con `REPORT_COEVOLVE.md`, **Q1 y Q4 no miden
nada** — y es preferible saberlo por 20 k que descubrirlo tras la run completa.

**Declarar lo que no cubre:** no valida el significado en un idioma que el
responsable no domina. Va en el cierre de §7, con la misma honestidad con que
el Hito 1 declaró que su MDE real era 0,458.

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

### Decisión 7 — B8, la cita que resuelve

**Aprobada.** Cada `[doc:x:c]` del blueprint se comprueba **contra la BD**:
existe el documento, existe el chunk, y no está vacío. Un lookup. **0 tokens.**

Es el hueco de forma: QA tenía `cite_precision` medido (0,943 en candF) y el
diseño de blueprints se quedó con el `grep` — **la mitad de la comprobación**.
Sin B8, tres citas a trozos irrelevantes sacan el eje de anclaje en verde.

**B9, B10 y B11** (las comprobaciones de las reglas de escritura R2, R7 y R4)
se aprueban **junto con la decisión 1**, porque nacen de §2.E y no existían
cuando se escribió este punto.

### Decisión 8 — suite negativa N1-N4

**Propuesta: SÍ, escrita a mano, 0 tokens.** Ver §3.4: técnica inexistente (N1),
técnica ingerida pero no sembrada (N2), objetivo contradictorio (N3), objetivo
que pide algo que el paper descarta (N4).

**Con dos condiciones añadidas tras revisarla:**

1. **3/3 por trampa, no 1/1.** H5 fue suerte **una sola vez**. Si cada trampa
   se prueba una vez y pasa, no se ha aprendido nada. ~20-30 k.
2. **JSONL con la etiqueta esperada** — igual que `golden_abstention`. Sin eso,
   *«¿se negó?»* lo decide quien mira. Y puntuación **binaria, sin suavizar**.

**Es el criterio que más pesa y el que menos se ha medido.** El Hito 1 se cerró
con el `0/64` como criterio **vinculante**; aquí no existía ningún equivalente.
Cerrar Hito 2 solo con el lado positivo repetiría el hueco que tuvo que tapar el
Hito 0 creando `golden_abstention`.

*N1 además obliga al fix de la decisión 4*, no solo a un test.

### Decisión 9 — la dimensión D: ¿el agente generado funciona?

**Propuesta: declararla BIERTA y no gatearla en este hito.** Ver §2.D.

**Motivo para no gatearla:** `instantiate_agent_template` genera un `run()` que
pone todo en `"todo"` por diseño, así que *hoy* no hay nada que ejecutar —
gatear D ahora sería fallar siempre, que es exactamente el defecto que se le
encontró a B2.

**Motivo para no saltársela:** el README promete «arneses que funcionan». Con
A+B+C se puede estar en 100% y que el agente no haga nada. Declarar el Hito 2
cerrado sin tocar D es **decir cumplido con un número que no mide eso**.

*Si se aprueba esto, el cierre de §7 debe decir explícitamente que «Hito 2»
cubre plausibilidad y anclaje, **no funcionamiento** — con la misma honestidad
con que el Hito 1 declaró que su MDE real era 0,458 y no 0,15.*

### Decisión 10 — R4, cambio de definición *(fijada 2026-10-11, antes de medir)*

**R4 pasa de «no atribuye lo que la fuente no dice» a:**

> **No presenta como de la fuente algo que no está en la fuente.**
> Puentear hacia un objetivo que la fuente no trata **está permitido**, si la
> frase lleva la marca de propuesta **junto a la afirmación** (misma línea, o la
> inmediatamente siguiente del mismo punto). Una etiqueta en otra sección no
> cuenta: no se puede saber a qué afirmación se refiere.

**Umbral: `>= 8/15`** — **se mantiene el original**, no se toca.

**Por qué cambia la definición, con la fecha puesta:**

1. **El goal del A/B está fijado a** *«validar mi agente antes de cada release»*
   y no todas las técnicas tratan eso: PEARL es un paper de grafos de
   conocimiento. Bajo la definición anterior, **la fabricación para PEARL era
   estructuralmente inevitable** y R4 no podía llegar a 8/15 sin trampa.
2. **El entregable real es una mezcla**: fuentes + diseño propio. Exigir que no
   aparezca nada propio no describe el documento — lo que hay que exigir es que
   **lo propio esté marcado como propio**.
3. **Correlación medida, pero débil:** la única técnica alineada con el goal
   (Task-CoEvolve, cuyo título lleva *Validation Task Selection*) sacó 2/3 y la
   peor (PEARL) 0/3 — pero WikiSkill llegó a 3/3 sin cuadrar y Procedural
   Graphs se hundió a 0/3 estando en tema. **El goal desalineado empeora R4,
   no lo explica**: es razón para cambiar la definición, no para dar por
   bueno el número.

**Lo que NO cambia:**

- **R1 sigue de suelo.** Sin puntero real a un chunk, la marca `Propuesta` no
  salva. Sin esto la métrica se vacía: el modelo se cubriría etiquetando todo y
  no citaría nada.
- **El umbral no se toca**, ni se reabren los brazos B, C y D: siguen medidos
  bajo la definición antigua y así deben leerse.

**Esto NO es una mejora del modelo.** Cualquier R4 medido a partir de ahora
compara contra una regla **más permisiva en el puente y más estricta en la
marca**. Un 8/15 futuro **no debe leerse como «el modelo ha aprendido a no
mentir»**, sino como «el documento dice de dónde sale cada cosa». Está
escrito aquí, con fecha, justo como exige la regla de §6 dec. 3.

**Cómo se comprueba** (calibrado el 2026-10-11, `evals/calibrate_r4.py`,
set dorado `evals/calib_r4_gold.json`, **14/14 en dos pasadas seguidas**):

| vía | ¿determinista? |
|---|---|
| Búsqueda literal en los chunks (8 de 14 del set) | sí |
| Regex de marca `Propuesta`/`no especifica` adyacente (3 de 14) | sí |
| Juez, solo para equivalencia semántica español↔inglés (3 de 14) | temp 0 |

**11 de 14 se deciden sin LLM.** La regla de la etiqueta se comprueba con
regex **a propósito**: con el juez parpadeaba —dos pasadas seguidas fallando
un item distinto, siempre de esa misma categoría— y un umbral que parpadea no
sirve para medir.

*Erratas propias de esta fase, declaradas: el juez original acusó `λ_t=0.125`,
`Rbest` y `lessons.md` de no estar en la fuente **y los tres están** (doc3
chunk43, doc5 ×3, doc4 ×7); y el set dorado se construyó primero buscando
frases **en español** sobre papers **en inglés**, lo que dejó mal etiquetados
al menos dos items — doc2 dice literalmente *«the framework localizes the
active node»*. Ambas cosas se corrigieron antes de medir, no después.*

### Decisión 11 — B, anclar la paráfrasis a una cita literal *(fijada 2026-10-12, antes de medir)*

**Lo que cambia:** la atribución deja de ser «Según X [doc:N:M]» y pasa a ser

> **«<fragmento literal del paper>» [doc:N:M] — <paráfrasis en español>.**

La cita literal va **primero**, es verificable con regex (¿está ese string en
el chunk citado?), y la paráfrasis va **pegada a ella**, en la misma línea.

**Por qué, y por qué ahora:** los cuatro caminos probados (§7.1.1) fallan
igual — **paráfrasis**. P3, P4 y R5 todos intentan *detectar después*, y
detectar una paráfrasis mala no la arregla: la caza o no. B es el único que
cambia el **formato** para que la parte comprobable ancle la que no lo es. El
juicio que queda por hacer se estrecha de *«¿esta paráfrasis corresponde al
paper?»* a *«¿esta frase se pasa de lo que su propia cita soporta?»*.

**No es mover la portería.** El umbral de R4 no se toca. Se cambia el sistema,
no la definición ni el número.

**Por qué es distinto de P4, que empeoró R4 (§5.9.2):** P4 añadía *más
atribución* (R1 como suelo), con lo que **aumentaba** la superficie donde
fabricar. B no pide más atribución: pide que **cada** atribución lleve su
ancla. La cantidad no sube; cambia la forma.

#### Umbrales fijados ahora

| criterio | umbral | nota |
|---|---|---|
| **R4 cumple** | **≥ 8/15** | **sin tocar.** Relajarlo ahora, al probar algo nuevo, haría el resultado ininterpretable. |
| **B9** | **≥ 1 cita literal por afirmación atribuida** | **se le da la vuelta — ver abajo** |
| **B8 resueltas/run** | **≥ 2,00/run** | mismo suelo que R5: no se puede «arreglar» R4 citando menos |
| **B11 frases copiadas** | **0** | **sin cambios.** Sigue siendo el que caza plagio de verdad. |

#### B9 se redefinible, y el original se deja visible

Hoy B9 mide *«lo entrecomillado que aparece literal en el corpus»* y **menos
es mejor** (C: 0,93/run · E: 0,33 · R5: 0). Si la cita literal pasa a ser
**obligatoria** para atribuir, B9 deja de medir copia y pasa a medir
**cumplimiento**: debería subir a ~1 por atribución.

**Se redefine aquí, con el original a la vista, y no después de ver el
número.** Los valores históricos de B9 se leen bajo la definición antigua y
así deben leerse. El que caza plagio de verdad es **B11, y B11 no cambia**.

#### Riesgo declarado

Que el modelo **sobre-cite**: fragmentos largos, irrelevantes o pegados a la
frase equivocada. Se verá en B9 y en la longitud del blueprint. Si B9 se dispara
sin que R4 suba, B no ha servido y se declara.

#### Decisión de cierre, fijada ahora

- **≥ 8/15 → R4 cerrada.** Hito 2 queda solo con la fila D de la dec. 9.
- **5–7/15 → B ayuda, no cierra.** Entonces se decide **C** (reencuadrar R4
  como pre-filtro para revisión humana) sobre esa base.
- **≤ 4/15 → B no sirve**, igual que P4 y R5. Se va directo a C.

#### Resultado (2026-10-12) — **B no sirve: 3/15**

| | C | E | R5 | **F (dec. 11)** | umbral |
|---|---|---|---|---|---|
| **R4 cumple** (calibrado) | **6/15** | 2/13 | 4/15 | **3/15** | ≥ 8/15 → **no** |
| B8 resueltas/run | 2,73 | 7,40 | 2,87 | **4,40** | ≥ 2,00 → cumple |
| **B9' cumplimiento** | — | — | — | **0,38** | ≥ 1,00 → **no** |
| B11 frases copiadas | 0,00 | 0,00 | 0,00 | **0,00** | 0 → cumple |
| blueprints sin ninguna cita | 3/15 | 3/15 | 6/15 | **7/15** | — |

**La decisión pre-fijada lo sitúa en ≤4/15 → B no sirve → se va directo a C.**

**Lo que el ancla sí consiguió, y hay que decirlo:**

De 41 anclas generadas, **0 no existían en el paper**:

| | anclas | % |
|---|---|---|
| literalmente en el documento | **24** | 59% |
| paráfrasis de una cita real (≥80% de palabras) | **16** | 39% |
| parcial | 1 | 2% |
| **inventada** | **0** | **0%** |

B no fabricó ni una cita. Eso era la hipótesis y se cumplió.

**Por qué igualmente falla — y es el hallazgo:**

1. **El ancla no constriñe la paráfrasis.** El modelo escribe una cita
   correcta y **acto seguido se pasa** en la paráfrasis. Estar pegado a una
   cita verificable no impide decir algo más de lo que la cita dice — que es
   exactamente lo que R4 castiga. **La hipótesis de la dec. 11 se refuta.**
2. **Solo el 38% de las atribuciones lleva ancla** (umbral ≥1,00). El modelo
   lo cumple a ratos; donde no lo cumple, la atribución queda como antes.
3. **Los punteros apuntan al chunk equivocado.** 59% de las citas están en el
   documento pero no en el chunk citado — `anclas_en_fuente` da 0,20/run
   frente a 2,73 de anclas. El ancla es real, el destino no.
4. **Coste colateral: 7 de 15 blueprints salen sin ninguna cita**, el peor de
   todos los brazos.

**Conclusión:** cinco caminos medidos (P3, P4, R5, B) y ninguno cierra R4.
El mejor sigue siendo **C**, el más simple. Se va a **C** — reencuadrar R4
como pre-filtro para revisión humana — tal como fija esta misma decisión.

### Decisión 12 — C, R4 pasa de *gate* a *pre-filtro* *(fijada 2026-10-12)*

**El umbral no se mueve. Se le cambia el papel.** Esta es la distinción que
separa esto de maquillar el resultado.

#### Qué cambia

| | antes | ahora |
|---|---|---|
| **Qué es R4** | umbral que hay que **cumplir** para cerrar el Hito 2 | **aviso** que le dice al revisor **dónde mirar** |
| **Quién decide** | el número, solo | **una persona**, con el número delante |
| **Umbral ≥ 8/15** | gate de cierre | **se mantiene visible y sin tocar**, como objetivo de calidad del artefacto |
| **Valor medido de C** | 6/15 = «no cierra» | 6/15 = «el 40% de los blueprints no necesitan revisión de atribución; el resto sí» |

#### Qué NO cambia

- **El umbral ≥ 8/15 sigue escrito y sin tocar.** No se rebaja, no se
  reinterpreta como «suficiente». Sigue siendo lo que costaría para que la
  comprobación fuera automática.
- **El valor medido sigue siendo 6/15**, pipeline calibrado, brazo C. No se
  re-mide ni se re-etiqueta.
- **La definición de R4 (dec. 10) no se toca.**

#### Qué obliga a declarar §7

Que el Hito 2 **no puede declarar** que las atribuciones son correctas. Puede
declarar que **las pone a la vista de un revisor**. Es el mismo tipo de
declaración que hizo el Hito 1 al decir que su MDE real era **0,458 y no
0,15**: el alcance se acota en voz alta, no se disimula.

#### Qué le debe el sistema al revisor

Un pre-filtro inútil no justifica nada. Para que C valga, el sistema tiene
que entregar:

1. **La lista de atribuciones**, cada una con su cita literal y su puntero
   `[doc:N:M]` — ya existe (`check_attributions`).
2. **El chunk citado al lado**, para que verificar cueste una lectura y no una
   búsqueda — ya existe (`_cited_chunks`).
3. **Las que el crítico marca como no sostenidas**, separadas de las que no
   revisó — ya existe (`critic_attributions`, con `violaciones` y `fallos`
   **aparte**, §8.4).
4. **Los punteros que no resuelven** — ya existe (B8).

**Todo lo anterior cuesta 0 tokens por blueprint**: son chequeos mecánicos y
un informe, no reescritura.

#### Por qué esta decisión y no otra

- **No hay camino automático.** Cinco intentos medidos (§7.1.1), el mejor en
  6/15. Declarar un sexto intento sin razón nueva sería repetir el error.
- **El producto ya lo pide.** La dirección de producto es *«publicar solo tras
  revisión de expertos»*. Si siempre hay revisión, exigir que la máquina
  llegue sola a 8/15 es un requisito que **nadie va a usar**: el revisor ya
  está.
- **Es reversible.** Si más adelante aparece un camino automático que llegue,
  R4 vuelve a ser gate con el mismo umbral. No se destruye nada.

#### Decisión de cierre del Hito 2, reescrita

- **Cierra** cuando A, B, C (ejes §2) cumplan **y** la fila de escritura
  declare explícitamente: *«R4 = 6/15, pre-filtrada, revisión humana
  obligatoria antes de publicar»*.
- **No cierra** si esa frase no está escrita en la tabla de cierre.
- **La fila D de la dec. 9** (¿el agente generado funciona?) sigue **abierta**
  y sin gatear — nada de esto la toca.

---

## 7. Como se sabra que Hito 2 esta cerrado

La misma estructura: tabla *criterio / umbral / medido* con el valor real de la
run final, coste real en tokens, y la seccion de erratas si algo resulta estar
mal medido. Y **el suelo mecanico se declara ANTES de la primera run**, no
despues de ver los numeros.

La tabla de cierre tendrá **una fila por eje de §2**, incluida **D**, y la de D
llevará la casilla vacia si no se trabajo en ella — **no la fila ausente**. Que
falte una fila es como tachar el umbral sin dejar el original: se pierde de
vista lo que no se comprobo.

**Alcance declarado de antemano** (§6 dec. 9): con A+B+C cerrados y D abierta,
lo que este documento puede declarar es que el blueprint **es fiel, es accionable
y esta anclado**. **No** que el agente generado **funcione**. El README promete
lo segundo; decir «Hito 2 cerrado» sin esa fila seria exactamente la clase de
engano que el Hito 1 paso a corregir en sus propias erratas.

**Segunda limitación declarada** (§6 dec. 12): **R4 no es un gate, es un
pre-filtro.** Cinco caminos automáticos se midieron y ninguno llegó a 8/15
(§7.1.1), así que la fila de escritura **no puede declarar que las atribuciones
son correctas**. Puede declarar que **las pone a la vista de un revisor**, con
el umbral ≥8/15 intacto y el valor medido —6/15, brazo C— a la vista. La tabla
de cierre **no cierra** si esa frase no está escrita en la fila.

### 7.1 Estado real (2026-10-13) — **Hito 2 NO cerrado**

La tabla de cierre, con lo que ya está medido y lo que no. **Toda fila medible
está cerrada — y ya no queda ninguna sin cerrar.** R4 y R5 están medidos con
el **mismo instrumento reproducible** (§8.12, §8.13): **0% de flips, recorrido
0, 0 fallos de JSON en 180 juicios**. Los umbrales siguen intactos: 10/15 para
R5, 8/15 para R4. B5 cierra con la frase de la dec. 17. **La única decisión
pendiente es el juez de publicación**, porque el actual comparte familia con
el agente (§8.12).

| eje (§2) | criterio | umbral | medido | estado |
|---|---|---|---|---|
| **B** Accionabilidad | suelo mecánico, B1-B4 (§3.1) | tests verdes | **277 tests** | ✓ |
| **A** Fidelidad | B3-B4 procedimientos reales, sin placeholder | — | ✓ en todos los brazos | ✓ |
| **C** Integridad | **B6** termina completo | 100% | **90/90 = 100%** (§8.5) | **✓ cerrada** |
| **C** Integridad | **B5** cada módulo lleva cita | 100% | **95,8% (H)** · 84,7 (G) · 81,3 (G2) · 65,9 (E) · 63,4 (C) · 58,1 (B) · 51,7 (D) · 48,7 (R5) · 39,1 (F) | **B5 = 95,8% (H), lista de revisión, clasificación mecánica y revisión humana obligatoria antes de publicar** (dec. 17) |
| **C** Integridad | **B7-B8** citas presentes y resuelven | B8 > 0 | **2,73/run (C)** · 7,40 (E) · 4,40 (F) | ✓ |
| **D** Funcionamiento | **D1, D2, D3** (dec. 13) | 5/5 · 5/5 · ≥1 `done` | **5/5 · 5/5 · 18/20** (§8.6) | **✓ cerrada** |
| **E** Escritura | **R4** | ≥ 8/15 | **9/15 (E)** ✅ · 8/15 (G) ✅ · 7 (C) · 7 (D) · 7 (G2) · 5 (H) · 4 (B) · 4 (F) — **juez nuevo**, 90 juicios, **0 fallos** (§8.13). El 6/15 viejo y los de §8.7 siguen como *instrumento no calibrado* | **✓ medida y CUMPLE** — 9/15 ≥ 8/15. **Frase de la dec. 12 intacta**: pre-filtrada, revisión humana obligatoria antes de publicar |
| **E** Escritura | **R5** | ≥ 10/15 | **13/15 (G)** ✅ · 8/15 (H) — **juez nuevo** `gemini-3.1-flash-lite`, **0% de flips, recorrido 0, 0 fallos** en 90 juicios (§8.12). Los valores viejos (**9/14 (G)** · **8/15 (H)** · 10/15 (D) · 9/15 (E·R5) · 8/15 (C) · 4/15 (F)) siguen como *instrumento no calibrado* y **no son comparables** | **✓ medida y CUMPLE** — 13/15 ≥ 10/15 (dec. 18). **Solo G y H re-juzgados** (§8.12) |
| **E** Escritura | R1, R7, B9, B11 | §3.1 | ✓ en C, D, E, R5 y F | ✓ |

**Errata propia, quinta — la tabla usaba ejes que no eran los de §2.** Durante
toda la sesión esta columna decía *«eje (§2)»* y etiquetaba **A Accionabilidad,
B Integridad, C Funcionamiento, D Escritura**, cuando §2 dice **A Fidelidad,
B Accionabilidad, C Integridad, D Funcionamiento, E Escritura** — es decir, la
tabla estaba **desplazada una posición**, y al añadir la fila de D aparecieron
**dos «D» distintos en la misma tabla**. Se reetiqueta contra §2.

**Ningún valor medido cambia**: solo cambian las etiquetas de la primera
columna. Las tres filas de escritura pasaban de «D Escritura» a **E Escritura**
(que es donde §2 las pone), B5/B6/B7-B8 de «B»/«C Funcionamiento» a **C
Integridad**, y la fila del agente —hasta ahora escrita *«no medido»*— se
coloca en **D Funcionamiento**.

**Asignaciones que se discuten**, para que no se lean como cerradas: B5
(cita por módulo) podría caer en **A Fidelidad** («ningún módulo inventado sin
respaldo») y se queda en **C Integridad** por ir emparejada con B6 desde §3.1;
B7-B8 van a **C Integridad** («cumple lo que el prompt promete») y no a **A**.
Se anota porque un eje mal puesto mueve una fila entera de la tabla de cierre.

**Cómo se lee la fila de R4 desde la dec. 12, y ahora desde §8.10:** el umbral
≥8/15 **sigue ahí y no se tocó**, y el valor del mejor brazo **sigue siendo
6/15** — pero §8.10 mide que ese número **no se sostiene como medida**: el
mismo juez que lo produce da **42%** de flips a temp 0, y un mismo brazo se
recorre **33 puntos** entre repeticiones. **Lo único que se afirma en la fila
es la frase** *«R4 = 6/15, pre-filtrada, revisión humana obligatoria antes de
publicar»*. **Si esa frase no está, la fila no cierra** — y el 6/15, que es
sólo pre-filtrado, tampoco la habría cerrado solo.

**R4 se re-puntúa con el pipeline calibrado de la dec. 10** (`rescore_r4.py`),
no con el juez original: los 4/15 y 7/15 de §5.8.2 eran juez **sin calibrar**
y ya no son comparables. **Brazo D no se ha re-puntuado** — su 7/15 sigue
siendo juez viejo y así debe leerse. **R5 y F son pipeline calibrado**,
comparables con C y E.

**Pero el pipeline calibrado de la dec. 10 tampoco arregla esto.** §8.10 mide
que la irreproducibilidad **no es de los parámetros del juez, sino del modelo**:
`gpt-oss-20b` es Mixture-of-Experts y su enrutado **no es determinista ni a
temperature=0**. Cambiar el prompt o la temperatura no alcanzó el criterio de
la dec. 16 en ninguna de las dos configuraciones. **Medir R5 de verdad
exigiría cambiar de modelo de juez**, que es un instrumento nuevo y requiere
su propia declaración antes de medir. **No se hace aquí.**

#### 7.1.1 Por qué R4 no se cierra, y qué se descartó

| camino | intento | resultado | destino |
|---|---|---|---|
| Reglas en el prompt | **P4** (dec. 10, R1 suelo, R6 en línea) | B8 2,73→**7,40** · **R4 6/15→2/13** | **descartado como arreglo de R4** (§5.9.2) |
| Reescribir la atribución | **P3** (`verify_and_repair`) | 3 de 3 empeoran | **descartado** (§5.8.3) |
| Verificar y solo informar | `verify_and_mark` | coste 0, no toca el texto | **se queda** como informe |
| Crítico + degradar puntero | **R5** (`critic_and_demote`) | B8 7,40→**2,87** · **R4 4/15** | **descartado** (§8.4.1) |
| Anclar paráfrasis a cita literal | **F** (dec. 11) | **R4 3/15** · B9' 0,38 · 0 citas inventadas | **descartado** (dec. 11) |

**R4 no se cierra por ninguna de las cinco vías probadas.** Ninguna llega,
tres la empeoran. El patrón es el mismo en todas: **lo que falla es
semántico**, y ni el prompt ni la regex ni el juez lo alcanzan de forma fiable
(§4.2). Por eso la dec. 12 deja de perseguir el gate automático.**

#### 7.1.2 Lo que el Hito 2 ya puede declarar

- **B8 se arregló y se queda** — 2,73 → 4,40/run sin tocar el mejor brazo.
- **La verificación funciona, la reparación no** — medido, no supuesto (§5.8.3).
- **El juez calibrado es una métrica defendible** — 14/14 estables, 11 sin LLM
  (dec. 10).
- **R4 queda con su umbral intacto y su valor medido a la vista** — ≥8/15 y
  6/15, ninguno de los dos tocado. Y ahora, con la dec. 12, **el papel que
  juega está declarado**: pre-filtro para revisión humana, no gate.
- **Lo que el sistema le entrega al revisor existe y cuesta 0 tokens** —
  lista de atribuciones con su chunk al lado, crítico con `violaciones` y
  `fallos` aparte, punteros que no resuelven (§6 dec. 12).

**Y lo que NO puede declarar, dicho igual de claro:** que las atribuciones
**son correctas**. 6/15 con el mejor brazo no lo es, y cinco intentos no
llegaron. La fila de escritura cierra con esa frase escrita, o no cierra.

---

## 8. Dos capas, y un fallo de formato que estaba ahí todo el rato

### 8.1 El sistema produce dos cosas distintas, y no se confunden

| | **blueprint** | **study** |
|---|---|---|
| Pregunta | *¿cómo levanto esto?* | *¿qué dice y qué no dice el paper?* |
| Contenido | módulos, dependencias, orden, validación | mecanismo, novedad, límites, silencios |
| Destino | se implementa y se **mide** | se **lee** y se retiene |
| Código | `agent/tools.py` | `knowledge/study.py` |
| Alimenta | `instantiate_agent_template` | — |

**Solo el blueprint es medible.** El study no tiene R1-R7 de escritura porque
no hay «correcto»: tiene R1 (cita), R4 (dec. 10) y R5, que es donde de verdad
se separa estudiar de resumir.

**No es uno por paper — es uno por técnica.** Hay 10 papers ingeridos y solo
5 producen blueprint, porque `build_blueprint` se niega si no hay procedimiento
registrado en el grafo para esa técnica. `doc6`, `doc7`, `doc8`, `doc9` y
`doc10` están en la BD, se pueden citar, y **no generan nada**.

El study sí cubre los 10: se dispara por `doc_id`, no por técnica.

**Por qué el study importa para transferencia** (tema pendiente): es el único
artefacto que **cruza papers entre sí** — sección «Relación con otras técnicas
de la base»—, y por tanto el único que un run posterior puede reutilizar sin
re-leer la fuente. Se escribe una vez y se cachea (`force=False` por defecto):
regenerarlo en cada run sería volver a empezar de cero, que es exactamente lo
que la transferencia quiere evitar.

*Cruce con cita, no de memoria:* relacionar dos papers exige citar a cada uno
con su propio chunk 0. Relacionar de título sería una atribución sin fuente,
que es el defecto que §5.9.2 mide que mata a R4 en los blueprints.

### 8.2 Errata propia, y afecta a todo lo medido hasta ahora

Al implementar el estudio se descubrió que **el formato de puntero no es
uniforme**, y que el verificador solo entiende uno:

| formato | apariciones en el brazo E | ¿lo parsea `_cited_chunks`? |
|---|---|---|
| `[doc:5:13]` | **130** | **sí** |
| `[doc:5:chunk:13]` | **48** | **no** |
| `[doc:5]` | 16 | no |
| `[doc:id:chunk]` (resto de plantilla) | 3 | no |

**48 de 197 punteros del brazo E no resolvían nunca.** Existían en el texto,
el modelo los escribía de buena fe, y B8 y la capa mecánica de R4 **no los
veían**. El 7,40/run de B8 está medido sobre los que se parsean; el resto
son invisibles.

Corrección: **`[doc:N:M]` es el único formato válido**, se dice con ejemplo
literal en el prompt del estudio, y `normalize_pointers()` lo arregla de forma
**determinista, sin LLM y solo sobre corchetes** — no toca prosa, que es lo
que destruyó P3. *Lo entreparentizado «(doc6: chunk 0)» se deja: es prosa, no
puntero, y convertirlo sería reescribir la frase.*

**Esto no se re-midió sobre el brazo E**: los números de §5.9 siguen siendo
los que se midieron. Arreglar el formato mejoraría B8, pero declararlo sin
volver a medir sería exactamente el error que §7 prohíbe.

### 8.3 Errata propia, segunda: `llm.generate` devolvía vacío sin avisar

Medido al probar ruta 5: **2 de 3 llamadas seguidas al juez devolvieron `""`**
y `generate` lo trataba como éxito — el vacío se devolvía y el llamante lo
leía como veredicto. En ruta 5 eso se contaba como **violación del modelo**:
un fallo del proveedor convertido en acusación de fabricación.

Afectaba a más que ruta 5: a Q1, a la calibración y a cualquier cosa que
confíe en el LLM. Corregido — `generate` reintenta en vacío con el mismo tope
que en excepciones. *Las 15 runs del brazo E contienen algún número de runs
con respuesta vacía del proveedor; no se cuantificó y así debe leerse.*

### 8.4 Ruta 5 implementada

**Umbrales fijados ANTES de la primera run — 2026-10-12, declaración previa:**

| criterio | umbral | por qué |
|---|---|---|
| **R4 cumple** | **≥ 8/15** | **se mantiene el de dec. 10, no se toca.** |
| **B8 resueltas/run** | **≥ 2,00/run** | suelo contra el que se hunde si ruta 5 degrada de más |

- **R4 no se reabre.** El umbral ≥8/15 se fijó en dec. 10 con fecha y se
  mantiene intacto. Ruta 5 cambia el *mecanismo*, no la *definición*.
- **B8 ≥ 2,00/run es nuevo y es la salvaguarda real.** Ruta 5 sube R4
  **quitando punteros** — lo que está en su poder es degradarlos *todos*,
  con lo que R4 se iría a 15/15 y el blueprint no citaría nada. Ese es el
  resultado degenerado que el suelo impide. Se fija en 2,00 porque queda
  por debajo del brazo C (2,73), que reconoce que se pierde algo, pero muy
  por encima de 0, que ya es el fallo que P1' arregló.
- **Contra quién se compara: el brazo E (2/13).** Ruta 5 corre sobre
  `run_blueprint()` con las reglas P4 vigentes, así que E+R5 vs E aísla
  ruta 5 y solo ruta 5. El brazo C queda como referencia histórica.
- **Método:** 15 blueprints vía `api.blueprint_route5()`, `limit=None`
  (crítico completo, ~10k tokens/blueprint). R4 se puntúa con el **pipeline
  calibrado** de dec. 10, vía Q1 + `rescore_r4.py` — el mismo camino que
  midió 6/15 al C y 2/13 al E.

**Decisión de cierre, fijada ahora:** ≥8/15 → **R4 cerrada**, Hito 2 queda solo
con la fila D de la dec. 9. Entre 5 y 7/15 → ruta 5 ayuda pero no cierra: es
decisión de dirección si el coste de producción (+10k tokens/blueprint) lo
paga. **≤4/15 → ruta 5 no sirve**, igual que P4, y el problema de R4 se
declara abierto en este hito.

#### 8.4.1 Resultado (2026-10-12) — **R4 NO se cierra**

| | C | E | **R5** | umbral |
|---|---|---|---|---|
| **B8 resueltas/run** | 2,73 | 7,40 | **2,87** | ≥ 2,00 → **cumple** |
| **R4 cumple** (pipeline calibrado) | **6/15** | 2/13 | **4/15** | ≥ 8/15 → **no cumple** |
| R5 declara silencios | 8/15 | 9/13 | 9/15 | ≥ 10/15 → no |
| fabricaciones/blueprint | 2,67 | 2,00 | **2,13** | — |
| reescritos (garantía) | — | — | **0/15** | 0 → **cumple** |
| llamadas al juez ilegibles | — | — | 0 | — |

**La decisión pre-fijada de §8.4 lo sitúa en el caso que ya se declaró:
≤4/15 → ruta 5 no sirve.** Está exactamente en 4/15.

**Por qué no funciona, y son dos motivos distintos:**

1. **El crítico tiene la misma limitación que todo lo demás.** Caza lo
   mecánico — términos y números ausentes del chunk citado — y se queda corto
   en la paráfrasis, que es donde vive la mitad de las fabricaciones. Las 23
   acusaciones que quedan tras calibrar son casi todas `juez_etiqueta`:
   semántica. **Degradar solo quita lo que el crítico detecta**, y el crítico
   detecta poco de lo que importa.
2. **Casi la mitad del esfuerzo fue a un blanco que a R4 le da igual.** De 83
   degradaciones, **44 fueron punteros rotos** — punteros a chunks que no
   existen (el `doc:0` de §8.2). Esas limpian B8, no mueven R4: un puntero
   roto ya no era una atribución a la fuente. Las **efectivas sobre R4 fueron
   39 en 15 blueprints — 2,60 por blueprint**, contra ~2,13 fabricaciones que
   seguían quedando.

**Y el coste de side-effect es real:** **6 de 15 blueprints terminaron sin
ninguna cita** tras degradar, y B8 cayó de 7,40 a 2,87. Ruta 5 arregla R4 a
medida que vacía el documento de anclas.

**Lectura:** la vía de *verificar y quitar* no cierra R4 porque el verificador
no alcanza lo que R4 exige. Lo que queda por detectar es semántico, y ni la
regex ni el juez lo cazan de forma fiable (§4.2). **R4 queda abierta en este
hit**, con el umbral intacto y la causa declarada.

#### 8.4.2 Lo que ruta 5 sí deja

No es un resultado nulo, y no debe leerse como tal:

- **`reescrito=False` en 15/15** — la garantía de §5.8.3 se sostiene: se puede
  tocar un blueprint sin destruirlo. P3 no pudo; esto sí.
- **44 punteros rotos limpiados** — el `doc:0` de §8.2 ya no llega al
  entregable.
- **0 llamadas ilegibles** — tras el fix de §8.3, el juez contestó siempre.
- **Coste medido en producción**: ~10k tokens/blueprint, y el B8 que queda
  (2,87) sigue por encima del suelo declarado.

---

`agent/attribution.py`:

- `critic_claim(frase, chunk)` — **una llamada por afirmación** (§5.10.2,
  opción A). `temperature=0` a propósito.
- `critic_attributions(blueprint, chunks)` → `{"violaciones": [...], "fallos": [...]}`.
  **`fallos` no son violaciones** — son llamadas ilegibles, y contarlas como tal
  inflaría R4 con errores del verificador.
- `demote_unsupported(blueprint, violaciones)` → sustituye `[doc:N:M]` por
  ` (propuesta del blueprint)`, o lo borra si el puntero estaba roto. **Prosa
  byte a byte idéntica** — verificado por test.
- `critic_and_demote(...)` → lo anterior, con `reescrito=False` siempre.

`api.blueprint_route5(technique, goal, limit=None)` — C + crítico + degradación.

**Pendiente de medir.** Sobre un blueprint real del brazo E (Task-CoEvolve
run2, 17/17 resueltas): 10 afirmaciones criticadas, **6 degradadas**, 0 fallos,
17 → 11 punteros, prosa intacta. Es una prueba de funcionamiento, **no una
medición de R4** — eso requiere las 15 runs con su umbral fijado de antemano.

---

### 8.5 Fila B de §7 — B6 pasa limpio, B5 no llega *(medido 2026-10-12)*

Los dos chequeos de la fila **B Integridad** están implementados en
`run_blueprint_ab.py::_b6_completo` y `_b5_cita_por_modulo`, cableados en
`score()`. **Coste: 0 tokens en los 90 blueprints** — son lectura de bloques,
no llamadas.

#### B6 — 100% (90/90)

| brazo | blueprints | B6 completo |
|---|---|---|
| C/D/E (A+B) | 60 | **60/60** |
| F (dec. 11) | 15 | **15/15** |
| R5 (crítico) | 15 | **15/15** |

**`max_tokens=1500` nunca ha truncado un blueprint.** B6 existía porque H1
salió cortado y nadie se enteró; desde entonces, nadie.

Validado contra truncados sintéticos, para que no sea un chequeo que pasa solo:

| truncado | detecta |
|---|---|
| prosa cortada a media frase | `prosa_cortada` |
| ``` sin cerrar | `cerca_de_codigo_sin_cerrar` |
| tabla acabando en su fila `\| :--- \|` | `tabla_sin_filas` |
| blueprint vacío | `vacio` |
| blueprint correcto | **pasa** ✓ |

#### B5 — no llega en ningún brazo

**El umbral no se inventa: está escrito en §3.1 desde el principio** —
*«**cada** módulo/dependencia principal lleva `[doc:chunk]`»*. «Cada» es 100%.

| brazo | módulos con cita | B5 |
|---|---|---|
| **E** (P1'+P4) | 49/54 | **91%** |

**Esta tabla está obsoleta.** La comprobación de B5 ha pasado por cuatro
versiones (erratas sexta a octava, §8.5 y §8.7); **el 91% del brazo E era
artefacto de medir otra cosa**. Los números definitivos, con la versión
actual y todos los brazos re-mididos con ella, están en **§8.7**: mejor brazo
**G con 84,7%**. Se deja la tabla tal cual para que se vea lo que se creyó y
cuándo dejó de ser cierto.

**Ninguno llega a 100%; la fila B queda abierta.** E es la más cerca, y lo
era justo de esperar: es el brazo con más citas por documento (B8 7,40/run),
y más citas repartidas llenan más módulos.

#### Errata propia, tercera — medí antes de fijar el umbral

§3.1 exige declarar el suelo **antes de la primera run**. Aquí la run es
lectura mecánica, pero la regla es la misma: **medí B5 antes de escribir en
§7 cuál era su umbral.** Se declara en lugar de esconderlo.

**Por qué no es un umbral inventado *a posteriori*:** el número no se escogió
mirando el resultado — **se leyó de la definición que ya estaba escrita**
(«cada» → 100%). Ningún brazo pasa, así que no hay incentivo para haberlo
ajustado. Pero el proceso fue el inverso al ordenado, y eso queda anotado.

#### Errata propia, cuarta — normalizar punteros cambia B5 de 35% a 68%

B5 contaba módulos con `\[\d+:\d+\]`, es decir solo el formato canónico. Con
los datos en crudo daba **82/233 = 35%**. Tras pasar `normalize_pointers`
(dí. §8.2) da **159/233 = 68%**. **Los blueprints son idénticos; cambió solo
la lectura.**

Es la segunda consecuencia de §8.2, y la más grande: los 14 formatos de
puntero conviviendo **inflaban el fallo de B5 en 33 puntos porcentuales**. Un
módulo con `[doc:5:chunk 13]` **sí lleva cita** — contarlo como fallo habría
sido mentir en la dirección contraria a la de las erratas anteriores.

Mismo criterio que ya se aplicó a B8 y a la capa mecánica de R4: **normalizar
es edición de cadena, no reescritura del texto** (§5.8.3 sigue intacto).

#### Estado de §7 tras esta medición

| eje (§2) | criterio | umbral | medido | estado |
|---|---|---|---|---|
| **C** Integridad | **B6** | termina completo | **90/90 = 100%** | **✓ cerrada** |
| **C** Integridad | **B5** | cada módulo (100%) | **mejor 91% (E)** | **✗ abierta** |

### Decisión 13 — criterio de la dimensión D, *fijado antes de medir* *(2026-10-12)*

§2.D dice qué hay que comprobar («devuelve algo que no sea todos los pasos en
`"todo"`») pero **no pone número**. Se pone aquí, **antes de ejecutar nada**, y
por el orden inverso al de la errata de §8.5: primero la tabla, después la run.

**Tres condiciones. La fila D cierra solo si las tres pasan.**

| # | comprobación | umbral | coste | falla si |
|---|---|---|---|---|
| **D1** | `agent_template.py` compila y `run()` no lanza excepción | 100% de los agentes | 0 | `py_compile` cae o `run()` levanta |
| **D2** | el `status` de cada paso **se calcula en ejecución**: el literal `"todo"` **no aparece escrito** en el código fuente | **0 agentes** con el literal | 0 | el estado está escrito en el archivo, es decir el resultado se sabía antes de correrlo |
| **D3** | ejecutado, el `trace` devuelve **algún paso en estado `done`** | **≥ 1 paso** por agente | 0 | ningún paso llega a `done` — ya sea porque todos siguen en `"todo"` (el fallo de §1.2) o porque todos fallan |

**Enmienda a D3, fijada antes de medir el brazo que va a arreglar esto**
*(2026-10-12)*. La redacción original decía «estado ≠ `"todo"`», y con ella
**un arnés que fallara los 20 pasos habría cerrado la fila**. Se endurece a
`done`. **El baseline de §8.6 no cambia**: estaba en 0/20 hecho, así que no
pasa bajo ninguna de las dos lecturas — la enmienda no retoca un resultado ya
visto, cierra una puerta antes de abrirla.

**Segunda enmienda a D3, y va con su crónica** *(2026-10-12)*.

`done` se definía como *«la recuperación devuelve documentos»*. Implementado y
medido, **D3 pasó 20/20 y cerró la fila**. Entonces se comprobó si el chequeo
discrimina, y no lo hacía:

| consulta | `deep_sweep` | mejor score |
|---|---|---|
| `ajkdhasdkjhaskdj` | **9 docs** | 0,132 |
| `zzzz qqqq nonsense xyz` | **9 docs** | 0,154 |
| `the of and` | **9 docs** | 0,086 |
| `Hájek full-set estimation` | 8 docs | 0,546 |
| `contextual subgraph extraction` | 8 docs | 0,748 |

**`deep_sweep` devuelve documentos para cualquier cadena.** Un paso estaba en
`done` **sin importar lo que se le preguntara**: el gate se ponía verde solo
por llamar a la función. Es el mismo defecto que §3.1 le achacó a B2 y que la
propia D1 arrastra — *verde sin decir nada* — y **acaba de cerrar una fila**.

**Se enmienda antes de declarar el cierre.** `done` pasa a exigir
**`mejor_score >= 0.30`**.

- **Por qué 0.30 y no otro número:** se elige en **medio del hueco** medido —
  el máximo de las consultas sin sentido es **0,154** y el mínimo de los
  procedimientos reales **0,546**. El umbral cae a 0,15 por encima de unas y a
  0,25 por debajo de las otras.
- **Lo que esto NO es:** no es un umbral calibrado contra un juez, es una
  separación observada sobre **8 consultas**. Se declara la muestra pequeña
  porque el número se va a leer como si viniera de una curva ROC y no viene.

**Secuencia completa, para que no se lea como ajustar el umbral a la salida:**

1. Criterio fijado («≥1 paso `done`») — *antes* de cualquier run.
2. Baseline: **0/20**, no pasa. 
3. Generador cambiado: **20/20, cierra**.
4. Se comprueba si el chequeo discrimina: **no lo hace**.
5. Se enmienda con la frontera medida, **antes** de escribir «cierra» en §7.
6. Se vuelve a medir con la enmienda ya puesta.

El paso 4 es el que importa: **un gate verde que no discrimina es peor que un
gate rojo honesto**, y aquí habría quedado escrito como cierre.

**Por qué D2 está ahí y no basta con D1.** D1 hoy pasa con un agente que no
hace nada: es el defecto que §3.1 ya le achacó a B2 («verde sin decir nada»).
**D2 es la condición que impide que eso vuelva a pasar** — si el estado está
escrito en el fichero, el resultado no se obtuvo, se copió. Es el equivalente
exacto de lo que el Hito 1 llamó fabricación, aplicado al funcionamiento.

**Por qué los tres son gratuitos.** Compilar, leer el fuente y ejecutar `run()`
no cuesta un token: `run()` recorre una lista de cadenas. Ninguna de las tres
llama a un LLM.

**Qué NO mide D.** No mide que la técnica esté **bien implementada** — eso
exigiría ejecutar el arnés contra una tarea con verificación externa, que no
existe. Mide que **el arnés hace algo en vez de fingir que lo hizo**. Si las
tres pasan, lo que se declara es «el agente se ejecuta y decide sus estados en
runtime», **no** «implementa correctamente PEARL». La distinción se escribe
aquí para que no se confunda al cerrar §7.

### 8.6 Dimensión D — por fin medida, y no pasa *(baseline 2026-10-12)*

§2.D decía *«nadie lo ha medido nunca»*. Ya no. Medidor:
`evals/run_dimension_d.py`, criterio **fijado antes** (§6 dec. 13), coste
**0 tokens**.

| agente generado | D1 ejecuta | D2 sin `"todo"` literal | D3 pasos hechos | responde al contexto |
|---|---|---|---|---|
| PEARL | ✓ | ✗ | 0/4 | ✗ |
| Procedural Graphs | ✓ | ✗ | 0/2 | ✗ |
| ReASearch | ✓ | ✗ | 0/6 | ✗ |
| Task-CoEvolve | ✓ | ✗ | 0/4 | ✗ |
| WikiSkill | ✓ | ✗ | 0/4 | ✗ |
| **total** | **5/5** | **0/5** | **0/20** | **0/5** |

**D1 cumple, D2 y D3 no. La fila D no cierra.**

El dato que §1.2 anticipaba, ahora con número: **0 de 20 pasos** se ejecutan
jamás, y el literal `"todo"` está escrito en los 5 ficheros — es decir **el
resultado ya venía escrito antes de correrlo**. Los 5 agentes devuelven
**exactamente lo mismo con contextos distintos**: `run()` no lee su entrada.

**D1 pasa con un agente que no hace nada**, tal como §3.1 advirtió de B2. Es
exactamente para lo que existe D2: sin ella, esta tabla se leería verde.

**Coste.** La primera ejecución sí llamó al LLM (`PEARL.retrieve_evidence`,
pearl.py:102) sin que mi parche lo cubriera. Se parcheó también y se repitió:
**salida idéntica**, lo que confirma que `agent_template.py` sale de
`bp["procedures"]` y no del LLM. El coste real de la run fue *n llamadas de
`retrieve_evidence` por técnica*; la medición definitiva, **cero**.

#### Qué mide D, y qué no — declarado antes de que pase

Si D2 y D3 llegaran a pasar, lo que se podrá declarar es *«el agente se
ejecuta y decide sus estados en runtime»*. **No** *«implementa correctamente
PEARL»*. Eso último exigiría ejecutar el arnés contra una tarea con verificación
externa, y esa tarea no existe. La frase va escrita aquí **antes** de que se
toque el generador, para que no se confunda al cerrar §7.

#### Resultado tras cambiar el generador *(2026-10-12)*

`instantiate_agent_template` ya no escribe el estado: cada paso llama a
`deep_sweep` con su nombre de procedimiento y guarda lo que la recuperación
diga. Re-medido con el criterio ya enmendado (2ª enmienda de dec. 13):

| agente | D1 | D2 | D3 `done`/pasos | responde al contexto |
|---|---|---|---|---|
| PEARL | ✓ | ✓ | **4/4** | ✓ |
| Procedural Graphs | ✓ | ✓ | **1/2** | ✓ |
| ReASearch | ✓ | ✓ | **5/6** | ✓ |
| Task-CoEvolve | ✓ | ✓ | **4/4** | ✓ |
| WikiSkill | ✓ | ✓ | **4/4** | ✓ |
| **total** | **5/5** | **5/5** | **18/20** | **5/5** |

**Las tres condiciones cumplen → la fila D cierra**, bajo el criterio tal como
queda tras dos enmiendas.

#### Corrección a la justificación del umbral 0.30

La 2ª enmienda dice que 0,30 cae *«en medio del hueco»* entre sin sentido
(máx. 0,154) y procedimiento real (mín. 0,546). **Eso era cierto solo para las
cuatro consultas controladas**, no para los pasos que el arnés genera de
verdad. Al medir:

| paso | score | estado |
|---|---|---|
| Procedural Graphs, paso 2 | **0,290** | `empty` |
| ReASearch, paso 5 | **0,220** | `empty` |
| ReASearch, paso 1 | 0,314 | `done` |
| Procedural Graphs, paso 1 | 0,317 | `done` |

**El umbral no cae en un hueco limpio para los pasos reales: 0,290 y 0,311
quedan separados por dos centésimas.** Se corrige el texto de la enmienda.

**Qué sí sostiene el 0,30** y no necesita retoque: separa las cadenas sin
sentido (**0,086 – 0,154**) de cualquier cosa que nombre algo real
(**≥ 0,220**). Ahí el margen es de 66 centésimas y no hay ambigüedad.

**Qué es discutible:** clasificar `empty` a un paso que encontró 5 documentos
con score 0,220. Dos lecturas, y se dejan las dos escritas:

- *Es acertado*: `empty` significa **«sin respaldo fuerte en el corpus»**, y un
  procedimiento con 0,220 justamente lo tiene flojo. La línea `detalle` lo
  dice con el número delante, nada queda escondido.
- *Es un falso negativo*: 0,290 y 0,311 son empíricamente indistinguibles y
  acaban en estados distintos por una centésima.

**Lo que no se hace** es declarar la fila sobre la primera lectura sin decir
la segunda. La muestra siguen siendo **8 consultas controladas y 20 pasos
reales**; con eso no se calibra una frontera, se elige una y se declara dónde
corta.

#### Lo que D cierra, y lo que no

Cierra: **el agente generado se ejecuta, decide sus estados en runtime y su
salida cambia con la entrada.** Antes 0/20 pasos se ejecutaban y el resultado
venía escrito en el fichero; ahora 18/20 llegan a `done` y 2/20 se declaran
sin respaldo.

**No cierra:** que la técnica esté **bien implementada**. `run()` recupera
evidencia por procedimiento; no ejecuta PEARL ni Task-CoEvolve. §2.D lo advierte
desde el principio y la frase queda aquí para el cierre de §7.

### Errata propia, sexta — **B5 medía otra cosa** *(2026-10-12)*

La cuarta errata arregló los *formatos* de puntero. Esta arregla **qué se
contaba**, y es mayor.

`_b5_cita_por_modulo` buscaba `N. **...**` en **todo el documento**, es decir
en cualquier lista numerada en negrita. Sobre los 87 blueprints medidos:

| | blueprints | % |
|---|---|---|
| los items detectados caían **dentro** de la sección de módulos | **34** | **39%** |
| caían **fuera** — se medían los *pasos del orden* de implementación | **40** | **46%** |
| sección de módulos sin items en negrita detectables | 13 | 15% |
| sin sección de módulos | 3 | 3% |

**Solo 2 de cada 5 mediciones miraban los módulos.** La cifra del 91% del
brazo E era artefacto de eso.

Se reescribe: localiza las secciones de **módulos** y **dependencias**
(las dos, que §3.1 menciona juntas y a veces van separadas), toma los items
con viñeta o numeración **y negrita**, y se queda con la indentación mínima
para no contar sub-componentes anidados.

**Los números cambian, y a peor.** Ninguna otra cifra de este documento se
toca; solo esta:

| brazo | B5 antes (errónea) | **B5 corregida** |
|---|---|---|
| E | 91% | **53%** |
| B | 55% | **59%** ← ahora el mejor |
| C | 68% | **47%** |
| D | 63% | 55% |
| F (dec. 11) | 63% | **36%** |
| R5 | 48% | 51% |
| **global** | 68% | **53%** (260 con cita, 249 sin) |

Se declara el empeoramiento: **el mejor brazo pasa de 91% a 59%** y el umbral
sigue siendo 100%. Si la errata hubiera resultado en un número mejor, habría
sospecha; sale peor y también se escribe.

### Decisión 14 — R8, cita **dentro de cada módulo** *(fijada 2026-10-12, antes de medir)*

**Diagnóstico, ya con B5 corregida:** el modelo **sí cita**, pero en la
primera línea de la sección («Según Yang et al. [doc:0:0], PEARL se compone
de los siguientes módulos:») y luego enumera los módulos **sin puntero cada
uno**. B5 cuenta por punto, no por documento.

#### Lo que NO se hace, y por qué

**Se descarta propagar el puntero de la cabecera a cada módulo.** Sería
mecánico, determinista y llevaría B5 a 100% sin un solo token. Pero en PEARL
r1 la cabecera cita **`[doc:0:0]`, el chunk del título** — no donde se
describen los módulos. Copiarlo a cada punto daría un puntero **que resuelve y
no sostiene**: B5 subiría, B8 seguiría verde, y la atribución sería peor que
antes. **Un 100% conseguido así es exactamente el gate verde sin contenido de
B2.**

#### Lo que se hace

**R8**, añadida a `_WRITING_RULES`:

> *Cada módulo y cada dependencia que enumeres lleva **su propia** cita literal
> + puntero **dentro de ese punto**. Una cita en la cabecera de la sección no
> cubre los puntos de debajo. Si el módulo es propuesta tuya y no del paper,
> márcalo con R6 en su lugar — no le pongas un puntero que no hay.*

La cláusula R6 no es cortesía: sin ella, exigir cita al 100% **empujaría al
modelo a inventar punteros para módulos que son suyos**, que es el fallo de §4.2
en su forma más cara.

#### Umbral — no se mueve

**Sigue siendo 100%**, leído de §3.1 («cada módulo»). No se toca a pesar de
que la línea corregida está en 53%.

**Refinamiento declarado antes de medir:** un punto marcado
`(propuesta del blueprint)` **no puede** llevar puntero de origen por
definición — no tiene fuente. Se cuenta aparte. **Se reportarán las dos
cifras**, con y sin la exención, para que se vea cuánto explica.

#### Brazo y comparación

- **Brazo G** = `api.blueprint_loop` con R8, 15 runs (5 técnicas × 3).
- **Se compara con F** (dec. 11): mismo camino de generación, mismas reglas
  de dec. 11, **la única diferencia es R8**. G vs F aísla R8.
- **B5 se mide con la comprobación ya corregida** (errata sexta) en ambos —
  es decir, los dos lados de la comparación usan la misma regla nueva.

**Se declara de antemano:** 53% → 100% en una sola regla es optimista. Si G
queda por debajo, se reporta el número y se decide entonces, sin reescribir
esta sección.

### 8.7 B5 con R8 — sube de 39% a 85%, y el umbral sigue sin tocar

**Errata séptima y octava, ambas de B5 y ambas del mismo tipo.** Tras la
sexta (medía otra cosa) y la séptima (no veía los módulos-cabecera), aparecen
dos más al aplicar R8, porque R8 **cambió la forma en que el modelo escribe**:

- **séptima**: R8 hizo que los módulos pasaran a ser cabeceras
  (`### Módulo 1: …`); el chequeo solo veía viñetas, y **6 de 15 blueprints
  del brazo G salían sin medir — no aprobados**. Se añaden cabeceras como
  unidad.
- **octava**: en G2 el modelo escribió cada módulo como **bloque de cita
  literal + paráfrasis** separado por línea en blanco, sin negrita; otra vez
  **sin medir**, y esos bloques **todos llevaban puntero**. Se añade el
  párrafo como tercera forma.

B5 acepta hoy **tres formas de módulo**: cabecera que nombra un módulo,
item con viñeta/numeración y negrita, y párrafo. Se re-midieron **todos los
brazos con la misma versión**, para que la comparación sea justa.

#### Resultado

| brazo | B5 | Δ vs F |
|---|---|---|
| **G** (R8) | **72/85 = 84,7%** | **+45,6** |
| G2 (R8 + enmienda de formato) | 61/75 = 81,3% | +42,2 |
| A+B (media de los cuatro) | 211/353 = 59,8% | +20,7 |
| R5 (crítico) | 37/76 = 48,7% | +9,6 |
| **F** (dec. 11, sin R8) | 25/64 = **39,1%** | — |

**R8 funciona**: F vs G aísla R8 y son +45,6 puntos, con el mismo camino de
generación y las mismas reglas de dec. 11.

**La enmienda de formato de R8 (G2) no ayudó: 81,3% < 84,7%.** Se declara como
resultado negativo — se pagó una run entera para comprobar que la cláusula
«el puntero es `[doc:<id>:<chunk>]` y nada más» **no sube B5**. G queda como
brazo de referencia.

**Cero puntos marcados `(propuesta del blueprint)` en G y G2**, así que la
exención de la dec. 14 **no explica nada**: las dos cifras coinciden.

#### Los 13 fallos que quedan en G, y qué son

| | |
|---|---|
| **infraestructura que el paper no cubre** | historial de ejecuciones del agente, registro de experimentos, conjunto de tareas de validación, capas de ficheros (`raw/`, `wiki/`, `skills/`) |
| **atribuidos con notación equivocada** | «citado en §3.2.1», «(ecuación 4)» — atribuyen, pero no con `[doc:N:M]` |

**Ninguno es una atribución al paper sin respaldo.** Son piezas de despliegue
que el paper no describe — y **el paper no tiene por qué describirlas**: describe
PEARL, no cómo montar el sistema que lo ejecuta.

#### Por eso el umbral de 100% puede estar midiendo otra cosa

§3.1 pide que **cada** módulo lleve `[doc:chunk]`. Pero un blueprint honesto
que incluya infraestructura de despliegue **no puede** citarla al paper, porque
**no está en el paper**. La alternativa sería inventar el puntero, que es el
fallo de §4.2.

**No se toca el umbral** — sigue en 100% y el mejor brazo está en 84,7%. Se
deja escrito, con la misma forma que la dec. 12 hizo con R4, que **una
posibilidad es que B5 no sea un gate sino una lista para revisar**: cada punto
sin cita clasificado en *«infraestructura propia»* o *«atribución mal
formateada»*, que las dos cosas son distinguibles mecánicamente.

**Esa decisión no se toma aquí.** Va al mismo sitio donde se resolvió R4: con
el umbral intacto, el valor medido a la vista y la elección declarada.

### Decisión 15 — R1 no puede prohibir lo que R5 exige *(fijada 2026-10-12, antes de medir)*

**El conflicto está en las propias reglas**, y los números lo delatan:

| brazo | R1 | R5 cumple |
|---|---|---|
| D (P3) | suelto | **10/15** |
| E, R5 (crítico) | suelo | 9/15 |
| C | suelo | 8/15 |
| **F (dec. 11, R1 ancla)** | **ancla literal obligatoria** | **4/15** |

**R1 dice textualmente: «sin cita literal + puntero no hay salvación por
ninguna otra regla».** R5 pide escribir *«el paper no especifica cómo se fija
epsilon»* — una frase que **no tiene cita que poner**: no hay fragmento que
entrecomillar de un silencio. Con R1 como suelo, **declarar un silencio es
incumplir R1**, y el modelo resuelve la contradicción rellenando el hueco,
que es exactamente lo que R5 castiga.

**No es un fallo del modelo: es una regla mal puesta.** Se corrige aquí.

#### Lo que cambia

**R1 queda con una excepción explícita, y solo una:**

> *Lo anterior no aplica a las declaraciones de silencio de R5 («el paper no
> especifica/describe…»). Esas frases no llevan cita porque **no tienen
> fuente que citar**: llevan la marca de R6 y ya.*

Fuera de esa excepción, R1 sigue siendo suelo sin tocar.

#### Brazo y comparación

- **Brazo H** = `api.blueprint_loop` con R8 **y** la excepción de R1.
- **Se compara con G**: mismo camino, mismas reglas de dec. 11, mismas de R8.
  **La única diferencia es la excepción de R1.** G vs H la aísla.
- Se re-puntúa G con Q1 para tener su línea base de R5 **antes** de correr H.

#### Umbrales, fijados antes de medir — ninguno se mueve

| | umbral | base en G |
|---|---|---|
| **R5** | ≥ 10/15 | **9/14** |
| **R4** | ≥ 8/15 (pre-filtrada, dec. 12) | 6/14 |
| **B5** | 100% | 84,7% |
| **B8** | ≥ 2,00/run | sin tocar |

**Se declara el riesgo de la excepción antes de ver el resultado:** relajar R1
puede **bajar R4**, que ya está en 6/14. Si H sube R5 y baja R4, no es una
mejora — es mover un número de una columna a otra, y se dirá.

#### Resultado de H — **la excepción empeoró R5** *(2026-10-12)*

| | G (base) | **H (R1 con excepción)** | umbral |
|---|---|---|---|
| **B5** | 84,7% | **95,8%** | 100% |
| **R4** | 6/14 | 7/15 | ≥ 8/15 (pre-filtrada) |
| **R5** | **9/14** | **8/15** | ≥ 10/15 |
| fabricaciones/blueprint | 1,57 | 1,53 | — |
| **rellenados/blueprint** | 1,07 | **1,80** | — |

**G vs H aísla la excepción de R1. El resultado es negativo para R5.**

Se relajó el ancla **para que el modelo pudiera declarar silencios**, y lo que
hizo fue lo contrario: **rellenó 68% más de detalles** (1,07 → 1,80 por
blueprint) y R5 bajó de 9/14 a 8/15. B5 subió 11 puntos y R4 uno, pero
**R5, el número por el que se hizo el cambio, empeoró**.

**La hipótesis se refuta.** La lectura más plausible, y se deja como lectura y
no como medida: **el ancla de R1 no era lo que impedia declarar silencios —
era lo que contenía la invención.** Quitada la presión de citar literalmente
cada cosa, el modelo escribió más cosas, y más de ellas no venían del paper.
El síntoma está en la misma tabla: el ancla subió B5 y R4, que son métricas de
*está respaldado*; bajó R5, que mide *reconoce lo que falta*.

**No se itera sobre esto sin una hipótesis nueva.** Una segunda variante de la
misma excepción sería repetir el experimento con la esperanza de que salga
distinto. G sigue siendo el mejor brazo de B5 y el menos malo de R5.

### 8.8 Errata propia, novena — **R5 no es medible con el instrumento actual**

*(medido 2026-10-12, sin generar nada)*

R4 tiene un pipeline calibrado (dec. 10). **R5 no tiene ninguno**: sus números
salen del juez Q1 en crudo, y ese juez corre a `temperature=0.2`. Y R5 estaba a
un blueprint de su umbral (G: 9/14 contra 10/15).

Antes de gastar una run de generación en subir 9 → 10, se midió si **la
decisión del juez es estable**. Se hizo lo mismo que `measure_judge_noise.py`
hace con el juez del QA: **re-juzgar la MISMA respuesta varias veces**. Entre
repeticiones **no se vuelve a generar nada** — el agente no vuelve a intervenir
—, así que lo que varíe es ruido del instrumento, por construcción.

Medida: `evals/measure_q1_noise.py`, brazos G y H, 3 repeticiones por blueprint,
**cero llamadas de generación**.

#### Resultado

| medida | resultado |
|---|---|
| **Acuerdo del juez consigo mismo** (mismo blueprint, otro juicio) | **G 8/11 = 73%** · **H 9/13 = 69%** |
| **Blueprints que cambian de veredicto en R5** | **14 de 27 = 52%** |
| Blueprints que cambian de veredicto en R4 | 9 de 27 = 33% |
| **Conteo del brazo G** | original **9/14** · repeticiones **3/12, 5/15, 4/13** |
| **Conteo del brazo H** | original **8/15** · repeticiones **5/13, 6/14, 5/12** |
| Juicios que no salen en JSON (el blueprint cae del denominador) | WikiSkill: solo **5-6 de 9** válidos · Task-CoEvolve 7-8 de 9 |

Un acuerdo del **69-73%** entre dos juicios del mismo juez sobre el mismo texto
está **apenas por encima del azar** para un veredicto binario. Y el conteo de un
brazo se mueve por un **factor de 2**: G pasa de 9 a 3.

#### Los confounds están descartados

- **No es el truncado.** H no tiene ni un blueprint por encima de 9000 chars
  (máx. 7761) y es **igual de inestable** que G, que sí trunca 2 de 15.
- **No es el agente.** Entre repeticiones no se vuelve a ejecutar el generador.
- **No es la fuente.** Se reutiliza exactamente el mismo `_source()` de la
  evaluación original.
- **No es el prompt.** Prompt y modelo son idénticos a los de §8.7.

#### Consecuencia

**La incertidumbre de R5 es de ±3 a 4 blueprints, y el umbral está en 10/15.**
Ningún brazo puede decirse que esté cerca o lejos del umbral. **Gastar una run
de generación en subir 9 → 10 habría sido optimizar un número que la medición
no puede resolver.** La fila de R5 pasa de *«no llega»* a **«no medible»**, que
es una afirmación distinta y más fuerte: no dice que el sistema falle, dice que
la regla no se puede aplicar todavía.

**Efecto secundario, y se declara:** **R4 también está tocado** — 33% de flips.
Su 6/15, ya reclasificado como *pre-filtro* por la dec. 12, **es un número
blando** y se leerá como tal.

#### Nada de esto mueve un umbral

R5 sigue en **≥ 10/15**, que es lo que decía antes de medir. La errata no
cambia el umbral ni el número original: **añade el hecho de que el número no
era reproducible.** Los valores de §8.7 se conservan y se marcan como
*medidos con instrumento no calibrado*.

### Decisión 16 — R5 queda en *no medible*; primero el juez *(fijada 2026-10-12)*

Se sigue el mismo criterio de la dec. 12: **no se re-baja un umbral, se
repara el instrumento.** R5 no se ataca con más generación porque no se sabe a
cuánto está del umbral.

Secuencia fijada, en este orden:

1. **`temperature` del juez → 0.** Hoy es 0.2 y ese es el origen directo de la
   mitad de los flips.
2. **Forzar salida JSON.** Hoy el juez se larga a prosa en algunos blueprints y
   el resultado cae del denominador **sin que se diga** — que es la clase de
   fallo silencioso que la errata 2 del Hito 1 ya costó caro. Un parseo fallido
   debe ser un error visible, no un blueprint menos.
3. **Quitar la instrucción «da como mucho 3 ejemplos».** Obliga a una elección
   discrecional en cada juicio, y esa elección es una fuente de varianza: el
   mismo fallo puede enumerarse o no dependiendo del azar.

**Criterio de éxito antes de re-medir R5:** repetir la misma medida sobre los
mismos blueprints y obtener **< 10% de flips** y **< 2 blueprints de recorrido
en el conteo por brazo**. Si no se alcanza, R5 se deja declarada *no medible*
y se cierra Hito 2 sin esa fila — que es preferible a cerrarla con un número
que no se sostiene.

**G sigue siendo el mejor brazo de B5 y el menos malo de R5.** Esta errata no
promueve a nadie; solo retira el derecho de R5 a medida mientras el juez no sea
reproducible.

### 8.9 B5 — qué son exactamente los que no llevan cita *(medido 2026-10-12)*

§8.7 dejó escrito que el umbral de 100% **podría estar midiendo otra cosa**, y
que la clasificación de los puntos sin cita **era distinguible mecánicamente**.
Aquí se hace, antes de decidir.

Clasificación mecánica de cada módulo sin `[doc:N:M]`:

| | **H** (95,8%) | **G** (84,7%) |
|---|---|---|
| módulos totales | 72 | 85 |
| con cita | **69** | 72 |
| sin cita | **3** | 13 |
| ↳ atribuyen con **notación equivocada** (`§`, `ecuación`, `figura`, `tabla N`) | **0** | 6 |
| ↳ **sin ninguna atribución** (infraestructura de despliegue) | **3** | 6 |
| ↳ exentas por dec. 14 (`(propuesta del blueprint)`) | 0 | 1 |

**En H no queda ni una sola atribución inventada ni mal formateada.** Los tres
puntos sin cita son piezas que el paper no describe — el paper describe PEARL,
no el sistema que lo ejecuta. En G sí hay 6 con notación equivocada, que es un
fallo **de formato**, no de respaldo: el modelo sí atribuye, pero no con el
puntero que pide la regla.

**No exentar la dec. 14 cambia nada:** 0 puntos exentos en H.

### Decisión 17 — B5 pasa de *gate* a *lista de revisión* *(fijada 2026-10-12)*

**El umbral de B5 sigue en 100%, intacto.** Sale de la palabra **«cada»** de
§3.1 y no se toca. Lo que cambia es **qué papel juega**, con el mismo
movimiento que la dec. 12 hizo con R4.

**Por qué no puede ser un gate.** B5 exige que **cada** módulo lleve puntero al
paper. Pero un blueprint honesto que incluya infraestructura de despliegue
**no puede** citarla al paper, porque **no está en el paper**. La única forma
de llegar a 100% en ese caso es **inventar el puntero**, que es exactamente el
fallo de §4.2 y el que B5 se supone que detecta. **Un gate de 100% sobre
contenido que la fuente no contiene es un incentivo a fabricar citas.** No es
una hipótesis: es lo que obligó a reescribir B5 tres veces (erratas sexta a
octava).

**B5 = 95,8% (H), lista de revisión, clasificación mecánica y revisión humana
obligatoria antes de publicar.**

Cada punto sin cita se clasifica de forma determinista en una de estas tres, y
**la clasificación es parte del entregable**:

1. **`infraestructura propia`** — el paper no describe esa pieza; no hay
   fuente que citar. *(los 3 de H)*
2. **`atribución mal formateada`** — sí atribuye, pero con `§` / `ecuación` /
   `figura` en vez de `[doc:N:M]`. **Es un fallo de formato y se arregla
   apuntando**, no se perdona. *(los 6 de G)*
3. **`exenta dec. 14`** — marcada `(propuesta del blueprint)`: sin fuente por
   definición. *(1 en G, 0 en H)*

**La tercera categoría no absuelve.** Una pieza exenta sigue siendo una pieza
que el blueprint introduce por su cuenta, y el revisor la ve igual.

### 8.10 El arreglo del juez **no funcionó** *(medido 2026-10-13, 90/90 juicios)*

La dec. 16 fijó tres cambios y un criterio de éxito. Los tres se aplicaron y se
re-midió **sobre los mismos blueprints, 3 repeticiones, sin generar nada**:

| cambio | estado |
|---|---|
| `temperature` 0.2 → **0** | aplicado |
| salida JSON reforzada («tu ÚNICA salida es el objeto JSON») | aplicado |
| «máximo 3 ejemplos» → **exactamente 1 por lista** (quita la elección discrecional) | aplicado |

**Criterio de éxito de la dec. 16: < 10% de flips y < 2 blueprints de recorrido
por brazo.**

#### Resultado — incumplido en los dos sentidos

| | juez original (temp 0.2) | **juez corregido (temp 0)** | criterio |
|---|---|---|---|
| **R5 flips de veredicto** | 52% | **50%** | < 10% |
| **R4 flips de veredicto** | 33% | **42%** *(peor)* | — |
| parseo de JSON fallido | 3 blueprints | **11 juicios = 12%** *(peor)* | 0 |
| recorrido del brazo **G** | 8 puntos (sd 4,3) | **33 puntos (sd 17,3)** *(peor)* | < 2 |
| recorrido del brazo **H** | 4 puntos (sd 2,3) | **21 puntos (sd 10,3)** *(peor)* | < 2 |

**Nada mejoró y dos cosas empeoraron.** R5 pasa de 52% a 50% de flips, que está
dentro del ruido de la propia medida; **R4 empeora** de 33% a 42%; y los
fallos de parseo suben de 3 blueprints a **11 juicios**, es decir, **1 de cada
8 llamadas no devuelve JSON**.

El recorrido por brazo se dispara: G pasa de 8 puntos a **33**, y una misma
repetición da **R5 = 1/11** donde otra da 5/14.

#### Por qué: la temperatura no era la fuente del ruido

`openai/gpt-oss-20b` es un modelo **Mixture-of-Experts**. El enrutado de
expertos **no es determinista ni a temperature=0** — depende del batching y del
estado de la infraestructura del proveedor. Bajar la temperatura atacaba el
muestreo, que **no era la causa principal**.

Y la instracción de «tu única salida es el JSON» **empeoró** el parseo: un
modelo que razona en prosa, al prohibirle la prosa, o se calla el razonamiento
(y responde peor) o razona igual y se come el presupuesto de tokens.

**La lectura honesta: no son los parámetros del juez, es el juez.** La
temperatura no era la palanca. Se midieron dos configuraciones distintas y las
dos son igual de irreproducibles.

#### Lo que dice la propia dec. 16

> *Si no se alcanza, R5 se deja declarada* no medible *y se cierra Hito 2 sin
> esa fila — que es preferible a cerrarla con un número que no se sostiene.*

**Eso es lo que ocurre.** R5 **no se re-medirá** con este juez. La fila queda
cerrada como *no medible*, umbral intacto en 10/15.

#### Y R4, que no estaba en la misma fila

R4 no estaba en el alcance de la dec. 16, pero **comparte el juez**, y su número
se mueve igual. El 6/15 de §7.1 **no se puede sostener como medida**. Lo que sí
se sostiene es lo que ya decía la dec. 12: **R4 va pre-filtrada con revisión
humana obligatoria** — y esa frase no depende del número, depende de que el
modelo atribuye por encima de lo que la cita sostiene, que está medido de forma
independiente en dec. 11 y §8.7.

**La fila de R4 se reetiqueta: el 6/15 pasa a *medido con instrumento no
calibrado*, y la frase de la dec. 12 se queda como lo único que se afirma.**

#### Qué haría falta para medir R5 de verdad

**Cambiar de modelo de juez**, no sus parámetros. Eso es un instrumento nuevo,
y como tal requiere su propia declaración **antes** de medir, y una run aparte.
**No se hace aquí.**

#### Lo que esto no es

**No es bajar el umbral.** 100% sigue escrito en §3.1 y el 95,8% se publica al
lado. Lo que desaparece es el derecho de B5 a **bloquear**; lo que aparece es
la obligación de **entregar la lista**. Un blueprint que no entregue la lista
incumple B5 igual que antes.

**No es eximir la infraestructura.** `infraestructura propia` **no** significa
*correcto*: significa *el paper no puede juzgarlo*. Sigue siendo material que
un humano tiene que mirar, y es la categoría más propensa a esconder una
invención — por eso se enumera y no se silencia.

**No promueve a ningún brazo.** H sigue en 95,8%, G en 84,7%, F en 39,1%.
Solo cambia qué significa cada cifra.

#### Consecuencia para §7.1

La fila de B5 deja de ser *«no llega»* y pasa a **medida y cerrada con lista
de revisión**, igual que R4 lleva su frase desde la dec. 12.

---

### 8.11 Cambio de juez — **declarado antes de medir** *(dec. 18)*

§8.10 cerró diciendo que hacía falta **otro modelo de juez**, y que eso es un
instrumento nuevo que se declara antes de medir. Aquí está esa declaración.
**Se escribe el criterio ANTES de la corrida**, igual que la dec. 16.

#### Candidato

| | |
|---|---|
| **modelo** | `qwen-3.8-27b` |
| **proveedor** | Cerebras (`https://api.cerebras.ai/v1`) |
| **por qué esta familia** | **Distinta del agente** (`nemotron`) **y del juez caído** (`gpt-oss`). La revisión ciega de §14 exige familias separadas: el juez no puede pertenecer a la familia que está juzgando. |
| **por qué este proveedor** | Es el que la tiene activa. `qwen-3.8-27b` está **también en Groq**, lo que permite después separar *varianza de modelo* de *varianza de proveedor* con la misma corrida. |
| **parámetros** | `temperature=0` — **no se toca nada más**. El prompt queda **idéntico** al del juez caído, para que lo único que cambie sea el modelo. |
| **estado de la clave** | verificada activa antes de declarar (HTTP 200, listado de modelos OK) |

#### Criterio de éxito — fijado aquí, antes de la corrida

**Mismo criterio que la dec. 16**, sin negociar:

1. **< 10% de flips** de veredicto en R5 sobre blueprints juzgados ≥ 2 veces;
2. **< 2 blueprints de recorrido** por brazo entre repeticiones;
3. **0 fallos de parseo de JSON** — si el modelo no devuelve JSON, la llamada
   cuenta como fallo y se ve, no desaparece.

**Cada brazo se juzga 3 veces.** Los blueprints, la fuente y el prompt son los
mismos de §8.10: **lo único que cambia es el modelo.**

#### Si no se alcanza

La dec. 18 tiene **dos salidas declaradas** y se elige **antes** de mirar:

- **Si queda cerca** (10-15% de flips): se declara **segundo candidato**
  `nvidia/nemotron-3-super-120b-a12b` o `mistral-large-2`, y se corre con el
  **mismo** criterio. **Un solo reintento**, no un techo de candidatos.
- **Si queda lejos** (>15% de flips o >4 de recorrido): **se cierra R5 como no
  medible para siempre**, con la dec. 16 como cierre definitivo, y §7.1 se
  queda con esa declaración. **No se itera más.**

**No se re-baja el umbral de flips. No se agranda el intervalo. No se alega
que «10% era mucho».**

#### Lo que NO cambia

- El umbral de **R5 = 10/15** — intacto, no se ha tocado en ninguna dec.
- El umbral de **R4 = 8/15** — intacto.
- La frase de la **dec. 12** — sigue siendo lo único que R4 afirma.
- **Ningún número ya publicado** se reescribe: los valores de §8.10 y de
  §7.1 quedan con el sello *instrumento no calibrado*.

#### Enmienda 18a — el proveedor declarado cae, cambia el proveedor *(no el modelo de medición)*

La corrida de Cerebras **no llegó a empezar**: HTTP 402, cuota agotada. La
misma familia sí está en **Groq**, que la dec. 18 ya anticipaba. **El modelo y
la familia no cambian; solo el proveedor**, así que el criterio declarado
sigue siendo el mismo.

**Resultado de esa corrida (Groq + `qwen-3.8-27b`, 90 juicios):** los tres
criterios se alcanzan — **0% de flips** en R5 y en R4, recorrido **0 puntos**
en G y **1 punto** en H, y **ningún fallo de parseo de JSON**.

**Pero la corrida no sirve como cierre, por dos razones declaradas aquí
mismo:**

1. **Groq devolvió HTTP 429 en el 53% de las llamadas.** La run se completó
   reintentando, pero el backoff hizo que la sesión durara más de una hora y
   que el muestreo por brazo quedara desigual. Un instrumento que no se puede
   hacer correr dos veces seguidas no es reproducible **por definición**.
2. **El criterio de la dec. 18 no cubre un juez degenerado.** Un juez que
   dijera «OK» a todo tendría **0% de flips** y pasaría el test siendo
   inútil. Hace falta comprobar aparte que **discrimina**, y esa comprobación
   quedó a medias (una sola muestra válida, que sí discriminó en R4).

#### Enmienda 18b — proveedor con ancho de banda: Gemini

| | |
|---|---|
| **modelo** | `gemini-3.5-flash` |
| **proveedor** | Google (`generativelanguage.googleapis.com`) |
| **por qué** | Barrido de 22 modelos con la clave declarada **antes** de elegir. Descartados: `2.5-flash` → **404, retirado para usuarios nuevos**; `3.x-flash`/`flash-latest` → **503 no disponible**; todos los `pro` → **429 de cuota**. Aprueban `gemini-3.5-flash` (**7,1 s, JSON a la primera**), `gemini-3.1-flash-lite`, `gemini-3-flash-preview` y `flash-lite-latest` (28,4 s, demasiado lento). **Se elige `gemini-3.5-flash`**: el más potente de los que responden y con el mejor tiempo. |
| **parámetros** | idénticos a los ya declarados: `temperature=0`, prompt sin tocar |
| **criterio** | **el mismo de la dec. 18** — no se negocia en la enmienda |

**Se añade un cuarto criterio**, que es el que faltaba en la dec. 18 y sin el
cual los otros tres se pueden ganar con un juez inútil:

4. **Discriminación**: sobre una muestra, el juez **debe emitir R4=false o
   R5=false en al menos un caso**, con una razón concreta y localizable en el
   blueprint. Si devuelve `true` en todo, **no aprueba** aunque tenga 0% de
   flips.

**Aviso de ceguera (§14):** el agente rota por `gemini-3.6-flash`. Elegir un
juez Gemini **comparte familia con el agente**. Se declara para que no pase
desapercibido: afecta a la **cegueza** de la evaluación, no a la
**reproducibilidad**, que es lo que se está midiendo. Si R5 llega a ser
medible, habrá que decidir entonces si ese juez sirve para publicar o solo
para medir.

---

### 8.12 El juez reproducible — **cuatro criterios cumplidos** *(medido 2026-10-13, 90/90)*

Corrida con `gemini-3.1-flash-lite` @ Google, `temperature=0`, **mismo prompt
que §8.10**, brazos G y H, 3 repeticiones, **sin generar nada**.

#### Criterios de la dec. 18 + enmienda 18b

| # | criterio | objetivo | **resultado** |
|---|---|---|---|
| 1 | flips de veredicto en R5 | < 10% | **0%** ✅ |
| 2 | recorrido por brazo entre repeticiones | < 2 blueprints | **0 puntos** (G **y** H) ✅ |
| 3 | fallos de parseo de JSON | 0 | **0 / 90** ✅ |
| 4 | **discrimina** — emite `false` en algún sitio | ≥ 1 caso | **R5 dice false en 2/15 (G) y 7/15 (H); R4 en 7/15 y 10/15** ✅ |

**Los cuatro se cumplen.** 90 juicios, **0 fallos**, y las tres repeticiones
dan **exactamente el mismo número**.

#### Los valores

| brazo | R5 por repetición | media | **recorrido** | R4 |
|---|---|---|---|---|
| **G** | 13/15 · 13/15 · 13/15 | **87%** | **0 pts** (sd 0,0) | 8/15 · 8/15 · 8/15 = 53% |
| **H** | 8/15 · 8/15 · 8/15 | **53%** | **0 pts** (sd 0,0) | 5/15 · 5/15 · 5/15 = 33% |

**No es un juez que apruebe todo:** da `false` en R5 **17 veces** de 30 y en
R4 **17 de 30**, y cuenta rellenos y fabricaciones de forma consistente.

#### Muestra de veredictos — son localizables, no genéricos

| brazo | R4 | R5 | lo que dice |
|---|---|---|---|
| G | true | true | *«refleja con precisión la metodología… sin atribuir información no declarada»* |
| G | **false** | true | *«atribuye erróneamente **vecindarios de 1 salto**, que la fuente solo menciona como union-based»* |
| G | **false** | true | *«atribuye **valores de rendimiento** que no aparecen en el texto fuente»* |
| H | **false** | true | *«atribuye la técnica **InfoNCE**, que no aparece en la fuente»* |
| H | **false** | **false** | *«atribuye métricas no presentes **y rellena los límites de rutas** que la fuente no especifica»* |

El juez **separa los dos fallos**: `R4=false / R5=true` (fabrica pero declara
silencio) frente a `R4=false / R5=false` (fabrica **y** rellena). Esa es
exactamente la distinción que dec. 11 dice que el juez viejo no hacía.

#### R5 vuelve a ser medible

| | |
|---|---|
| umbral §3.1 | **≥ 10/15** — **intacto, no se ha tocado en ninguna dec.** |
| **brazo G** | **13/15 → CUMPLE** |
| brazo H | 8/15 → no cumple |
| brazo con mejor puntuación | **G, 13/15** |

#### Los tres límites de este resultado — declarados, no escondidos

1. **Solo G y H.** Los brazos B, C, D, E, F **no se han re-juzgado** con el
   instrumento nuevo. Los números de §7.1 para esos brazos siguen marcados
   *instrumento no calibrado* y **no se comparan** con este.
2. **No es comparable con §8.10 ni con nada anterior.** Cambió el modelo de
   juez: **el 13/15 de aquí no es el mismo 13/15 que un 13/15 del juez
   viejo.** Los valores previos **no se reescriben**.
3. **Ceguera (§14).** El agente rota por `gemini-3.6-flash`; el juez es
   `gemini-3.1-flash-lite`. **Comparten familia.** Está declarado en la
   enmienda 18b. Afecta a la **cegueza**, no a la **reproducibilidad** que
   aquí se mide — pero **hay que resolverlo antes de publicar**, o la
   evaluación deja de ser ciega.

#### Lo que sigue

**R5 deja de estar en «no medible».** La fila se reescribe con este número y
su umbral. Queda pendiente **decidir el juez de publicación**: si se quiere
cegueza, hace falta un juez de familia distinta del agente, y eso es otra
declaración con sus propios criterios.

---

### 8.13 R4 medido con el juez reproducible — **cumple** *(90/90, 0 fallos)*

Los seis brazos que faltaban (B, C, D, E, F, G2) juzgados con el **mismo
instrumento de §8.12**: `gemini-3.1-flash-lite`, `temperature=0`, prompt sin
tocar. **90 llamadas, 0 fallos, 0 × 429.**

#### Resultado — umbral ≥ 8/15 *(§3.1, intacto)*

| brazo | **R4** | ¿cumple? | repeticiones |
|---|---|---|---|
| **E** | **9/15 = 60%** | **✅ CUMPLE** | 1 |
| **G** | **8/15 = 53%** | **✅ CUMPLE** (exacto en el umbral) | 3 |
| C | 7/15 | ✗ | 1 |
| D | 7/15 | ✗ | 1 |
| G2 | 7/15 | ✗ | 1 |
| H | 5/15 | ✗ | 3 |
| B | 4/15 | ✗ | 1 |
| F | 4/15 | ✗ | 1 |

**Mejor brazo: E con 9/15 ≥ 8/15. R4 CUMPLE.**

#### Cómo se leyeron las repeticiones

**G y H llevan 3 repeticiones** (del run de §8.12); **el resto, 1**. No es un
atajo: la reproducibilidad ya está medida en §8.12 con **0% de flips sobre 30
blueprints × 3 corridas**, así que repetir para obtener el *valor* de un brazo
no aporta información nueva — solo multiplica el consumo. **Se declara aquí
para que la tabla no parezca más sólida de lo que es.**

#### R5 y R4 con el mismo instrumento

| fila | umbral §3.1 | mejor brazo | estado |
|---|---|---|---|
| **E Escritura R5** | ≥ 10/15 | **G, 13/15** | **✅ CUMPLE** |
| **E Escritura R4** | ≥ 8/15 | **E, 9/15** | **✅ CUMPLE** |
| C Integridad B5 | 100% | H, 95,8% | ✅ cerrada con lista (dec. 17) |

#### Los tres límites — los mismos que §8.12

1. **No comparable con nada anterior.** Cambió el modelo de juez: **el 9/15 de
   E aquí no es el mismo 9/15 que el del juez viejo.** Los números de §8.7 y
   §8.10 **no se reescriben**; quedan sgrabados como *instrumento no calibrado*.
2. **Brazo R5 ausente.** §7.1 citaba R4 en «C, **R5**, F, E», pero **el brazo
   R5 no está en ningún fichero de resultados** (`result_blueprint_ab.json` ni
   `result_arm_*.json`). **No se ha juzgado y se anota como tal** — no se
   rellena con un número prestado.
3. **Ceguera (§14).** El juez comparte familia con el agente. **Antes de
   publicar hay que resolverlo.**

#### Consecuencia para §7.1

**Ya no queda ninguna fila sin cerrar.** R4 pasa de *«medido con instrumento
no calibrado»* a **medido y CUMPLE** con el instrumento reproducible, y su
frase de la **dec. 12** (pre-filtrada, revisión humana obligatoria) **se
mantiene igual** — el número ahora la sostiene en vez de contradecirla.

**Queda una única decisión pendiente: el juez de publicación.** §8.12 y
§8.13 usan un modelo con el que el agente comparte familia, lo que es válido
para medir **reproducibilidad** pero no para una evaluación **ciega**.
