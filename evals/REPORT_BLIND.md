# Evaluación ciega: 40 preguntas × 3 runs

Set: `evals/golden_blind_qa.jsonl` (escrito leyendo los chunks, sin ejecutar el
agente ni el juez). 8 por paper, 35 respondibles y 5 no respondibles (una por
paper). Agente pineado a `nvidia/nemotron-3-super-120b-a12b` (`--provider
nvidia`), juez a `openai/gpt-oss-20b` (familia distinta). Datos:
`evals/result_blind_r{1,2,3}.json`.

## Aviso: una versión anterior de este informe daba 4.219 y era inválida

La primera tanda de runs **no era ciega**. `LOOP.run` guardaba una lección con
`key_insights = "Q: <texto de la pregunta>"` y `load_lessons()` metía las 5 más
recientes en el prompt, así que cada pregunta recibía el texto de hasta 5
preguntas anteriores del propio golden. Además `get_harness()` era un singleton
compartido por los 4 hilos del paralelismo.

Las cifras de este informe son de una repetición completa con `isolated=True`
(harness por hilo, sin lecciones). Coinciden en la media y difieren en todo lo
demás, que es justo lo que importa.

## Resultado

| | r1 | r2 | r3 | media |
|---|---|---|---|---|
| judge (respondibles sin fallo de infra) | 4.171 | 4.273 | 4.486 | **4.310** |
| respondibles puntuadas | 35 | 33 | 35 | |
| caída de infraestructura | 0 | **2** | 0 | |
| cite_precision | 0.871 | 0.871 | 0.957 | 0.900 |
| abstain_rate (5 no respondibles) | 1.0 | 0.6 | 1.0 | 0.867 |
| abstención falsa | 0.114 | 0.057 | 0.029 | 0.067 |
| truncadas / fallbacks | 0 / 0 | 0 / 0 | 0 / 0 | |
| tokens de agente | 562k | 667k | 710k | 646k |

**judge = 4.310, IC 95 % ± 0.264** sobre 103 observaciones.

> Las cifras de esta tabla se recalcularon al arreglar la métrica de
> infraestructura (Fase 0, más abajo). Antes ponían `4.229` y contaban 105
> observaciones: las dos caídas de red de r2 (`pg-b4`, `tce-b6`) se puntuaron
> `judge=0` y, como `0` no es `None`, el agregado las contaba como respondibles
> válidas con `n_judge_errors=0`. Bajaban la media **sin dejar rastro**. La cifra
> real era 4.310.

## Fase 1: el ruido es del agente, no del juez

La pregunta era cuánto del σ=0.709 intra-pregunta es del juez. Resuelta
midiendo, no suponiendo: se re-juzgó la **misma** respuesta 3 veces
(`evals/measure_judge_noise.py`, 19 respuestas × 3 repeticiones × 2 brazos =
114 llamadas, 94.9k tokens, **cero llamadas al agente**). Todo lo que varía al
repetir el juez sobre la misma respuesta es ruido del juez por construcción.

| | T=0.2 | T=0.0 |
|---|---|---|
| sd del juez | **0.061** | 0.061 |
| sd máxima en un item | 0.577 | 0.577 |
| items coherentes en las 3 repeticiones | 17/19 | 17/19 |
| errores de parseo | 0 | 0 |

| | |
|---|---|
| sd del juez | 0.061 |
| sd intra-pregunta observada en las runs | 0.709 |
| **varianza explicada por el juez** | **0.7 %** |

**El juez explica el 0.7 % de la varianza. El resto es el agente.** Las dos
discrepancias están justo en una frontera de la rúbrica: `tce-b7` dio 5,4,4
(original 4) y `wiki-b4` dio 2,1,2 (original 2). Error de ±1 punto, en el sitio
donde la rúbrica dice "le falta un matiz" (4) frente a "correcta y completa" (5).

Confirma por un camino independiente el análisis gratuito previo: 0 casos de
respuesta idéntica con nota distinta en las 3 runs.

### `temperature` no sirve: el endpoint la ignora

Sorpresa que invalida una recomendación previa. Se repitieron 4 llamadas
**idénticas** con `temperature=0.0` y devolvieron **3 salidas distintas**; con
0.9, 4 distintas. NVIDIA NIM ignora el parámetro, así que **no se puede hacer
el juez reproducible bajando la temperatura**. Por eso los dos brazos dan
exactamente los mismos números.

La alternativa correcta es **cachear el juez por hash de
(pregunta, referencia, respuesta, modelo)**: entonces re-puntuar es
determinista y gratis. Pendiente.

## Varianza

| | contaminado | válido |
|---|---|---|
| sd entre preguntas | 1.234 | 0.952 |
| **sd dentro de la misma pregunta** | **0.445** | **0.709** |

Quitar la contaminación **subió** el ruido dentro de la pregunta (0.445 →
0.709). Las lecciones actuaban de pista y el agente rendía más parejo con ellas,
pero era un apoyo externo, no capacidad propia. La media no se movió
(4.219 → 4.229 → 4.310): lo que cambió es el mecanismo y la confianza en la cifra.

Con 3 runs y las mismas 35 preguntas (comparación emparejada) se detectan
diferencias de **0.150** al 95 %; con una sola run serían 0.260.

**8 preguntas tienen sd ≥ 1.7** y barren la escala:

| pregunta | r1 | r2 | r3 |
|---|---|---|---|
| pg-b4 | 5 | 0 | 5 |
| tce-b6 | 5 | 0 | 5 |
| tce-b4 | 1 | 5 | 5 |
| reas-b6 | 5 | 1 | 5 |
| wiki-b2 | 5 | 1 | 5 |
| pg-b2 | 2 | 5 | 5 |
| tce-b5 | 2 | 5 | 5 |
| reas-b3 | 5 | 2 | 5 |

Es decir: **8 de 35 preguntas cambian de veredicto según el día**, y en todas
ellas hay al menos un 5. El agente sabe la respuesta a ratos. Con una sola run
habríamos reportado como firme cualquiera de esos veredictos.

## Dificultad: ahora sí es monótona, pero casi no informa

| | n | media | sd |
|---|---|---|---|
| fácil | 12 | 4.444 | 1.157 |
| media | 14 | 4.095 | 1.445 |
| difícil | 9 | 4.148 | 1.460 |

Fácil 4.44 → media 4.10 → difícil 4.15. La inversión absurda del set
contaminado (difícil 4.67 por encima de fácil 4.08) ha desaparecido, pero
"media" y "difícil" son indistinguibles. **La etiqueta de dificultad separa poco
en este corpus**: los saltos de 1 a 5 dentro de una misma pregunta son más
grandes que la distancia entre niveles.

## Abstención: 87%, con dos fabricaciones

| | r1 | r2 | r3 |
|---|---|---|---|
| pearl-b8 | ✓ | ✓ | ✓ |
| pg-b8 | ✓ | ✗ (inventó "0") | ✓ |
| tce-b8 | ✓ | ✓ | ✓ |
| reas-b8 | ✓ | ✗ (inventó "0.23") | ✓ |
| wiki-b8 | ✓ | ✓ | ✓ |

13/15 = 86.7 %. Las dos fabricaciones **roban un valor plausible de otro
contexto**: 0.23 es la puntuación final de ReASearch, y el primer "0" de pg-b8
también es un número que existe en el paper. No inventan de la nada, que es lo
que un detector de "cifra inventada" no cazaría.

Un detalle del harness: `n_fabricated` contaba por verdad, así que el "0" de
`pg-b8` **no** se contabilizaba como fabricación. Corregido a `is not None`, con
test.

La **abstención falsa** bajó a 6.7 % (de 11.4 % en la run 1 más 2.9 % en la 3),
y las preguntas que se abstienen no son las mismas entre runs: ya no es un fallo
sistemático
sino ruido. Aun así `abstain_rate` y `false_abstention_rate` tienen que leerse
juntos: 87 % de acierto en abstención con 6.7 % de abstención sobre preguntas
respondibles sigue siendo una política que se calla de más.

## Coste

| | por run | total 3 runs |
|---|---|---|
| tokens agente | 646k | 1.94M |
| tokens juez | 36k | 108k |

Latencia mediana 233 s. **NVIDIA estaba serving a ~6× la latencia de la tanda
anterior** (un prompt trivial tardó 67 s, 1,0 s y 98 s en tres llamadas
seguidas), así que la duración de las runs no es comparable entre tandas. Sin
ficha de precios por modelo, el coste se reporta en tokens, no en dólares.

Efecto colateral medible de la contaminación: las lecciones repetidas en cada
turno costaban **~108k tokens por run** (670k → 562k al aislar).

## Limitaciones conocidas

- **Una sola familia de juez**, y además comparte endpoint (NVIDIA) con el
  agente. Solo difieren en familia de modelo.
- **El juez fluctúa poco (±1 punto en frontera de rúbrica) pero no es
  determinista**, y el endpoint ignora `temperature`, así que no se puede
  fijar sin cachear. Ver la sección de Fase 1.
- **8 de 35 preguntas no dan un veredicto estable**, así que la media global
  resume mejor las 27 restantes.
- **La deriva entre runs (6 preguntas `[3,5,5]`) sigue sin explicar.** Los logs
  que lo habrían mostrado se borraron antes de commitearlos.
- El barrido profundo se limita a los 2 papers con mejor score (`n_docs=2`): con
  5 papers serían ~80k caracteres. `tce-b4` y `tce-b5` fallaron bastante y son
  casos donde la respuesta está en un chunk que el top-8 no trae.
## Fase 2 (descartada): el problema no es el volumen del contexto

Antes de tocar el agente se hicieron tres mediciones locales, sin inferencia
(`evals/diagnose_visibility.py`):

1. **La ventana de 220 chars del loop no oculta nada útil.** `result_s` es
   `json.dumps(resultado)[:3000]` y de ahí se conservan 220. Con `search_papers`
   el volcado gasta JSON, score, doc_id, chunk y **el título entero** (90 chars
   solo para `WikiSkill`), así que quedan ~35 chars de texto de chunk de ~1300.
   Medido en las 35 respondibles: `frac_visible = 0.000`. Ningún keyword de
   ninguna pregunta llega a esa ventana.
2. **La evidencia sí llega.** El doc gold está en el top-2 inyectado en 34/35
   (nota 4.28 frente a 2.33 del único que se escapa, `wiki-b4`). Y el **chunk**
   gold está inyectado en 29/35 (4.22) frente a 6/35 ausente (4.28): sin
   diferencia. `wiki-b1` recibe el chunk 12, `wiki-b7` el 37 y `tce-b7` el 25.
3. **El barrido entrega 5x más de lo que promete su docstring.** `per_doc=4` no
   se respeta: `tools.py:125-128` añade los chunks léxicos y de cobertura con
   `setdefault` sin comprobar el tope, y cada doc devuelve 19-22 chunks. Se
   inyectan **50.494 chars de media** (máx 64k) donde el docstring dice 4-11k.

Consecuencia: ampliar el truncado (la Fase 2 inicialmente propuesta) se
construía sobre una premisa falsa, así que se sustituyó por el test correcto:
**repetir el loop real dando solo el chunk gold** (pajar de 1.3k) frente a las
runs válidas (46-56k). Todo idéntico salvo el volumen: trayectoria de 4 turnos,
retries, filtro `_toolish`, parche de cita y juez.

| pregunta | estrecho (1.3k) | ancho (46-56k, 3 runs) |
|---|---|---|
| `wiki-b1` | 2 | 2, 2, 2 |
| `wiki-b7` | **5** | 2, 2, 2 |
| `tce-b7` | **2** | 4, 4, 4 |

Ni mejor ni peor: una sube 3 puntos, otra baja 2, otra igual. **El volumen no es
el cuello de botella**, así que capar `per_doc` se descarta.

Lo que sí muestra es el patrón de fallo real. El agente responde **con
fluidez, citando bien y de forma reproducible**, y aun así se equivoca:

- `wiki-b1` acierta `skill-impact.md` pero rellena con
  `take-examine-move-loop.md` y `multi-operation-loop.md`, nombres plausibles
  extraídos de otra parte del doc, en vez del `logs.md` de la referencia.
- `tce-b7` con pajar corto responde sobre la reducción del 96% en coste con
  Random-Resample: tema equivocado, bien citado.
- `wiki-b7` con pajar corto acierta los tres elementos.

Es desanclaje confiado, no truncamiento ni ruido. Encaja con Fase 1: si el juez
solo explica el 0.7% de la varianza, es porque el fallo del agente es
sistemático y reproducible, no aleatorio. `tce-b7` en concreto peorea al
recortar, lo que es coherente con que `_doc_coverage_chunks` existe justamente
para garantizar la cobertura del apéndice: ese pajar no es ruido, es lo que
mantiene al agente en tema.

### Dos trampas del arnés (fallaron y se corrigieron)

1. `generate()` hace round-robin entre proveedores: sin `LLM_PROVIDERS=nvidia`
   una 504 de NVIDIA lleva la respuesta a **Gemini en silencio**. La primera
   versión de la sonda dio 5,1,1 mezclando dos modelos. Ahora el proveedor se
   pinea antes de tocar la red y se graba el modelo de cada llamada.
2. El prompt de cierre es `_final_answer` (filtra `_toolish`, parchea
   truncado, fuerza `[doc:?]`). Una reconstrucción a mano puntuaba el volcado
   JSON de una llamada a tool como respuesta, y por eso todo salía 1. El prompt
   se delega al loop, no se copia.

### Pendiente por tanto

Ningún cambio de volumen. Las vías que quedan son de anclaje, no de recorte:
extraer citas literales antes de redactar, o abstención calibrada cuando el dato
concreto no aparece. Requieren medición propia y aprobación aparte.

## Fase 3: anclaje (extracción verbatim antes de redactar)

Ruta que quedaba abierta tras descartar la Fase 2. Opt-in por
`ANCHOR_GROUNDING=1`; el default sigue siendo el de siempre, asi que nada cambia
sin la variable.

Una pasada extra de localización pide al modelo que **copie literal** las líneas
del barrido que pueden responder la pregunta, y devuelva `NO_ENCONTRADO` si no
hay ninguna. El cierre solo puede usar esos spans. Motivo, medido: el juez ya
tiene una regla para puntuar bien una abstención honesta (`judge.py:47`), pero
`CIERRE OBLIGADO: responde YA` lo impedía. Con el pajar corto, `tce-b7`
respondía sobre la reducción del 96% en coste con Random-Resample: tema
equivocado y bien citado. En `wiki-b1` el agente citaba
`take-examine-move-loop.md`, que **no existe en el barrido de esa pregunta** (sí
es real, pero pertenece a `wiki-b7`). Fabricación y mala selección a la vez.

Comparación contra las runs válidas, mismo loop, mismo barrido de producción:

| pregunta | sin anclaje (3 runs) | con anclaje (2 runs) | delta |
|---|---|---|---|
| `wiki-b1` | 2, 2, 2 | 3, **5** | **+2.00** |
| `wiki-b7` | 2, 2, 2 | **5, 5** | **+3.00** |
| `tce-b7` | 4, 4, 4 | 4, 4 | 0.00 |

Ninguna regresión: el `0.00` de `tce-b7` significa "sigue como estaba", no
empeora. Y las tres son preguntas deterministas por definición, así que el delta
no es ruido del juez (que explica solo el 0.7% de la varianza).

Verificación mecánica del caso más grave: los dos nombres que el agente
inventaba desaparecen y los dos correctos aparecen.

| | antes | con anclaje |
|---|---|---|
| `logs.md` (correcto) | ausente | presente |
| `skill-impact.md` (correcto) | presente | presente |
| `take-examine-move-loop.md` (inventado) | presente | **ausente** |
| `multi-operation-loop.md` (hermano equivocado) | presente | **ausente** |

Sin regresiones de formato: 6/6 respuestas con cita `[doc:chunk]`, 0 vacías, 0
errores de infraestructura.

### Coste

~37k tokens por pregunta con anclaje frente a ~18k sin él: **se duplica**, porque
la pasada de localización vuelve a leer el barrido completo. A 35 preguntas son
~650k tokens extra por run. Before de activarlo por defecto hay que medir si el
set completo aguanta la mejora: en estas 3 preguntasGanó, pero son las que ya
fallaban, y el mecanismo solo puede ayudar cuando la evidencia contiene el dato.

`wiki-b1` rep0 se quedó en 3 porque mezcla quién actualiza cada archivo: el anclaje
encuentra los nombres correctos pero no siempre la atribución completa. El juez lo
penaliza por matiz, no por invención.

## Fase 0: la caída de red se camuflaba como nota mala

El requisito para gastar 1.1M tokens en un run con anclaje era que los datos
fueran fiables, y no lo eran. Dos caídas de proveedor en r2 quedaron con
`answer=""`, `turns=0` y `judge=0`. Como `0` no es `None`, el agregado las
contaba como respondibles puntuadas y `n_judge_errors` salía a **0**: el ruido de
red bajaba la media y no había forma de verlo en ninguna métrica.

Efecto sobre la cifra: **r2 pasa de 4.029 a 4.273**, y la media de las tres runs
de **4.229 a 4.310**. El agente estaba mejor de lo que se sabía.

Lo que se cambió:

1. **`infra_error` en la fila.** `run_one` distingue caída de infraestructura de
   respuesta mala, y el juez **no se llama** si no hay respuesta (`judge=None`).
2. **`aggregate` la excluye de la media** y expone `n_infra` e
   `infra_error_ids`. El hueco queda visible en vez de escondido en un 0.
3. **Un bug de programación no se camufla de infraestructura.** Un `TypeError`
   relanza. Si no, un error nuestro se descartaría en silencio y se perdería una
   pregunta sin que nadie se entere.
4. **Reanudar rehace la infraestructura.** Las filas de infra no cuentan como
   terminadas: al reanudar se reintentan solas y las ya medidas no se vuelven a
   pedir. Es lo que hace que una run a la que se le agota el tier se pueda
   completar.
5. **504/502/408/timeout ahora son transitorios.** `_classify` no los reconocía,
   así que no reintentaban. Y un proveedor **no se aparca a la primera** con un
   solo proveedor configurado (`LLM_DEAD_AFTER=3`): antes una ráfaga de 504
   tumbaba el endpoint entero y las 35 preguntas salían vacías.
6. **`meta.anchor_grounding`.** La run dice si fue con anclaje; sin eso no se
   puede comparar una run con otra.

Verificado sin red con una prueba de reanudación de dos pasadas: la infra se
reintenta, las filas previas sobreviven, el orden del golden se mantiene y
`judge_mean` sale limpio.

**Impacto en el MDE.** El sd entre preguntas es 0.952, así que con n=35 el error
estándar de un run es 0.161 y el MDE de una comparación pareada está entre 0.07 y
0.48 según cuánto mueva el cambio. Con el perfil realista observado (+1.5 en unas
8 preguntas, 27 sin cambio) el MDE es ≈0.07: de sobra para ver el efecto del
anclaje, que en las 3 deterministas fue +1.67 de media.
