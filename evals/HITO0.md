# Hito 0 — que el agente no afirme lo que no tiene

Estado a 2026-10-02; **actualizado el 2026-10-10** con la run T0, la primera
con la temperatura aplicada de verdad. La seccion "Errata" anula la atribucion
de temperatura de la linea base original. Todos los numeros de aqui son medidos
sobre `evals/golden_abstention.jsonl` (64 no respondibles, 50 de ellas
verificadas por sonda contra el corpus) y sobre los goldenes de respondibles
existentes.

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

- la fabricacion se mueve **entre 33.9% y 51.6% en runs con la misma
  configuracion**. Leido bien, eso es evidencia de inestabilidad, no de una
  palanca;
- el fallo de `_verify_support`: el flag viaja por variable de entorno, no por
  kwarg, asi que si se aplico. 6 items corregidos contra 13 rotos, p=0.17;
- el suelo de ruido: ~200 items pareados para un efecto de 15pp;
- la regresion de respondibles: 0 abstenciones falsas, 0 degenerados, 0
  truncados, 0 fallbacks.

Los dos bugs estan arreglados y con guardian:
`test_temperature_llega_a_run_one_en_las_dos_ramas` y
`test_wrap_generate_reenvia_temperature`. **La temperatura ya si se mide**: el
2026-10-10 se corrio la suite completa con `--temperature 0.0` aplicado de
verdad (consta ahora en la metadata de `harness_runs`, no solo en el `meta` del
JSON, que es como se colo el bug).

`--temperature` conserva el default 0.0 porque el protocolo pareado necesita
reproducibilidad (ver el docstring de `loop.generate`): sin sampling fijo, cada
run mide otra cosa. Que baje la fabricacion **si esta medido**: ver la linea
base.

## La metrica

Abstencion binaria, no la nota de 1 a 5. Una respuesta que dice "esto no esta en el
corpus" no es un 2: es el comportamiento correcto, y promediarlo con las
respuestas buenas lo penaliza. Por eso vive aparte.

Es ademas la unica cifra del proyecto con ruido de juez cero: la decision es
binaria y no pasa por el LLM-as-a-judge. Con n=64 el margen del IC95 es de
+/-8.7pp a una tasa de abstencion del 85%, y de +/-11pp a la tasa real de la
run T0 (71.9% de abstencion, 28.1% de fabricacion).

## La linea base

| brazo | temperatura REAL | fabrica |
|---|---|---|
| run A (`result_abstention_base`) | 0.2 | 32/62 = 51.6% |
| run B (`result_abst_t0_base`) | 0.2 | 21/62 = 33.9% |
| **run T0 (`result_abst_t0_applied`)** | **0.0** | **18/64 = 28.1%** |

A y B corrieron a 0.2 por el bug de la Errata. **T0, el 2026-10-10, es la primera
que lleva la temperatura aplicada de verdad.** 64/64 decididas, 0 errores de
juez, 0 fallbacks, 0 truncados; 2.083.943 tokens de agente, 44.798 de juez,
latencia mediana 52s. IC95 de la T0: **+/-11.0pp**.

Pareadas contra T0 sobre los items comunes y decididos por ambas:

- **T0 vs A**: 6 fabricaciones nuevas contra 21 perdidas — McNemar exacto
  **p = 0.0059**;
- **T0 vs B**: 7 contra 10 — **p = 0.6291**.

Que deja y que no: T0 es significativamente mejor que la run A e
indistinguible de la run B. Como A y B se diferencian entre si en 17.5pp, **no
se puede separar el efecto de temperatura del ruido entre brazos**. La
medicion existe por fin, el signo es favorable: T0 es la mas baja de las tres.
Pero con n=64 no resuelve la pregunta.

El piso sigue siendo grave: en el mejor caso, **una de cada cuatro** no
respondibles se fabrica. A un objetivo de <=5% le faltan 23pp.

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

La decision de abstencion es **inestable en el 30%**: nueve de treinta
abstenciones correctas se dan la vuelta entre dos runs. Ampliado a las tres runs
sobre los 62 items comunes: las tres deciden lo mismo en **31/62 = 50.0%**, y
las dos que corrieron a 0.2 discrepan entre si en **19/62 = 30.6%**, que es
exactamente el 30% de siempre. La inestabilidad no es una peculiaridad de la
primera pareja.

**Lo que ha cambiado:** ya no vale que "la comparacion que debia discriminar
entre sampling y trajectory fue la anulada por la Errata" — se corrio, con la
temperatura aplicada de verdad (run T0). **Lo que sigue sin aislarse** es la
atribucion: T0 es un unico brazo a 0.0, y compararla con A o B mezcla el efecto
de temperatura con el ruido entre brazos. Para separarlos hace falta **una
segunda run a 0.0** y medir su flip contra T0. Esa es la medicion que falta, y
cuesta una run.

Lo que se observa en cualquier caso: en cuanto el primer turno diverge, todo lo
demas diverge.

Consecuencia practice: con este ruido, un efecto de 15pp necesita n cercano a 200
items pareados para llegar a p<0.05 por McNemar. Cualquier palanca futura que
se mida contra una sola run por arm esta por debajo del suelo de ruido. Ese es
el motivo real de los cinco fracasos, mas que la calidad de las palancas.

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
  Estado tras la run T0: **73 tareas, 74 outcomes, 74 runs con score**. La
  diferencia entre 73 y 74 es `pearl-b8`: esta en el set ciego y en la suite de
  abstencion, asi que se registra una sola tarea (idempotente por `golden_id`)
  pero deja dos outcomes. No es un duplicado erroneo — el set ciego es mixto
  por diseno y reutiliza los cinco `-b8`.

**Condicion, no verificacion:** `task_stats` calcula `p̄` *por tarea*. Con
`n=1` por golden, `p̄` es 0 o 1 y la varianza es 0 con cualquier umbral. El
selector solo se vuelve informativo cuando un mismo golden se observa varias
veces. El cableado no sirve de nada si no cambia el habito de lanzar evals.

## Donde queda

Hito 0 **no cerrado**: con la temperatura aplicada de verdad, **28.1%** (18/64)
de los no respondibles se fabrica. Sigue siendo inaceptable para un agente de
investigacion, y a un objetivo de <=5% le faltan 23pp.

Lo que se sabe ahora que antes no:

- **la temperatura ya esta medida**, y con ella desaparece la unica palanca que
  se creia certificada y no lo era. El signo es favorable (28.1% < 33.9% <
  51.6%) pero no separable del ruido entre brazos;
- hay infraestructura para puntuar runs y para alimentar Task-CoEvolve, pero sin
  repeticion de evals no genera dato;
- el suelo de ruido (~200 pareados) explica los cinco fracasos tanto o mas que
  la calidad de las palancas, y ahora esta confirmado en tres runs: 50% de
  acuerdo total;
- **`stray_docs` es el primer correlato de fabricacion que aparece con p<0.05**
  en una run, y `cite_precision` queda descartado como filtro (11 de 18 en 1.0).

La direccion que la evidencia apoya, en este orden:

1. **Una segunda run a 0.0**, para medir su flip contra T0. Cuesta una run y es
   lo que separa "la temperatura estabiliza" de "no estabiliza nada". Sin eso,
   toda palanca futura se vuelve a medir contra un suelo de 30% y a n=200.
2. **Atacar `stray_docs`**: filtrar o vetar la recuperacion y la cita de
   documentos fuera del `doc_id` de la pregunta. Es mecanico, no pasa por juez,
   y su techo asociado en la run T0 son 7 de las 18 fabricaciones — **sin que
   este probada la causalidad**, porque puede ir al reves.
3. **Trazabilidad de la run**, que es lo que describe domino 4 ("deliberate
   diagnosis, verification"): seedear el primer turno o grabar y reproducir cada
   paso, para poder ver por que se decide abstenerse en un item y no en otro. Un
   agente recursivo cuyo primer turno ya es aleatorio no puede pararse a si
   mismo a partir de la evidencia. Sigue sin existir.

