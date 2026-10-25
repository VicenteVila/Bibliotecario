# HITO24 — SD-4: constructo de cola larga (probe)

Estado: **EN CURSO — probe diseñado; presupuesto pendiente de ratificación**.
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

## 3. Presupuesto (pendiente de ratificación)

- Modelo: `nvidia/nemotron-3-ultra-550b-a55b`.
- Probe: 3 tareas × {A1, A5} = **6 celdas**.
- A1: one-shot, sin herramientas.
- A5: `max_turns=16`, cap por celda **70.000**, canal **b2**.
- Proyección conservadora: A1 5.479 + A5 70.000 por tarea → **226.437**.
- **Techo solicitado: 250.000 tokens**; si la proyección no cabe, el runner
  aborta antes de llamar al LLM.
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
importación (la cola rota). Falta la ratificación del techo de 250.000 y el
commit de congelación antes de lanzar `--probe`.
