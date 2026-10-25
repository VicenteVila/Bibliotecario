# HITO 23 — SD-3: probe de constructo y decisión

Fecha: 2026-10-25. Estado: **EN EJECUCIÓN**.
Antecedente: H22 cerrado NO CUMPLE (C2 imposible; A1 100 en 5/5 celdas).
Diagnóstico: `SD3_DIAGNOSTICO.md`.

## 1. Objetivo

Comprobar, con 3 tareas desechables y coste acotado, si existe un constructo
en el que el arnés con herramientas (A5, canal b2) supere de forma medible a
A1 one-shot. Solo si el probe pasa se construyen las 24 tareas de SD-3.

## 2. Diseño del probe

Tareas **desechables**, fuera del futuro split dev/test:

| id | eje | forma |
|---|---|---|
| `sd3-probe-breadth` | amplitud / salida | 16 módulos, 16 bugs, cambios locales cruzados; A1 no puede reescribir todo en 8.192 tokens |
| `sd3-probe-runtime` | comportamiento con estado | 8 módulos, secuencias con estado; los públicos revelan un caso, los ocultos generalizan |
| `sd3-probe-contract` | contrato parcial | 8 módulos, `TASK.md` da invariantes incompletas; públicos = oráculo parcial |

Cada tarea: `workspace/` (buggy), `reference/` (correcta), `tests_public/`,
`tests_hidden/`, `TASK.md`, `META.json`.

Matriz: 3 tareas × {A1, A5} = 6 celdas. `max_turns=12`; cap 100k/celda;
A5 en **canal b2** (lectura completa hasta 8.000 chars y multi-acción);
A1 one-shot. Semilla y modelo fijos como en H22.

## 3. Presupuesto

- Techo del probe: **250.000 tokens**.
- Estimación A1: 3 × 2.000 = 6.000; A5: 3 × 90.000 = 270.000 → recorte:
  A5 cap 80.000/celda y techo 250.000. Si el runner proyecta >250.000,
  **no se lanza**.
- H22 no se reutiliza. La Fase 2 exigirá techo nuevo declarado y ratificado.

## 4. Disciplina

- El probe se congela (hashes en `SD3_PROBE_LOCK.json`) **antes** de medir.
- No se editan tareas, públicos, ocultos, TASK ni gates tras ver resultados.
- Si un gate falla → **NO CUMPLE con evidencia**; no se construyen las 24.
- No se eligen tareas por A1/A5; las 3 se miden completas.
- Evidencia: `results/result_sd3_probe.json`, log, trazas y estado.
- No se tocan fixtures, lock ni evidencia de H22.

## 5. Gates (ratificados antes de medir)

- **P1 Validez**: 3/3 tareas con A1 y A5 válidas, sin `infra_error`; QA de
  referencia 100 y workspace vacío <100.
- **P2 A1 no saturado**: media A1 ≤ 70 y ≥2/3 tareas con A1 < 100.
- **P3 Headroom A5**: media A5 ≥ media A1 + 10 y ≥2/3 tareas con A5 < 100.
- **P4 Trabajo real de A5**: en ≥2/3 tareas A5 hace ≥1 `write_file`; y en
  ≥2/3 no agota los 12 turnos solo leyendo.
- **P5 Coste**: total ≤ 250.000 tokens.

Diagnóstico permitido: si A5 falla solo por `max_turns` y ya había escrito,
una celda extra a 16 turnos sobre la peor tarea; **no cuenta** para P3/P4.

## 6. Decisión

- P1-P5 verdes → construir Fase 2.
- Cualquier gate rojo → H23 cierra NO CUMPLE; no se construyen 24 tareas.
- Si P2 falla (A1 sigue 100), el constructo one-shot está saturado incluso con
  amplitud; no se parchea con más tareas del mismo tipo.

## 7. Fase 2 (solo si el probe pasa)

1. 12 dev + 12 test, 8 por familia F1/F2/F3; QA 24/24.
2. `SD3_LOCK.json` + test de congelación antes de calibrar.
3. Calibración dev A1/A5; gates C1-C4 análogos a H22 pero con umbrales
   declarados antes de medir.
4. Oficial 60 celdas; `HARNESS_CARD_SD3.md`; presupuesto nuevo.
5. Sin editar tareas tras ver scores; sin elegir test por A1/A5.

## 8. Ficheros

- `evals/SD3_DIAGNOSTICO.md`
- `evals/sd_pilot/sd3_tasks.py`
- `evals/sd_pilot/sd3_sens.py`
- `evals/sd_pilot/run_sd3.py`
- `evals/sd_pilot/sd_tasks_v3/` (probe; luego dev/test)
- `tests/test_sd3.py`
- `evals/results/result_sd3_probe.json`
- `evals/logs/sd3_probe.log`
- `evals/sd_pilot/traces_sd3_probe.sqlite`
- `evals/sd_pilot/_run_state_sd3_probe.json`

## 9. Cierre

(pendiente)
