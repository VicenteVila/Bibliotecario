# HITO24 — SD-4: constructo de cola larga (probe)

Estado: **CERRADO 2026-10-25 — NO CUMPLE**.
Fecha de diseño: 2026-10-25. Este plan es contrato: sus gates se ratifican
antes de medir y no se tocan después.

## 1. Por qué SD-4

H22 y H23 cerraron **NO CUMPLE** con evidencia. H22 midió una calibración
demasiado fácil para A1 (100/100 en 5/5). H23 midió un probe con tres
constructos; A1 solo midió **0%** en amplitud porque el límite de salida
one-shot (8.192 completion) truncó el JSON de 16 módulos. Ese resultado no
distingue “no puede” de “no cabe en la salida”, y no es una base limpia para
decidir el benchmark.

SD-4 cambia el constructo: en vez de pedir a A1 que **produzca** un payload
grande, le pide que **lea y corrija** un workspace cuyo defecto está en la
cola de cada fichero. La asimetría de entrada está en el harness:

- A1 (`one_shot`): recibe el workspace inline truncado a **6.000 caracteres**;
  no tiene herramientas.
- A5 (`b2`): puede leer ficheros hasta **8.000 caracteres**; tiene shell,
  lectura, escritura y tests.

Cada módulo mide **7.569 caracteres**; la línea defectuosa
`TABLA_EXTRA = {` está en el carácter **7.548**. A1 no puede verla; A5 sí.
Esto no depende de que A1 escriba más de 8.192 tokens: el defecto es
invisible para su entrada.

## 2. Probe (3 tareas desechables)

| ID | Paquete | Módulos | F | Públicos | Ocultos |
|---|---|---:|---|---:|---:|
| `sd4-probe-tail-2` | `catalogo` | 2 | F1 | 2 | 22 |
| `sd4-probe-tail-4` | `facturacion` | 4 | F2 | 4 | 44 |
| `sd4-probe-tail-24` | `inventario` | 24 | F3 | 24 | 264 |

Cada módulo contiene 150 entradas deterministas, `consultar`, `total`,
`por_grupo` y `validar`; el workspace trae una línea final incompleta
`TABLA_EXTRA = {`. La referencia elimina esa línea. El test público solo
comprueba la primera entrada; los ocultos comprueban primeras, últimas,
total, grupos y validación. `TASK.md` dice “elimina la línea final
incompleta; no cambies los datos”, sin revelar el contenido de la cola.

La tarea de 24 módulos mide presión de presupuesto y multitarea; no se usa
para elegir tareas por el resultado de A1/A5. Los tres IDs son el probe
completo y desechable. La Fase 2 (24 tareas dev/test) no existe hasta que
R1-R6 pasen.

## 3. Presupuesto (ratificado 2026-10-25)

- Modelo: `nvidia/nemotron-3-ultra-550b-a55b`.
- Probe: 3 tareas × {A1, A5} = **6 celdas**.
- A1: one-shot, sin herramientas.
- A5: `max_turns=16`, cap por celda **70.000**, canal **b2**.
- Proyección conservadora: A1 5.479 + A5 70.000 por tarea → **226.437**.
- **Techo ratificado por el dueño: 250.000 tokens** (2026-10-25); si la
  proyección no cabe, el runner aborta antes de llamar al LLM.
- No se reutiliza el techo de H22/H23. Este plan no autoriza Fase 2 ni el
  oficial: solo el probe.

## 4. Disciplina

- Congelar tareas, `sd4_tasks.py`, `sd4_sens.py`, `run_sd4.py`, tests y
  `SD4_PROBE_LOCK.json` antes de medir.
- No editar fixtures, umbrales, gates ni `TASK.md` después de ver scores.
- No reutilizar ni modificar fixtures, locks o evidencia de H22/H23.
- No tocar `Respuesta.txt` ni `D "Solucion idempotencia.txt"`.
- Evidencia inmutable: `evals/results/result_sd4_probe.json`, log, traza y
  estado. Los intentos fallidos se documentan con causa y coste.
- Commits en ASCII sin acentos; secret scan antes de commit.

## 5. Gates R1-R6 (ratificar antes de medir)

| Gate | Condición | Si falla |
|---|---|---|
| R1 | 3/3 tareas con A1 y A5 válidas, sin `infra_error` | NO CUMPLE |
| R2 | media A1 ≤ 10 y 3/3 A1 < 100 | NO CUMPLE |
| R3 | media A5 ≥ 60, A5 ≥ A1+10 y ≥1/3 A5 < 100 | NO CUMPLE |
| R4 | A5 escribe en ≥2/3 y no agota 16 turnos sin escribir en ≥2/3 | NO CUMPLE |
| R5 | coste total ≤ 250.000 | NO CUMPLE |
| R6 | A5 ≥ 80 en ≥2/3 tareas | NO CUMPLE |

`cumple = R1 ∧ R2 ∧ R3 ∧ R4 ∧ R5 ∧ R6`.

- **Todos verdes** → se autoriza diseñar/construir las 24 tareas de Fase 2
  con presupuesto nuevo; este plan no las construye.
- **Cualquier rojo** → H24 cierra **NO CUMPLE con evidencia**; no se
  construyen las 24 tareas, no hay oficial y no hay Harness Card SD-4.

## 6. Si el probe pasa

La Fase 2 se planificará en una enmienda separada: 12 dev + 12 test,
mezcla de 8/12/16/24 módulos, QA, lock, calibración y oficial con techo
nuevo. No se reutilizan las tareas del probe ni se eligen por dificultad
observada en A1/A5.

## 7. Evidencia prevista

- `evals/results/result_sd4_probe.json`
- `evals/logs/sd4_probe.log`
- `evals/sd_pilot/traces_sd4_probe.sqlite`
- `evals/sd_pilot/_run_state_sd4_probe.json`
- `evals/sd_pilot/SD4_PROBE_LOCK.json`

## 8. Estado

Diseño y QA locales hechos sin LLM: 3/3 tareas con referencia 100, workspace
0, públicos de referencia verdes y públicos del workspace con error de
importación (la cola rota). El dueño ratificó el techo de 250.000 el 2026-10-25. Probe, gates y tareas
quedaron congelados en `d6481dc`; el probe se lanzó sobre `e463983` y cerró
**NO CUMPLE** con la evidencia de §9. No hay Fase 2, oficial ni Harness Card
SD-4.


## 9. Cierre del probe — NO CUMPLE (2026-10-25)

Ejecución única sobre `e463983`; lock `SD4_PROBE_LOCK.json` verificado sin
problemas. 5/6 celdas puntuadas: A5 de `sd4-probe-tail-24` no se ejecutó
porque el techo ya estaba superado.

| celda | score | turns | tools | writes | parada | tokens |
|---|---:|---:|---:|---:|---|---:|
| A1 `tail-2` | 27,2727 | 1 | 0 | 0 | `one_shot` | 13.882 |
| A5 `tail-2` | 0,0 | 7 | 2 | 0 | `presupuesto` | 91.027 |
| A1 `tail-4` | 0,0 | 1 | 0 | 0 | `one_shot` | 22.160 |
| A5 `tail-4` | 0,0 | 6 | 4 | 0 | `presupuesto` | 72.152 |
| A1 `tail-24` | 0,0 | 1 | 0 | 0 | `one_shot` | 90.964 |
| A5 `tail-24` | — | — | — | — | no ejecutada | 0 |

- Coste: **16 llamadas, 238.176 prompt + 52.009 completion = 290.185 tok**;
  **40.185 por encima del techo de 250.000**. A5 `tail-2` gastó 91.027 >
  70.000 de cap: el cap se comprueba tras el turno y el overshoot de una
  llamada no se recorta.
- **R1 ❌** 2/3: falta A5 `tail-24`; **R2 ❌** media A1 13,6364 y
  `A1<100=2` (solo 2 tareas válidas); **R3 ❌** media A5 0,0 y diferencia
  −13,6364; **R4 ❌** A5 con escritura 0/3 y no atascada 2/3; **R5 ❌**
  290.185 > 250.000; **R6 ❌** A5≥80 0/2.
- Causa medida: A5 leyó los ficheros completos (7.569 chars) pero intentó
  reescribirlos con `write_file` completo; la salida se cortó a 4.096 tokens
  y produjo JSON inválido (5 y 2 avisos en `tail-2`/`tail-4`), sin ninguna
  escritura. A1 `tail-2` alcanzó 27,27 por salida parcial; `tail-4`/`tail-24`
  agotaron completion (8.192) sin bloques parseables. El constructo no
  separa “no puede” de “no cabe en la salida” para A5 en este tamaño.
- Decisión: **NO CUMPLE**. No se construyen las 24 tareas, no hay oficial,
  no hay Harness Card SD-4 y no se reintenta con `--resume` (el plan prohíbe
  rescatar un probe rojo). SD-4 no sustituye a SD-2/SD-3.
- Evidencia: `evals/results/result_sd4_probe.json`, `evals/logs/sd4_probe.log`,
  `evals/sd_pilot/traces_sd4_probe.sqlite`,
  `evals/sd_pilot/_run_state_sd4_probe.json` y `SD4_PROBE_LOCK.json`.
