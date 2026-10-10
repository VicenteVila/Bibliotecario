# Hito 0 — que el agente no afirme lo que no tiene

Estado a 2026-10-02; **actualizado el 2026-10-10** con las runs T0 y T0', las
primeras con la temperatura aplicada de verdad, con T0' como replica exacta de
T0, y con las tres runs `promptstop` (64 no respondibles, `golden_blind_qa` y la
**replica** de esta ultima), que bajan la fabricacion de no respondibles a
**0%** y cierran el hito. La seccion "Errata" anula la atribucion de temperatura
de la linea base original. Todos los numeros de aqui son medidos sobre
`evals/golden_abstention.jsonl` (64 no respondibles, 50 de ellas verificadas
por sonda contra el corpus), sobre `evals/golden_blind_qa.jsonl` (35
respondibles + 5 no) y sobre los goldenes de respondibles existentes.

## Errata: la temperatura nunca se aplico

Al cablear el score del harness se encontro que **`--temperature` no llego a
ejecutarse en ninguna run del corpus**. Dos bugs que se tapaban entre ellos:

1. La rama paralela de `main()` hacia `ex.submit(run_one, q, args.turns)` sin
   `**temp_kw`. Todas las runs se lanzaron con `--workers 3..5`, asi que
   `--temperature` solo se registraba en `meta` y no se pasaba.
2. El wrapper `LOOP.generate` de `main()` era `(p, max_tokens, retries)` y no
   aceptaba `temperature`: aunque hubiera viajado, `generate(..., temperature=0.0)`
   reventaba con `TypeError`. El bug 1 impedia que este llegara a ejecutarse nunca.

Consecuencia: los dos brazos del pareado corrieron los dos a **0.2**, el default
del backend (`llm.py:254`). Comparaban 0.2 con 0.2.

Queda **anulado** como efecto de temperatura:

- la tabla 51.6% vs 33.9% (p=0.019). La diferencia entre las dos runs es real en
  las muestras, pero no es de temperatura: o es ruido o es un confundidor no
  medido (presion de tier, hora, reintentos — los logs muestran
  `LLM reintentable nvidia: esperando 30s`);
- "temperatura 0 no reduce la inestabilidad (30% -> 31%)": ambas a 0.2;
- "24 respondibles a temperatura 0" en la regresion: fueron a 0.2.

Lo que **sigue en pie**, porque no depende de la temperatura:

- la fabricacion se mueve **dentro de la misma configuracion**: de 33.9% a
  51.6% entre las dos runs a 0.2, y de 28.1% a 34.4% entre las dos replicadas
  a 0.0. Leido bien, eso es evidencia de inestabilidad, no de una palanca — y
  el abanico se estrecha al bajar la temperatura, que es justo lo que mide la
  seccion de estabilidad;
- el fallo de `_verify_support`: el flag viaja por variable de entorno, no por
  kwarg, asi que si se aplico. 6 items corregidos contra 13 rotos, p=0.17;
- el suelo de ruido: **~200 items pareados a 0.2 y ~122 a 0.0** para un efecto
  de 15pp;
- la regresion de respondibles: 0 abstenciones falsas, 0 degenerados, 0
  truncados, 0 fallbacks.

Los dos bugs estan arreglados y con guardian:
`test_temperature_llega_a_run_one_en_las_dos_ramas` y
`test_wrap_generate_reenvia_temperature`. **La temperatura ya si se mide**: el
2026-10-10 se corrio la suite completa con `--temperature 0.0` aplicado de
verdad (consta ahora en la metadata de `harness_runs`, no solo en el `meta` del
JSON, que es como se colo el bug), y se repitio con un segundo `HEAD`
identico (`T0'`) para poder medir flip.

`--temperature` conserva el default 0.0 porque el protocolo pareado necesita
reproducibilidad (ver el docstring de `loop.generate`). Que bajara la
fabricacion **quedo medido y descartado**: 28.1% frente a 34.4%, z = 0.97. Lo
que si toca es la estabilidad, de 30.6% a 17.7% de flip, con p = 0.093. Ver la
linea base.

## La metrica

Abstencion binaria, no la nota de 1 a 5. Una respuesta que dice "esto no esta en el
corpus" no es un 2: es el comportamiento correcto, y promediarlo con las
respuestas buenas lo penaliza. Por eso vive aparte.

Es la unica cifra del proyecto con ruido de juez practicamente nulo. Matiz que
importa: la decision **si** pasa por un LLM (`judge_abstention`), con lo que la
formulacion original de este apartado era falsa en el razonamiento. Lo que la
sostiene es la medida, no la frase: replicado tres veces sobre las mismas 64
respuestas el juez de abstencion **gira 0/64**, y en el rubrica el juez explica
el **0.7% de la varianza** (`measure_judge_noise.py`, commit `3f339dc`). La
cifra es fiable; el ruido es del agente.

Margen del IC95: **+/-8.2pp** con las dos runs a 0.0 combinadas (n=124) y
+/-11pp con una run suelta (n=64).

## La linea base

| brazo | temperatura REAL | fabrica |
|---|---|---|
| run A (`result_abstention_base`) | 0.2 | 32/62 = 51.6% |
| run B (`result_abst_t0_base`) | 0.2 | 21/62 = 33.9% |
| **run T0 (`result_abst_t0_applied`)** | **0.0** | **18/64 = 28.1%** |
| **run T0' (`result_abst_t0_rep2`)** | **0.0** | **22/64 = 34.4%** |

A y B corrieron a 0.2 por el bug de la Errata. **T0 y T0' son las primeras que
llevan la temperatura aplicada de verdad**, y T0' es una replica exacta de T0:
mismo `HEAD` 17269d1 y **cero cambios de `.py`** entre las dos.

T0: 64/64 decididas, 0 errores de juez, 0 fallbacks, 0 truncados; 2083943 tokens
de agente, 44798 de juez, mediana 52s.
T0': los mismos 64/64 y los mismos ceros; 2086539 tokens de agente (0.1% de
diferencia), 46369 de juez, mediana 56s.

**Estimacion combinada a 0.0: 39/124 = 31.5%, IC95 +/-8.2pp.** Esa es la cifra
contra la que hay que comparar el objetivo, no una de las dos sueltas.

### ¿y la estabilidad? (la medicion que faltaba)

Mismo valor en las dos runs, misma temperatura, mismo codigo: ¿gira?

| par | temperatura real | flip |
|---|---|---|
| **T0 vs T0'** | **0.0** | **11/62 = 17.7%** |
| A vs B | 0.2 | 19/62 = 30.6% |

Sobre los **62 items comunes a las cuatro runs**: el flip baja de 30.6% a 17.7%.
Direccion correcta, **pero p = 0.093, no significativo**. Y la fabricacion entre
las dos runs a 0.0 va de 27.4% a 35.5% (z = 0.97), tampoco significativo.

Lo que deja claro:

- **T=0 no alcanza determinismo**: casi una de cada cinco decisiones sigue
  girando con la temperatura a cero.
- **T=0 no reduce la fabricacion**: 28.1% y 34.4% son la misma cifra.
- El efecto sobre la estabilidad apunta bien (17.7% frente a 30.6%) pero con
  n=62 no se distingue del azar. **Se necesitan mas items, no mas runs.**
- **Los items que giran son practicamente aleatorios**: de los 12 que giran
  entre T0 y T0', solo 3 giran tambien entre A y B, cuando por azar se
  esperarian 3.7. No hay un subconjunto de preguntas inestables al que culpar.

Consecuencia practica: la tasa de discordancia mas baja baja el minimo para
detectar un efecto de 15pp de ~200 a ~122 items pareados. **Sigue sin salirse
del rango en el que una run por brazo no sirve.**

Pareadas contra T0 sobre los items comunes y decididos por ambas:

- **T0 vs A**: 6 fabricaciones nuevas contra 21 perdidas — McNemar exacto
  **p = 0.0059**;
- **T0 vs B**: 7 contra 10 — **p = 0.6291**.

T0 es significativamente mejor que la run A e indistinguible de la run B. Como
A y B se diferencian entre si en 17.5pp, **no se puede separar el efecto de
temperatura del ruido entre brazos**. Con T0' repetido la conclusion se
sostiene: la temperatura toca un poco la estabilidad y la fabricacion en nada.

El piso deja grave a ese punto del analisis: **mas de una de cada cuatro** no
respondibles se fabrica, y a un objetivo de <=5% le faltan ~26pp. Es el estado
que midieron la temperatura y las cinco puertas LLM — **no el final**: al final
del documento esta lo que si lo cambio.

## Lo que no funciona

`_verify_support` (opt-in por VERIFY_SUPPORT=1). En la primera comparacion parecia
funcionar: 51.6% -> 36.5%, p = 0.12. Al repetirla el efecto se dio la vuelta:
6 items corregidos contra 13 rotos, p = 0.17. El -14.5pp anterior era ruido a su
favor. Esta comparacion **si es valida**: el flag se lee de la variable de entorno
al importar el modulo, no via kwarg, asi que llego a aplicarse en las dos runs.

Es la quinta intervencion sin resultado (A, B, C, VERIFY_CITATION y esta). Se
conserva el codigo porque el flag es opt-in y no cuesta nada apagado, pero **no
la pongas por defecto**: el numero medido va al reves.

Por que fallo, que es lo que si se aprende: la puerta comparaba la respuesta
contra la evidencia con un juez que no ve la evidencia. El juez de abstencion
existente (`judge_abstention`) solo recibe pregunta y respuesta, asi que sus
"75% de deteccion" son deteccion de cifras inventadas, no de sustaining de
afirmaciones. `cite_precision` tampoco sirve para esto: daba 1.0 en 3 de las 5
fabricaciones de la primera linea base. En la run T0, con mayor muestra, **11 de
las 18** fabricaciones siguen teniendo `cite_precision = 1.0`. Un gate de citas
se quedaria con 11/64 = 17.2% de fabricacion: descartable, lejos del 5%.

## Una senal nueva: la documentacion ajena

En la run T0, `stray_docs > 0` — el agente cita o recupera documentos que no son
los de la pregunta — predice la fabricacion:

| | fabrica |
|---|---|
| `stray_docs > 0` | **7/11 = 64%** |
| `stray_docs = 0` | 11/53 = 21% |

Fisher exacto **p = 0.0079**, riesgo relativo **3.1x**. El caso tipico es
`pearl-u6`, que responde "as stated in the Evo-Bench paper" en una pregunta de
PEARL: recupera el papel equivocado y de ahi saca el 256000.

Dos cautelas obligatorias:

1. **n=11 expuestos y una sola run.** Con el suelo de ruido de arriba esto es un
   correlato de una run, no una palanca certificada.
2. **La causalidad puede ir al reves.** El que fabrica cita mas lejos; que
   `stray_docs` este en la misma fila no demuestra que sea la causa.

Otra correlacion en el mismo sentido: con `n_evid = 4` se fabrica el
**16/40 = 40%**, con `n_evid = 3` el 1/12, y con `n_evid = 1` el **0/3**.
Recuperar mas trozos no ayuda si los que faltan son los que no existen, y
ampliar el contexto amplia tambien la superficie de la que se puede coger un
numero.

## El ruido, que es donde nos hemos quedado 20 horas

La decision de abstencion era **inestable en el 30%** entre dos runs a 0.2
(nueve de treinta abstenciones correctas se dan la vuelta). Ampliado a las
cuatro runs sobre los 62 items comunes, la cifra queda medida:

| par | temperatura | flip |
|---|---|---|
| A vs B | 0.2 | **19/62 = 30.6%** |
| **T0 vs T0'** | **0.0** | **11/62 = 17.7%** |

La medicion que faltaba ya esta hecha: se corrio la misma pregunta dos veces a
temperatura cero, con el mismo `HEAD` y sin cambios de codigo entre medias.

- **T=0 baja el flip de 30.6% a 17.7%, con p = 0.093.** Ni significativo ni
  prescindible: hay efecto, no hay muestra para afirmarlo.
- **T=0 no da determinismo.** Casi una de cada cinco decisiones sigue girando
  con la temperatura a cero y el codigo identico. La sampling no era la fuente
  unica, ni siquiera la principal.
- **La fabricacion no se mueve**: 28.1% y 34.4% entre replicadas, z = 0.97.
- **El juez descartado**: `measure_judge_noise.py` (commit `3f339dc`) asigna al
  juez el **0.7% de la varianza**; el 99.3% es del agente. Y el juez de
  abstencion, replicado 3 veces sobre las mismas 64 respuestas, **gira 0/64**.
  El ruido es integramente del agente.
- **Los items inestables no existen como grupo**: de los 12 que giran entre T0
  y T0', solo 3 giran tambien entre A y B, cuando por azar serian 3.7. No hay
  un subconjunto de preguntas dificiles al que culpar; la inestabilidad se
  reparte por todo el conjunto.

Consecuencia practice: con un flip del 17.7%, un efecto de 15pp necesita ~122
items pareados en vez de ~200. Baja la factura, **pero no sale del rango en el
que una run por brazo sigue sin servir**. Cualquier palanca futura medida con
una sola run por brazo sigue por debajo del suelo de ruido — que es el motivo
real de los cinco fracasos, mas que la calidad de las palancas.

## El harness ya se puede puntuar

Hasta aqui `harness_runs.score` se escribia `NULL` en las 1121 runs: el loop no
tiene juez, asi que nadie lo rellenaba y no habia forma de saber que run salio
bien. Ahora:

- `RuntimeHarness.record_score()` escribe el score **desde fuera**, en `run_one`,
  que es donde estan el juez y la decision de abstencion. Solo toca la fila de su
  `run_id`, asi que con `--workers 5` no hay carrera.
- `run_score()` normaliza a **0-1** las dos poblaciones: `(judge-1)/4` en
  respondibles, `1.0/0.0` por abstenerse o fabricar en no respondibles, y `None`
  en infraestructura (NULL significa "nadie lo midio", no "fue 0").
- `run_success()` da el booleano por tarea: **`judge >= 4` y cita** en
  respondibles, **`abstained`** en no respondibles.

  El corte en 4 lo fija la rubrica, no la estadistica: un 3 es
  "falta O altera el dato principal pedido", que para un agente de investigacion
  no es un acierto. juez>=3 daria p=0.847 y juez>=2 p=0.971, este ultimo
  saturado (varianza 0.028) y sin nada que elegir para Task-CoEvolve. juez>=4
  da p=0.725, varianza 0.199. La cita se exige porque la rubrica prohibe al juez
  valorarlas: es lo unico que no puede ver, y una respuesta correcta sin
  atribucion no es auditable. Coste medido: 1 run de 313.
- `validation_tasks` y `task_outcomes` por fin se llenan: cada golden se registra
  como tarea (idempotente por `golden_id`) y cada run deja su outcome con
  `harness_run_id`. Antes las dos tablas estaban en 0 y `task_pool` no tenia ni
  un caller, asi que selector y estimator corriran sobre el prior 0.5 vacio.
  Estado tras T0 y T0': **73 tareas, 138 outcomes, 138 runs con score**. Las
  tareas no suben porque los ids ya existian (el registro es idempotente); la
  diferencia de una entre tareas y la primera ronda de outcomes es `pearl-b8`,
  que esta en el set ciego y en la suite de abstencion, asi que se registra una
  sola tarea pero deja dos outcomes. No es un duplicado erroneo — el set ciego
  es mixto por diseno y reutiliza los cinco `-b8`.

**Condicion, no verificacion:** `task_stats` calcula `p̄` *por tarea*. Con
`n=1` por golden, `p̄` es 0 o 1 y la varianza es 0 con cualquier umbral. El
selector solo se vuelve informativo cuando un mismo golden se observa varias
veces. El cableado no sirve de nada si no cambia el habito de lanzar evals.

## Lo que si funciona: quitar la orden de contestar

Las cinco intervenciones anteriores fueron puertas LLM encima de un prompt que
ordenaba fabricar. La causa real estaba en dos lineas que nadie habia revisado:

- `state.py`: *"Maximo 3 llamadas a tools por pregunta; despues responde con lo
  que tengas"* y *"RESPONDE de inmediato"*;
- `loop.py`, `_close_prompt`: *"CIERRE OBLIGADO: responde YA"*, junto a
  *"no inventes cifras que no aparezcan literalmente"*.

Orden contradictorio: responde si o si, pero no inventes. Cuando el dato no
estaba, la unica salida legal era inventar un hermano plausible — el propio
comentario de `_ground` ya lo decia.

### La auditoria previa: no busca mal, da por buena la primera coincidencia

Las 40 fabricaciones de T0 y T0' contra la corpus entera (10 papers, 842 chunks):

| donde esta la cifra dada | T0 | T0' | total |
|---|---|---|---|
| en el paper objetivo, pero no responde la pregunta | 6 | 10 | **16** |
| sin cifras: contesta otro tema | 8 | 9 | **17** |
| solo en otro paper | 3 | 1 | 4 |
| en ninguna parte | 1 | 1 | 2 |
| gold + otro | 0 | 1 | 1 |

Hipotesis descartada: solo 4-5 de 40 son respuestas verdaderas de otro paper.
El caso dominante es que la cifra **si existe en el paper correcto** y no
contesta lo preguntado, o que el agente contesta otro tema sin cifras.

### El cambio

Quitada la orden de contestar y anadida explicitamente la rama de parada: el
objetivo de `STATIC_PROMPT` da la abstencion por valida como tercera respuesta,
y `_close_prompt` pasa de obligado a condicional — si el dato esta literalmente,
responde y cita; si no, declara que no aparece y cierra sin dar ningun dato.

### El resultado

| run | fabricacion |
|---|---|
| T0 | 18/64 = 28.1% |
| T0' | 22/64 = 34.4% |
| **`promptstop`** | **0/64 = 0.0%** |

McNemar exacto: **p = 7.6e-06** contra T0 y **p = 4.8e-07** contra T0'. 18 y 22
corregidas, **0 rotas**: ni una abstencion correcta se perdio ni hubo un giro en
la direccion contraria. 0 errores de juez, 0 truncados, 0 fallbacks, 2101719
tokens. El suelo de ruido (flip 17.7%) habria producido giros en ambas
direcciones; estos son unilaterales.

**Es la primera intervencion con resultado**, y la unica que no anade otra
puerta: quita una orden en vez de meter un verificador.

### La mitad respondible: medida

Se corrio `golden_blind_qa` (35 respondibles + 5 no respondibles) con el mismo
codigo. **El miedo no se cumple**: el prompt no niega en masa.

| | promptstop | su replica | r5 | r6 | r1 |
|---|---|---|---|---|---|
| `judge_mean` | 4.314 | **4.143** | 4.714 | 4.600 | 4.171 |
| `run_score` | 0.825 | **0.787** | 0.912 | 0.887 | 0.819 |
| exito (`run_success`) | 77.5% | 72.5% | 87.5% | 90.0% | 75.0% |
| juez >=4 y con cita | 27/35 | 25/35 | 31/35 | 32/35 | 25/35 |
| abstenciones falsas | 1 (`reas-b2`) | **0** | 0 | 1 | 4 |
| no respondibles abst. | 4/5 | 4/5 | 4/5 | 4/5 | 5/5 |
| fabricadas (`fabricated_value`) | 0 | 1 | 1 | 0 | 0 |
| truncadas | 0 | **2** | 0 | 0 | 0 |
| tokens | 1.16M | 0.90M | 1.13M | 1.13M | 0.56M |

La replica **confirma la direccion y complica el juicio**: 4.143 contra 4.314 de
la original, delta de +0.171 con p = 0.468 — ruido entre dos runs del mismo
sistema, del mismo orden que el +0.114 de r5 contra r6. Los no respondibles se
mantienen: 4/5 abstienen en las dos, y el que se contesta cambia de lado
(`reas-b8` pasa a abstenerse, `wiki-b8` pasa a fabricar), asi que la fabricacion
concreta es 0 y 1, no una tendencia.

Con las dos runs promediadas por pregunta:

| comparacion | delta de juez | p |
|---|---|---|
| **promptstop (2 runs) vs r5** | **-0.486** | **0.014** |
| ... sin las 2 truncadas | -0.424 | 0.036 |
| ... sin `pearl-b5/b6/b7` | -0.359 | 0.069 |
| promptstop (2 runs) vs r6 | -0.371 | 0.106 |
| promptstop (2 runs) vs r1 (la base) | +0.057 | 0.840 |

La regresion contra r5 **es significativa en la especificacion principal y
sobrevive a sacar las 2 respuestas truncadas**, pero no a sacar el cluster
entero de pearl, y **nunca es significativa contra r6**. Contra la base r1 es
indistinguible.

Los tres items que arrastran todo son `pearl-b5`, `pearl-b6` y `pearl-b7`: en la
original sacaron 5, 5 y 5, y en la replica 1, 2 y 1. `pearl-b7` salio ademas
truncado, igual que `pg-b7` (un 3). El resto del descenso es difuso.

Ademas se midio el coste de la otra via, `ANCHOR_GROUNDING`: funciona (smoke
3/3 abstenciones) pero cuesta 64284 tokens/pregunta frente a 32561, casi el
doble (~3.9M la suite). Queda apagado por defecto — con el cambio de prompt no
hizo falta, que es la conclusion util.

## Donde queda

**Hito 0 cerrado: las dos mitades medidas.**

| criterio | umbral | medido |
|---|---|---|
| fabricacion en no respondibles | <=5% | **0%** (0/64) frente a 28.1% y 34.4%, McNemar p <= 4.8e-07 |
| `run_score` | >=0.75 | **1.000** (suite abstencion) y **0.806** (blind, 2 runs; la replica sola, 0.787) |
| juez >=4 con cita en respondibles | - | 52/70 = 74.3% |
| abstenciones falsas | - | 1/70 (solo la original); r5: 0, r6: 1, r1: 4 |
| no respondibles que se abstienen | - | 8/10 (4/5 en cada run) |

Coste de las tres runs: 2.10M + 1.16M + 0.90M = **4.16M**.

**La deuda de respondibles ya esta medida, no pendiente.** El descenso contra r5
es significativo en la especificacion principal (p = 0.014) y sobrevive a sacar
las 2 truncadas (p = 0.036), pero se sostiene sobre tres preguntas de pearl y
**no llega a significancia contra r6** (p = 0.106). Y hay un confundo que
separa: r5 y r6 corrieron a temperatura libre (0.2) y estas a 0.0, ya medida con
efecto pequeno sobre respondibles.

Lectura honesta: **Hito 0 pasa sus umbrales** — fabricacion 0% y run_score 0.806
>= 0.75 — pero el cambio que arreglo la fabricacion **cuesta puntos en la mitad
respondible**, y el precio no esta aislado del efecto temperatura. No es una
mejora gratis.

Los puntos 1 y 2 que estaban escritos aqui (veto de `stray_docs` y
verificacion determinista de cifras) **quedan refutados por preview offline,
sin gastar tokens**. Tres variantes medidas sobre el cache de barridos:

- recortar `_deep_evidence` a 1 doc pierde el paper objetivo en el 47%
  (77% -> 53%) y aun asi deja papers ajenos;
- exigir que la cifra este en la evidencia entera caza 1-2 de 18-22;
- exigir que este solo en el trozo citado caza 7 de 40 (17.5%) pero rompe el
  12% de las respuestas correctas (6 runs, 6.5%-20%).

Mismo motivo que la auditoria: la evidencia esta llena de numeros reales de
papers equivocados, asi que cualquier cifra "se verifica" sola, y al recortar
para arreglarlo se pierde el paper bueno.

Pendiente, en orden:

1. **Trazabilidad de la run** (domino 4, "deliberate diagnosis,
   verification"): seedear el primer turno o grabar y reproducir cada paso.
   Un agente cuyo primer turno diverge no puede pararse a si mismo a partir de
   la evidencia. Sigue sin existir.
2. **Ampliar la suite a n>=122** solo si alguna palanca futura se espera
   pequena. Para efectos grandes como el de ahora, n=64 ha bastado con creces.

Hecho y fuera de esta lista:

- **Replica de la run blind** (896816 tokens): medida arriba. Confirma la
  direccion del descenso, lo acota a3 preguntas de pearl y no alcanza
  significancia contra r6.
- **Co-evolucion (#4)**: descartada el ciclo en vivo con datos, sin gastar un
  token. Detalle en `evals/REPORT_COEVOLVE.md`.
- **CI (#5)**: en verde en cada push desde `b11fd3b`.


