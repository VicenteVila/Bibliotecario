# Harness Card — SD-2 (HITO22)

Estado: **calibración cerrada NO CUMPLE (2026-10-25); corrida oficial no
ejecutada**. La calibración se paró al ser C2 imposible (A1=100 en las 5
celdas medidas); no se editó ninguna tarea. Cualquier cambio de arnés, prompts,
herramientas, variantes, caps o scoring exige enmienda ratificada y nueva
evidencia.

## 1. Modelo y proveedor

- Modelo: `nvidia/nemotron-3-ultra-550b-a55b`.
- Fallback: el mismo modelo; no hay mezcla de proveedores dentro de la corrida.
- Clave de evaluación: `NVIDIA_API_KEY_PILOTO` (la app usa la principal).
- `LLM_PROVIDERS=nvidia`.

## 2. Split y tareas

- 12 tareas **dev** (solo calibración): `inventory`, `reservations`, `payroll`,
  `routing`, cada una en F1/F2/F3.
- 12 tareas **test** (solo oficial): `banking`, `healthcare`, `logistics`,
  `media`, cada una en F1/F2/F3.
- Familias: **F1 bugfix**, **F2 contrato**, **F3 refactor**; 8 tareas por familia.
- Cada tarea incluye `TASK.md`, `workspace/` (3-6 ficheros Python),
  `tests_public/` (4-6 tests), `tests_hidden/` (10-17 tests), `reference/` y
  `tests_hidden/` fuera del workspace.
- El test está congelado en `evals/sd_pilot/SD2_LOCK.json`
  (SHA-256 del fichero: `d702ac80ffc9d4f8e43088dd19e669e5cde39dfdebe2a9c7022532f4d6812609`;
  split SHA-256: `0fa9cc29dc4eb91df56ca83185cb4da3b56b04a912721b76d4a08094ee49b33a`;
  24 tareas, 274 ficheros hasheados).

## 3. Variantes del arnés

Todas comparten modelo, prompt de sistema, herramientas y scoring; solo cambian
los subsistemas D1/D3/D4/D5/D7. En SD-2 el bucle se limita a 12 turnos (A1 es
one-shot por diseño).

| Variante | D1 bucle | D3 tools | D4 digest | D5 PFs | D7 skills | Regulación |
|---|---|---|---|---|---|---|
| A1 | one-shot | no | no | no | no | no |
| A2 | loop<12> | sí | no | no | no | no |
| A3 | loop<12> | sí | no | sí | no | no |
| A4 | loop<12> | sí | no | sí | sí | no |
| A5 | loop<12> | sí | sí | sí | sí | sí |

## 4. Contexto y prompts

- Prompt inicial: `TASK.md` completo + árbol de ficheros del workspace.
- Bucle: se añade el resultado de cada herramienta y el historial de acciones.
- `A5` añade digest de errores recientes; `A4/A5` cargan `skills_pack`; `A5`
  activa la capa de regulación.
- No se revelan tests ocultos, `reference/` ni el número/localización de fallos.
- Canal: `oficial` (el mismo de H19); no se usa el canal `b`/`b2`/`b3`.

## 5. Herramientas

- `read_file(path)`: lectura de un fichero del workspace, con truncado de
  seguridad en el canal oficial.
- `write_file(path, content)`: escribe el contenido completo indicado.
- `run_tests()`: ejecuta solo `tests_public/` y devuelve pasan/fallan/errores
  y un extracto de salida; nunca ejecuta `tests_hidden/`.
- No hay red, shell, ejecución arbitraria ni acceso fuera del workspace.

## 6. Límites y presupuesto

- `max_turns=12` para las variantes con bucle; A1 = 1 llamada one-shot.
- Calibración dev: 24 celdas (12 tareas × A1/A5), cap **100.000 tok/celda**,
  techo **700.000 tok**.
- Oficial test: 60 celdas (12 tareas × A1-A5), cap **150.000 tok/celda**,
  techo **2.800.000 tok**.
- Corte mid-cell: regla del 80 % de la proyección al alcanzar el techo global;
  el corte queda documentado en `stopped_by`.
- Proyección pre-registrada: calibración 561.792 tok; oficial 2.199.300 tok
  (modelo cúbico H19; `--presupuesto`).

## 7. Scoring y gates

- Score de celda: porcentaje de tests ocultos que pasan contra el workspace
  final (`verifier.hidden_score`).
- QA del BUILD: referencia 100 %, workspace vacío <100 %, públicos fallan en
  el estado inicial.
- Calibración (stop/go): **C1** 12/12 tareas con A1/A5 válidas sin
  `infra_error`; **C2** media A1 ≤85 y A1<100 en ≥8/12; **C3** media A5 ≤85,
  A5<100 en ≥8/12 y A1−A5 ≥10; **C4** coste ≤700k.
- Oficial: **U1** A1-A5, modelo y 12 turnos congelados, sin `infra_error`;
  **U2** 60/60 celdas; **U3** spread Q_h ≥15; **U4** Sens finitos ≥6/12;
  **U5** Sens positivos ≥6/12; **U7** media global ≤60, media A5 ≤80,
  A5<100 ≥8/12; **U8** media A1 ≤80, A1<100 ≥8/12; **U9** coste ≤2,8M;
  **U10** lock intacto, Harness Card presente y sin fuga dev→test.
- Bootstrap descriptivo: 10.000 iteraciones, semilla `20261024`, IC95 de
  medias y de Sens; no convierte Sens en gate adicional.

## 8. Evidencia

- BUILD: `evals/results/result_sd2_build_qa.json`.
- Calibración: `evals/results/result_sd2_calibracion.json` (**NO CUMPLE**:
  parada por C2; 9/24 celdas, 213.859 tok), `evals/logs/sd2_calibracion.log`,
  `evals/sd_pilot/traces_sd2_calibracion.sqlite`.
- Oficial: **no ejecutado** (no hay `result_sd2.json` ni `sd2_oficial.log`).
- Estados reanudables: `evals/sd_pilot/_run_state_sd2_calibracion.json` y
  `evals/sd_pilot/_run_state_sd2.json`.

## 9. Regla de publicación

No se publica un score SD-2 sin esta Harness Card, sin el lock verificado y sin
las gates correspondientes. Un fallo de calibración cierra H22 como **NO
CUMPLE** y no autoriza la corrida oficial; el rediseño sería SD-3.
