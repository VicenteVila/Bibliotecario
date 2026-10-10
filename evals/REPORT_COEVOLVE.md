# Co-evolución (Task-CoEvolve): el estimador es correcto, pero no le gana a no hacer nada

**Fecha:** 2026-10-10 · **Coste: 0 tokens** (todo simulado sobre datos ya guardados).

## Veredicto

El ciclo en vivo de co-evolución **queda descartado con datos, no con opinión**.
La maquinaria está bien escrita: es insesgada y le gana a la media simple de la
submuestra. Pero contra el baseline que importa —*no hacer nada y quedarse con
la nota antigua*— **solo gana en el mejor de los casos y a `rho = 0.5`**, que
son 1.45 M de tokens persiguiendo un cambio de 0.043 que ya está por debajo del
ruido medido (0.05). Sería pagar 1.45 M para medir ruido.

Decisión: **no se gasta**.

## Alcance, y lo que queda fuera

Medido: `estimator.py` (Hájek, diferencia anclada, `estimate_full`) y
`selector.py` (pesos de varianza ponderada, `sample_subset`,
`inclusion_probabilities`).

**No medido:** `wiki.py` (`gate_skill`, promoción/rollback de habilidades y las
tres capas raw/accumulated/skill). Esa mitad sigue sin evaluar.

## 1. De dónde sale la historia (y por qué no de la DB)

La idea era medir la deriva desde `harness_runs`, que tiene 1375 filas de
2026-09-21 a 2026-10-10. **No sirve**: el `score` es `NULL` en los 1120 runs
anteriores a hoy. La instrumentación de puntuación se añadió el 2026-10-10, y
los 245 scores que existen son exactamente los 245 `task_outcomes`, todos del
mismo día. La `metadata` de los runs viejos solo lleva `turns` y `tools`.

La historia real está en `evals/result_*.json`: 41 ficheros entre 2026-09-29 y
2026-10-10, con puntuación por pregunta. Ahí se mide.

## 2. Estado del pool

99 tareas, todas `kind=qa`, **35 respondibles + 64 no respondibles**, con 245
outcomes repartidos en 2026-10-10 (08:04–14:16). Ninguna tarea se ha quedado
sin observaciones.

| | media `pbar` | mediana | en techo (`pbar=1.0`) | `pbar=0` |
|---|---|---|---|---|
| respondibles (35) | 0.771 | 1.000 | **27/35** | 8 |
| no respondibles (64) | 0.797 | 1.000 | **38/64** | 0 |
| **total (99)** | **0.788** | **1.000** | **65/99** | 8 |

**Las dos terceras partes del pool están en el techo.** Solo 26 tareas tienen
margen real de movimiento en cualquier dirección. Esto es lo que aplasta la
deriva en el punto 4.

### El selector funciona

Pesos `w_t = max(pbar(1-pbar), l) + lambda/sqrt(n)`:

```
min=0.250  max=0.550  ratio=2.20x        (1.00 = uniforme = degenerado)
top-5 ponderados: ids 76, 79, 84, 87, 89 — todos pbar=0.0, n=1
```

No es degenerado y prioriza como manda la fórmula: **el piso `l` de las tareas
nunca resueltas las coloca primero**, que es exactamente el diseño de Task-CoEvolve
Fase 1.

## 3. Ruido frente a deriva

Tres réplicas **exactas** del mismo sistema, sin cambiar nada, sobre el mismo
golden — en la métrica binaria que usa el pool (`run_success`, la misma que
alimenta `task_outcomes.success`):

| réplica | golden | n | Δ éxito |
|---|---|---|---|
| `blind_r5` vs `blind_r6` | `golden_blind_qa` | 40 | **+0.025** |
| `ext2_r1` vs `ext2_r2` | `golden_blind_qa_ext2` | 40 | **−0.050** |
| `abst_t0_applied` vs `abst_t0_rep2` | `golden_abstention` | 64 | **−0.063** |

**Suelo de ruido ≈ 0.05**, y es del orden del error binomial a n=40
(sqrt(0.875·0.125/40) = 0.052): las réplicas se mueven como si solo variara el
muestreo.

La deriva por **intervención deliberada** (mismo golden, versiones distintas):

| arco | Δ éxito de entrada | Δ **realizado** tras el techo |
|---|---|---|
| `blind_r1` → `blind_r5` (5 intervenciones) | +0.125 | **+0.043** |
| `blind_r1` → `blind_promptstop` | +0.025 | **+0.009** |

El techo absorbe el 66% de la mejora: un +0.125 aplicado a las 99 tareas solo
mueve la media +0.043, porque 65 de ellas ya están en 1.0 y el recorte no deja
que suban.

**La deriva real (+0.043 en el mejor arco) es menor que el ruido (0.05).**

## 4. El test del estimador

### El test que NO cuenta

Primero corrí el caso *oracle*: `x_t = pbar_t` para las tareas muestreadas.
Salía **RMSE = 0.0000**, exacto en las 12 condiciones.

**No prueba nada.** `anchored_difference` usa como anclas el `pbar` de **todas**
las tareas, así que cuando la observación iguala la ancla devuelve la verdad por
construcción: `base = media(anclas) = verdad` y `adj = 0`. Es tautológico. Se
descarta.

### El test que sí cuenta: anclas obsoletas

Que es el caso de uso real: tienes una nota antigua del pool y quieres la nota
**actual** corriendo solo una fracción de tareas.

- ancla = `pbar` histórico (0.7879)
- verdad actual = `pbar` desplazado y recortado
- observación = Bernoulli(verdad) para cada tarea muestreada
- 400 réplicas por condición, `inclusion_probabilities` con 600 sims

| deriva | rho | estimador RMSE | media simple | ancla vieja | veredicto |
|---|---|---|---|---|---|
| **+0.043** (mejor arco real) | 0.1 | 0.0753 | 0.1304 | 0.043 | pierde |
| | 0.2 | 0.0542 | 0.1002 | 0.043 | pierde |
| | 0.3 | 0.0438 | 0.0786 | 0.043 | pierde |
| | **0.5** | **0.0347** | 0.0575 | 0.043 | **gana** |
| +0.017 (ruido) | 0.1–0.5 | 0.0702 → 0.0329 | 0.1368 → 0.0594 | 0.017 | pierde siempre |
| +0.009 (r1→promptstop) | 0.1–0.5 | 0.0677 → 0.0330 | 0.1384 → 0.0612 | 0.009 | pierde siempre |

Dos cosas a la vez:

1. **Sesgo ≈ 0 en las 12 condiciones** (|sesgo| ≤ 0.0053). El estimador es
   correcto.
2. **Le gana a la media simple en las 12** (1.2×–1.7× menos RMSE). La corrección
   Horvitz–Thompson/Hájek hace trabajo real.
3. **Pero a la ancla vieja solo le gana en una fila de doce**, y en esa fila hay
   que estar en `rho = 0.5`.

### El coste

A ~29k tokens por pregunta (medido en `result_blind_promptstop.json`:
1158851 / 40):

| rho | tareas | coste/iteración |
|---|---|---|
| 0.1 | 10 | **0.29 M** |
| 0.2 | 20 | **0.58 M** |
| 0.3 | 30 | **0.87 M** |
| 0.5 | 50 | **1.45 M** |

La única condición donde gana cuesta 1.45 M para detectar 0.043 de deriva, con
un ruido de réplica de 0.05 por encima.

## 5. La excepción que confirma la regla

Hubo **una** deriva enorme en la historia del proyecto: el lado de la
abstención pasó de **0.492 → 1.000 (+0.508)** con el cambio de prompt. El
estimador sí cazaría esa.

Pero (a) esa mejora **ya está hecha y medida** — es el Hito 0 —, así que no
necesita al estimador para descubrirla; y (b) ese movimiento pertenece a
`golden_abstention`, no al pool de 99 tareas, cuyo `pbar` refleja el reparto de
hoy (35 + 64), con el techo del punto 2.

**Lo que haría que el ciclo se justificara:** un pool con tareas más difíciles
(margen por debajo del techo) o una cadencia de cambios grande y frecuente. Con
el pool actual, no.

## 6. Cómo se reproduce

Ninguna de estas cifras cuesta tokens. Con la DB y los resultados ya
commiteados:

```bash
python - <<'PY'
from bibliotecario.coevolve import task_pool as TP, selector as SEL, estimator as EST
print(TP.task_stats())          # pbar y n de las 99 tareas
print(SEL.weights(TP.task_stats()))
print(SEL.inclusion_probabilities(TP.task_stats(), 0.2))
PY
```

La deriva se lee de `evals/result_*.json` agrupados por `meta.golden`, usando
`eval_end2end.run_success` como métrica binaria; el suelo de ruido son las
réplicas exactas (`blind_r5`/`r6`, `ext2_r1`/`r2`, `abst_t0_applied`/`rep2`).
