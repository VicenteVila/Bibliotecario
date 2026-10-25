# SD-3 — Diagnóstico de H22 (0 tokens)

Fecha: 2026-10-25. Fuente: `results/result_sd2_calibracion.json`,
`sd_pilot/traces_sd2_calibracion.sqlite`, fixtures `sd_tasks_v2/`.

## 1. Qué midió H22

Calibración dev: 12 tareas × A1/A5, `max_turns=12`, cap 100k/celda.
Se ejecutaron 9/24 celdas antes de parar por **C2 imposible**: A1 sacó 100 en
las 5 celdas medidas y C2 exige ≥8/12 con A1<100. Coste: 213.859 tokens.

## 2. Tareas medidas

| tarea | ficheros | chars código | chars TASK | públicos | ocultos | A1 | A5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| dev-f1-inventory | 5 | 1.886 | 1.854 | 7 | 17 | 100 | 76,47 |
| dev-f2-inventory | 6 | 2.710 | 1.265 | 6 | 11 | 100 | 100 |
| dev-f3-inventory | 6 | 2.733 | 1.326 | 5 | 11 | 100 | 100 |
| dev-f1-reservations | 4 | 1.608 | 965 | 6 | 12 | 100 | 50 |
| dev-f2-reservations | 4 | 1.800 | 961 | 6 | 12 | 100 | no ejecutada |

Las 12 tareas dev tienen 4-6 ficheros y 1.207-2.790 chars de código. El
`TASK.md` enumera el contrato exacto de cada función.

## 3. Qué hizo A5

En las 4 celdas A5:

- 36 `read_file`, 4 `write_file`, 10 `run_tests` (traces).
- 1, 1, 2 y **0** escrituras; la celda con 0 escrituras (reservations F1)
  terminó a `max_turns` con 50 % y repitió el mismo fallo público.
- inventory F1: 76,47 % tras una escritura; inventory F2/F3: 100 %.
- A5 no superó a A1 en ninguna celda; en dos empató y en dos quedó por debajo.

## 4. Causas

1. **Contrato exacto**: A1 podía reescribir el paquete desde `TASK.md` sin
   ejecutar tests ni leer nada más.
2. **Escala pequeña**: 4-6 ficheros y <3k chars caben en el contexto inline y
   en la salida one-shot; no hay presión de herramientas ni de amplitud.
3. **A5 sin turnos útiles**: 12 turnos se consumieron leyendo y ejecutando;
   el presupuesto de 12 turnos no da espacio a iterar si el paquete crece.
4. **Hipótesis descartada**: no es un problema de dominio ni de familias
   F1/F2/F3; es el constructo de tarea.

## 5. Hipótesis para SD-3

Para que el arnés con herramientas aporte, la tarea debe exigir información o
trabajo que A1 no puede obtener con su contexto inline y su salida one-shot:

- **Amplitud**: 12-20 ficheros con cambios cruzados; A1 no puede reescribirlos
  todos dentro de 8.192 tokens de salida.
- **Runtime**: comportamiento con estado que solo se observa ejecutando
  secuencias; A1 no ejecuta.
- **Contrato parcial**: `TASK.md` da invariantes y los públicos son oráculo
  parcial; los ocultos cubren generalización.
- **Herramientas**: A5 debe poder leer/escribir ficheros completos y hacer
  varias acciones por turno (canal b2), con 12 turnos y sin truncar la
  lectura a 2.500 chars.

## 6. Decisión

No se editan las tareas H22. SD-3 empieza con un **probe de 3 tareas
desechables** y gates P1-P5; si el probe no muestra headroom, no se construyen
las 24 tareas.
