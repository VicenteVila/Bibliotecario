# Hito 0 — que el agente no afirme lo que no tiene

Estado a 2026-10-02. **Corregido el 2026-10-10**: la seccion "Errata" anula la
atribucion de temperatura. Todos los numeros de aqui son medidos sobre
`evals/golden_abstention.jsonl` (64 no respondibles, 50 de ellas verificadas por
sonda contra el corpus) y sobre los goldenes de respondibles existentes.

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
`test_wrap_generate_reenvia_temperature`. **La temperatura sigue sin medir.**

`--temperature` conserva el default 0.0, ya no por la cifra anulada sino porque
el protocolo pareado necesita reproducibilidad (ver el docstring de
`loop.generate`): sin sampling fijo, cada run mide otra cosa. Que baje la
fabricacion **no esta medido**.

## La metrica

Abstencion binaria, no la nota de 1 a 5. Una respuesta que dice "esto no esta en el
corpus" no es un 2: es el comportamiento correcto, y promediarlo con las
respuestas buenas lo penaliza. Por eso vive aparte.

Es ademas la unica cifra del proyecto con ruido de juez cero: la decision es
binaria y no pasa por el LLM-as-a-judge. Con n=64 el margen del IC95 es de
+/-8.7pp a una tasa de abstencion del 85%, y de +/-12pp a la tasa real del 51%.

## La linea base

| brazo | fabrica | |
|---|---|---|
| run A | 51.6% | 32/62 |
| run B | 33.9% | 21/62 |

**Ambas a temperatura 0.2** (ver Errata). Pareadas sobre los mismos 62 items,
McNemar exacto p = 0.019, quince abstenciones nuevas contra cuatro perdidas.
Ese p mide que las dos runs difieren; no dice por que, y ya no puede decirse que
sea por temperatura.

El piso es lo importante: aun en el mejor caso, una de cada tres no respondibles
se fabrica.

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
fabricaciones de la primera linea base.

## El ruido, que es donde nos hemos quedado 20 horas

La decision de abstencion es **inestable en el 30%**: nueve de treinta
abstenciones correctas se dan la vuelta entre dos runs. No se llego a aislar si
viene de la sampling o de la trajectory recursiva — la comparacion que debia
discriminar entre ambas fue la anulada por la Errata, asi que **sigue sin
saberse**. Lo que se observa: en cuanto el primer turno diverge, todo lo demas
diverge.

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

**Condicion, no verificacion:** `task_stats` calcula `p̄` *por tarea*. Con
`n=1` por golden, `p̄` es 0 o 1 y la varianza es 0 con cualquier umbral. El
selector solo se vuelve informativo cuando un mismo golden se observa varias
veces. El cableado no sirve de nada si no cambia el habito de lanzar evals.

## Donde queda

Hito 0 **no cerrado**: entre un 34% y un 52% de fabricacion, segun la run, sigue
siendo inaceptable para un agente de investigacion.

Lo que se sabe ahora que antes no:

- **temperatura sin medir**, y con ella la unica palanca que se creia certificada;
- hay infraestructura para puntuar runs y para alimentar Task-CoEvolve, pero sin
  repeticion de evals no genera dato;
- el suelo de ruido (~200 pareados) explica los cinco fracasos tanto o mas que
  la calidad de las palancas.

La direccion que la evidencia apoya: **primero medir de verdad la temperatura**
(cuesta una run y ahora el flag funciona), y en paralelo atacar la trazabilidad
de la run. Un agente recursivo cuyo primer turno ya es aleatorio no puede
pararse a si mismo a partir de la evidencia. Seedear el primer turno, o grabar y
reproducir cada paso, es lo que permitiria ver por que se decide abstenerse en un
item y no en otro. Es la misma disciplina que domino 4 describe
("deliberate diagnosis, verification") y la que este proyecto todavia no tiene.
