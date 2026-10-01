# Evaluación ciega: 40 preguntas × 3 runs

Set: `evals/golden_blind_qa.jsonl` (escrito leyendo los chunks, sin ejecutar el
agente ni el juez). Agente pineado a `nvidia/nemotron-3-super-120b-a12b`
(`--provider nvidia`). Juez pineado a `openai/gpt-oss-20b` (familia distinta).
Datos: `evals/result_blind_r{1,2,3}.json`.

## Resultado

| | r1 | r2 | r3 | media |
|---|---|---|---|---|
| judge (35 respondibles) | 4.400 | 4.000 | 4.257 | **4.219** |
| errores de juez | 0 | 0 | 1 | |
| cite_precision | 0.929 | 0.814 | 0.900 | 0.881 |
| abstain_rate (5 no respondibles) | 1.0 | 0.8 | 0.8 | 0.867 |
| abstención falsa | 0.057 | 0.143 | 0.057 | |
| truncadas | 0 | 1 | 0 | |
| tokens de agente | 670k | 666k | 707k | 681k |

**judge = 4.219, IC 95% ± 0.273** sobre 105 observaciones.

## Varianza

| | sd |
|---|---|
| entre preguntas (dificultad del ítem) | 1.234 |
| dentro de la misma pregunta (ruido del agente) | 0.445 |

El ruido *dentro* de la pregunta es el que importa para comparar sistemas.
Con 3 runs y las mismas 35 preguntas (comparación emparejada) se detectan
diferencias de **0.112 puntos** al 95%. Con una sola run serían 0.194.

Ésta es la razón de haber pagado las 3 runs: **5 preguntas tienen sd ≥ 1.7** y
barcan la escala entera entre runs.

| pregunta | r1 | r2 | r3 | sd |
|---|---|---|---|---|
| tce-b5 | 5 | 3 | 0 | 2.52 |
| pg-b2 | 5 | 1 | 5 | 2.31 |
| reas-b2 | 5 | 1 | 1 | 2.31 |
| pg-b5 | 2 | 1 | 5 | 2.08 |
| reas-b5 | 2 | 5 | 5 | 1.73 |

Con una sola run, `tce-b5` habría podido reportarse como 5 y como 0.

## Dificultad: mi etiqueta no predice nada

| | n | media | sd |
|---|---|---|---|
| fácil | 12 | 4.083 | 1.556 |
| media | 14 | 4.048 | 1.577 |
| difícil | 9 | **4.667** | 0.832 |

Las "difíciles" puntúan **más alto** y con **menos** dispersión. Mi etiqueta
decía "cuántos chunks hay que combinar", no "cuánto le cuesta al agente". No
serve para estratificar. Lo que separa el rendimiento no es la dificultad
percibida sino si el agente encuentra el chunk.

## Abstención: 87% pero no calibrada

| | r1 | r2 | r3 |
|---|---|---|---|
| pearl-b8 | ✓ | ✗ (inventó "2.7") | ✓ |
| pg-b8 | ✓ | ✓ | ✓ |
| tce-b8 | ✓ | ✓ | ✓ |
| reas-b8 | ✓ | ✓ | ✗ (inventó "0.23") |
| wiki-b8 | ✓ | ✓ | ✓ |

13/15 = 86.7%. Las dos fabricaciones son *"un número que sí existe en el
paper pero en otro contexto"*: pearl-b8 dio 2.7 (las rutas medias de V1) y
reas-b8 dio 0.23 (la puntuación final). **Roba un valor plausible del
contexto en vez de inventar de la nada**, que es más difícil de detectar.

**Y no está calibrada**: `tce-b3` y `tce-b4` son abstenciones sobre preguntas
respondibles, y se repiten en las 3 runs. La respuesta está en `[3:16]` y
`[3:26]`. El agente no distingue "no está en el corpus" de "no lo he
retrieved". `abstain_rate` alto no significa que sepa cuándo callarse.

## Fallos dominantes

No son fallos de razonamiento sino de **recuperación**:

- `tce-b4` (3/3): la Tabla 4 con las cuatro configuraciones de ablación está en
  `[3:26]`; el agente dice que no la encuentra y sugiere consultar "suplementos
  no indexados".
- `pg-b5`: mezcla columnas de una tabla y fabrica el 4.003,24 para el baseline
  (el real era 7.403,98).
- `wiki-b4`: inventa un "binomial exact test" donde el paper usa *paired
  bootstrap*.
- `reas-b5`: responde con un marco de RL en vez de qué devuelve
  `validate_candidate`.

## Limitaciones conocidas

- **Una sola familia de juez.** Agente y juez están ambos en NVIDIA; solo
  difieren en familia de modelo. No hay proveedor independiente.
- **El juez no es determinista.** 1 de 105 scores fue `None` (JSON truncado
  aunque el presupuesto era de 900 tokens) y el propio juez varía entre runs.
- **Coste del barrido profundo sin medir en USD**: se cuentan tokens, no
  dólares, porque no hay ficha de precios por modelo.
- **1 respuesta truncada** de 120 (r2).