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

Umbrales propuestos (a confirmar): suelo en **B1-B4 = 100%** y
`judge_mean >= 4.0` en Q1-Q3. El 4.0 es mas bajo que el 4.50 del Hito 1
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

## 5. Lo que decide el responsable antes de medir

1. **B5 — ¿citas `[doc:chunk]` en los blueprints?** Es lo que separa un
   blueprint verificable de uno que suena bien. Anadirlo cambia el prompt, asi
   que obliga a re-medir, como el Hito 0. **H3 lo vuelve urgente**: sin citas,
   H2 es indetectable por diseño.
2. **`max_tokens=1500` no alcanza** (H1). Subirlo cambia la salida, asi que hay
   que elegir el valor **antes** de la primera run de medicion, no despues —
   igual que se hizo con la temperatura en el Hito 1. B6 detecta el corte pero
   no lo evita.
3. **Umbrales**: suelo 100% en B1-B6 y juez 4.0 en Q1-Q3. ¿o se sube?
4. **El fallback silencioso del 1.1** (tecnica inexistente -> todas las
   tecnicas): B3 lo detecta. **H5 anade que hoy lo salva el modelo, no el
   codigo** — se puede arreglar como bug, o declarar que se confia en esa
   negativa y medirla. Lo que no se puede es no decidirlo.
5. **Referencias escritas por quien**: sin eso, Q1 es el unico juez de
   fidelidad y es exactamente lo debil.
6. **H2, el problema de fondo**: un blueprint que contradice `REPORT_COEVOLVE.md`
   sin que nada lo señale. No hay umbral que lo arregle — es el motivo por el
   que §3.3 (referencias a mano) deja de ser opcional y pasa a ser **el
   trabajo del Hito 2**.

---

## 6. Como se sabra que Hito 2 esta cerrado

La misma estructura: tabla *criterio / umbral / medido* con el valor real de la
run final, coste real en tokens, y la seccion de erratas si algo resulta estar
mal medido. Y **el suelo mecanico se declara ANTES de la primera run**, no
despues de ver los numeros.
