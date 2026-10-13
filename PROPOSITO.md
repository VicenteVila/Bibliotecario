# Propósito del proyecto

> Documento de navegación. Si en algún momento no sabemos por dónde va el proyecto,
> se vuelve aquí **antes** de decidir. Se modifica solo si cambia el propósito real,
> nunca por conveniencia de un experimento.

---

## 1. El objetivo final

Construir un sistema capaz de **diseñar, crear y evaluar arneses de agentes con el
mejor conocimiento posible** — conocimiento que **crece** a medida que avanza la
ciencia en el dominio de la ingeniería del software y las ciencias de la computación.

No se trata de tener un corpus. Se trata de que **el agente sepa usarlo**.

**El conocimiento entra, se almacena, y tiene que salir por otra parte distinta de
por donde entró.** Si solo puede repetir lo que el paper dice cuando se le pregunta
por ese paper, no está diseñando: está copiando con cita. **Diseñar es aplicar la
idea del paper X al problema Y que X nunca contempló.**

---

## 2. El ciclo

```
   papers ──► memoria ──► diseña arnés ──► evalúa ──► lecciones ──► diseña mejor
     ▲          (crece)       │               │             │
     │                        └─── benchmark ──┘             │
     │                          INMUTABLE                   │
     │                        (nunca se mueve)               │
     └────────────────── la ciencia avanza ──────────────────┘
```

**Dos cosas crecen; una, jamás.**

| capa | qué | regla de vida |
|---|---|---|
| **Corpus** | papers de frontera | **crecer** y filtrarse con rigor |
| **Agente / arneses** | diseña y mejora | **itera** bajo presupuesto |
| **Benchmark** | dice si funciona | **inmutable** — jamás se mueve |

---

## 3. Por qué el benchmark es inmutable

No es buenas práctica: es que **estamos cambiando dos cosas a la vez** — el corpus
y el arnés. Si el benchmark también cambia, **la variación de la nota no se puede
atribuir a ninguna causa**, y entonces no hemos aprendido nada: solo hemos generado
un número.

Además: **un benchmark que el agente ha visto mide memorización, no transferencia.**
Si se mueve o se filtra al iterar, se destruye la distinción *visto / no visto*, que
es exactamente la que hace posible medir si el sistema transfiere.

Si el benchmark tiene que cambiar, se declara como **benchmark nuevo con línea base
nueva**. Nunca en silencio. Nunca mezclando series.

---

## 4. Los tres principios

### 4.1 Estrictura en la ingesta

Lo que entra determina lo que se puede diseñar. Los modos de fallo reales, ya
presentes en la carpeta:

- **duplicado por traducción** — mismo contenido que pesa doble en la recuperación
- **tema equivocado** — ruido que el *retrieval* devuelve como si fuera pertinente
- **preprint sin revisar** — frontera sí, pero no verificado
- **encuesta de encuestas** — sensación de conocimiento sin método nuevo

Una puntuación de calidad **que no puede rechazar no es un filtro, es decoración.**

### 4.2 El camino hasta el diseño tiene que estar entero

**Ingerir ≠ estar disponible.** Cada tramo es un punto ciego:

```
paper ingerido ──► nodo en el grafo ──► consulta ──► blueprint ──► arnés
      │                  │                 │
   calidad            seed            recuperación
   dedup            (¿existe?       (¿llega el
                    ¿está abierto?)  contenido?)
```

**Un corpus lleno con la puerta cerrada es un agente ciego.** Es la situación
durante mucho tiempo: 14 papers sin ingerir, y de los ingeridos, solo 5 sembrados
en el grafo.

### 4.3 Transferencia

| | qué es | cómo se falsifica |
|---|---|---|
| **Recuperar** | dice lo que el paper dice | pregunta directa sobre el paper |
| **Transferir** | aplica la idea donde **el paper no llegó** | pregunta en contexto **distinto** al de aprendizaje |

**Transferencia sin control no se puede medir** — hace falta un grupo que no tuvo
el conocimiento. Y sin benchmark congelado no hay contexto *no visto* que medir.

> Situación conocida: `skills = 0`, `memory_items = 0`, `lessons = 275`.
> La maquinaria existe, está testeada, y **nunca se ha compilado ni una habilidad
> transferible**. Es el mismo patrón que los PFs inertes.

---

## 5. Qué aporta este proyecto que los papers no hacen

| | Evo-Bench | Nosotros |
|---|---|---|
| evolver empieza con | **ninguna literatura** | **el corpus leído** |

**Evolución de arneses guiada por corpus científico.** Ese es el diferencial —
y **solo es defendible si el benchmark es inmutable y sensible a los cambios de
arnés**. Si no, la mejora no es atribuible al corpus y la tesis cae.

---

## 6. De dónde sale el método

**No lo inventamos nosotros — está en `Documentos/`.**

| grupo | papel | papers |
|---|---|---|
| **A** | **cómo se diseña** un arnés | HarnessDev, Harness-of-Harness, RRSI, HARDE, SoL-Pi, Combinación de ramas, Un estudio empírico |
| **B** | **cómo se evalúa** un arnés | **Stop Comparing**, **Evo-Bench**, Evaluación y análisis comparativo |
| **C** | **cómo se mejora** | optimización evolutiva, regularización, auto-mejora con ramas |
| **D** | **qué se mide** | estabilidad, *context drift*, *control lag*, coste, plasticidad |

Hasta ahora solo se usaba el **grupo 1** (contenido de las 5 técnicas sembradas).
Los grupos **A, B, C y D estaban ingeridos como texto plano para QA** — nunca
leídos para extraer método.

**Leerlos antes de codificar.** Es la fase más barata de todas y es lo que
convierte el proyecto de «he construido un agente» en «he construido un agente
con metodología de la literatura».

---

## 7. Anti-objetivos — cómo sabríamos que nos hemos desencaminado

Señales de alarma. Si aparece **una sola**, se frena y se vuelve a este documento:

- ☐ **Re-bajar un umbral** porque la medida no salió bien.
- ☐ **Cambiar el benchmark** para que los números mejoren.
- ☐ **Sembrar/ingestar sin declararlo**, rompiendo la comparabilidad.
- ☐ **Publicar una nota sin la Harness Card** — *«a model score without a harness
  specification is missing part of the experimental condition»*.
- ☐ **Atribuir una mejora al modelo** cuando puede ser del arnés (o del corpus).
- ☐ **Medir sin control** — un solo brazo no demuestra nada.
- ☐ **Iterar contra el set de evaluación** — eso es *teaching to the test*.
- ☐ **Tratar un resultado negativo como bug** en vez de como resultado.
- ☐ **Codificar sin haber leído el paper que lo fundamenta.**

---

## 8. Las preguntas que hay que poder responder siempre

1. **¿Qué mide exactamente este umbral?** — si mide otra cosa, se reencuadra el
   papel del umbral y se deja el valor a la vista. No se re-baja.
2. **¿Este resultado es de benchmark o de diagnóstico de QA?** — hoy, por estándar
   de los papers, **son diagnóstico de QA**: no hay `D^eval`, ni Harness Card,
   ni `Sens(x)`, ni presupuesto, ni bases.
3. **¿El conocimiento llegó al arnés, o solo a la memoria?**
4. **¿Podría el agente hacerlo sin haber leído ese paper?** — si sí, no hubo
   transferencia.
5. **¿El benchmark se movió?** — tiene que ser **no**.

---

## 9. Estado de referencia

| | |
|---|---|
| Disciplina de proyecto | umbrales **antes** de medir · erratas **declaradas** · umbrales **nunca re-bajados** · resultados negativos **se declaran** |
| Juez congelado | `gemini-3.1-flash-lite`, temp 0 — 0% flips, 0 fallos, discrimina (§8.12/§8.13) |
| Benchmark | **pendiente de especificar** → `evals/BENCHMARK_SPEC.md` |
| Hito 2 | cerrado → `evals/HITO2.md` |
| Hito 3 | plan → `evals/HITO3_PLAN.md` *(revisar §7: sembrar el corpus es condición previa, no aplazable)* |
| Corpus | `Documentos/` — 24 ficheros, 63 MB, **en `.gitignore`** |
| Última decisión | *declarar antes de medir* |

---

*Si este documento y una decisión en conflicto, gana este documento. Si este
documento y la realidad están en conflicto, se cambia este documento — pero se
declara, con fecha y motivo.*
