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
| judge (35 respondibles) | 4.171 | 4.029 | 4.486 | **4.229** |
| errores de juez | 0 | 0 | 0 | |
| cite_precision | 0.871 | 0.871 | 0.957 | 0.900 |
| abstain_rate (5 no respondibles) | 1.0 | 0.6 | 1.0 | 0.867 |
| abstención falsa | 0.114 | 0.057 | 0.029 | 0.067 |
| truncadas / fallbacks | 0 / 0 | 0 / 0 | 0 / 0 | |
| tokens de agente | 562k | 667k | 710k | 646k |

**judge = 4.229, IC 95 % ± 0.259** sobre 105 observaciones.

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
(4.219 → 4.229): lo que cambió es el mecanismo y la confianza en la cifra.

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