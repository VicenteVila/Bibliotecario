# Hito 0 — que el agente no afirme lo que no tiene

Estado a 2026-10-02. Todos los numeros de aqui son medidos sobre la suite
`evals/golden_abstention.jsonl` (64 no respondibles, 50 de ellas verificadas por
sonda contra el corpus) y sobre los goldenes de respondibles existentes.

## La metrica

Abstencion binaria, no la nota de 1 a 5. Una respuesta que dice "esto no esta en el
corpus" no es un 2: es el comportamiento correcto, y promediarlo con las
respuestas buenas lo penaliza. Por eso vive aparte.

Es ademas la unica cifra del proyecto con ruido de juez cero: la decision es
binaria y no pasa por el LLM-as-a-judge. Con n=64 el margen del IC95 es de
+/-8.7pp a una tasa de abstencion del 85%, y de +/-12pp a la tasa real del 51%.

## La linea base y el unico cambio que funciona

| brazo | fabrica | |
|---|---|---|
| temperatura libre (sd 0.2 del backend) | 51.6% | 32/62 |
| **temperatura 0** | **33.9%** | 21/62 |

Pareado sobre los mismos 62 items, McNemar exacto **p = 0.019**. Quince
abstenciones nuevas frente a cuatro perdidas. Y no cuesta un token: es el mismo
modelo con el sampling apagado.

Por eso `--temperature` ahora tiene default 0.0 en `eval_end2end.py`. El
default de la libreria no se toca; esto es el instrumento de medida.

**El otro lado esta comprobado.** 24 respondibles a temperatura 0: cero
abstenciones falsas, cero respuestas degeneradas, cero truncados, cero fallbacks,
cero bucles de repeticion. El judge medio baja de 3.83 a 3.67, o sea -0.17 a
0.85 sigma: no es una regresion demostrable, y con n=24 el MDE es de 0.39, asi
que no se pretendia distinguir mas.

## Lo que no funciona

`_verify_support` (opt-in por VERIFY_SUPPORT=1). Con temperatura libre parecia
funcionar: 51.6% -> 36.5%, p = 0.12. Al repetir la comparacion **a temperatura 0**
el efecto se dio la vuelta: 6 items corregidos contra 13 rotos, p = 0.17. El
-14.5pp anterior era ruido a su favor.

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

La decision de abstention es **inestable en el 30%**: nueve de treinta
abstenciones correctas se dan la vuelta entre dos runs identicos. No es el
sampling — temperatura 0 no lo reduce (30% -> 31%) — sino la trajectory
recursiva: en cuanto el primer turno diverge, todo lo demas diverge.

Consecuencia practice: con este ruido, un efecto de 15pp necesita n cercano a 200
items pareados para llegar a p<0.05 por McNemar. Cualquier palanca futura que
se mida contra una sola run por arm esta por debajo del suelo de ruido. Ese es
el motivo real de los cinco fracasos, mas que la calidad de las palancas.

## Donde queda

Hito 0 **no cerrado**: 33.9% de fabricacion sigue siendo inaceptable para un
agente de investigacion. Pero se paso de 51.6% a 33.9% con una palanca medida,
gratis, y se sabe cuales palancas no sirven.

La direccion que la evidencia apoya: dejar de tocar el agente y atacar la
trazabilidad de la run. Un agente recursivo cuyo primer turno ya es aleatorio no
puede pararse a si mismo a partir de la evidencia. Seedear el primer turno, o
grabar y reproducir cada paso, es lo que permitiria ver por que se decide
abstenerse en un item y no en otro. Es la misma disciplina que domino 4 describe
("deliberate diagnosis, verification") y la que este proyecto todavia no tiene.