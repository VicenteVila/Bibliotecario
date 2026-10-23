# Plan HITO20 — endurecimiento de tareas (B) + arreglos del bucle (C1)

> **Estado**: §0-§0.1 **DECLARADO 2026-10-23** — decisión del dueño y protocolo
> del diagnóstico, **antes de cualquier medición**. §0.2 se rellena al cerrar el
> diagnóstico. §1+ (alcance HITO20: BUILD, gates, techo) se escribe con el
> resultado del diagnóstico y **requiere su ratificación** como siempre.

## §0 — Decisión del dueño (2026-10-23)

Tras cerrar el H19 en **NO CUMPLE** (§5 de `HITO19_PLAN.md`), el dueño decide
esta escalera:

1. **Diagnóstico de 0-0,5M tokens** antes que nada.
2. **Si sale bien → se lanza HITO20 = B + C1, sin acelerador.**
   - **B** = tareas endurecidas (BUILD nuevo; las 12 tareas de H19 quedan
     congeladas como evidencia y no se tocan).
   - **C1** = arreglar la base del bucle: presupuesto de turnos y robustez de
     infraestructura (reintentos).
   - **sin acelerador** = **sin C2** (no se baja el modelo).
3. **Si no hay conclusiones claras con el primer lanzamiento B + C1 → B + C2**
   (C2 = modelo más débil como acelerador, para esa segunda fase).

Salvedad de lectura (declarada, no se improvisa): la regla del punto 3 apunta
al **primer lanzamiento de HITO20 (B+C1)**. Si el **diagnóstico** no da
conclusión clara, **se para y se consulta al dueño** antes de lanzar HITO20.

## §0.1 — Diagnóstico: protocolo DECLARADO antes de correr (2026-10-23)

**Pregunta única**: ¿el colapso de las 22 celdas truncadas del oficial
(media 38.4 vs 92.2 de las que terminaron) se debe a que **16 turnos no
bastan** (→ C1 lo arregla) o a que el bucle **queda atascado** aunque tenga
turnos (→ C1 no basta y hace falta C2 u otra cosa)?

**Techo total: 500.000 tokens** (Parte B ≤450k + margen 50k). Mismo modelo
(`ultra-550b`), mismas variantes; el **único** cambio es `max_turns 16 → 32`.
Este diagnóstico **no mide gates**, no sustituye evidencia de H19 y no toca
nada del oficial (workspaces, estado, trazas y resultados propios aparte).

### Parte A — análisis de las trazas oficiales (0 tokens)

Sobre `evals/sd_pilot/traces.sqlite`, para cada una de las 22 celdas con
`stopped_by=max_turns`:

- Señales por celda: escrituras de archivo (`write_file`) por turno;
  escrituras dentro de los últimos 3 turnos; **racha máxima** de llamadas
  idénticas consecutivas (mismo `tool_name` + mismos args); proporción
  lectura/escritura.
- **Clasificación (regla declarada)**:
  - **PROGRESA** = hay escrituras en ≥1 de los últimos 3 turnos **y** la racha
    máxima de idénticas ≤3.
  - **ATASCADO** = racha de idénticas ≥4 **o** 0 escrituras en los últimos 5
    turnos.
  - **INDETERMINADO** = el resto.
- Evidencia: `evals/results/result_sens_sd_diag_trazas.json`.

### Parte B — mini-corrida con `max_turns=32` (≤450k)

- **Candidatas (criterio declarado)**: celdas oficiales con
  `stopped_by=max_turns`, coste@16 ≤170k y `score@16 < 70`.
- **Selección concreta (tras la Parte A, 2026-10-23)**:
  1. **A2_plugin-registry** — score@16 64.29, coste@16 92.549 (bucle desnudo).
  2. **A5_repo-cache-layer** — score@16 41.67, coste@16 114.467 (bucle completo
     con regulación). `2 × (92.549 + 114.467) = 413.952` ≤ 450k (peor caso,
     ambas a 32 turnos).
  3. 3ª opcional **A5_workflow-statemachine** (est@16 116.571): solo se
     ejecuta si `acumulado_real + 2×116.571 ≤ 450.000`.
  Motivo: una tarea donde A1=82.14 (la única donde un arnés le ganó) y otra
  con A1=100 y 0 escrituras nunca; una desnuda y una completa; distintas
  tareas.
- **Ejecución**: modo nuevo `--diagnostico` de `run_pilot.py`. Workspaces
  propios en `/tmp/opencode/sd_pilot_diag/` (los oficiales no se pisan),
  trazas `traces_diag.sqlite`, estado `_run_state_diag.json`, resultado
  `evals/results/result_sens_sd_diag.json`, log `evals/logs/sens_sd_diag_run.log`.
  Si el acumulado excede 450k **entre celdas**, se detiene y se documenta.
- **Reglas de veredicto (se evalúan en orden D1 → D2 → D3, sin retoque tras
  ver los datos)**:
  - **D1 CLARO_C1**: `score@32 ≥ 0.9 × A1` (one-shot de la misma tarea) en
    ≥2 celdas (si solo corren 2, ambas) → el presupuesto era el cuello de
    botella → **se lanza HITO20 = B+C1**.
  - **D2 NO_CLARO**: media de (`score@32 − score@16`) < **+10** puntos →
    doble presupuesto casi no mueve → el problema no es solo presupuesto →
    **se consulta al dueño** (candidato a su regla de escalera B+C1+C2).
  - **D3 AMBIGUO**: cualquier otro caso (incluida una sola celda ejecutada)
    → **se consulta al dueño** con datos.

### Disciplina de commits (§4 del plan)

Orden: (1) esta declaración, (2) implementación del modo `--diagnostico` +
tests, (3) evidencia del diagnóstico + §0.2. Puerta verde antes de cada
commit. Evidencia (`result_*.json`, `traces_*.sqlite`, logs) se añade con
`-f` donde gitignore lo exija y **nunca se edita ni borra** tras publicarse.

## §0.2 — Resultado del diagnóstico (CERRADO 2026-10-23 → **D2_NO_CLARO**)

Evidencia: `evals/results/result_sens_sd_diag_trazas.json` (Parte A),
`evals/results/result_sens_sd_diag.json` (Parte B),
`evals/logs/sens_sd_diag_run.log`, `evals/sd_pilot/traces_diag.sqlite` +
`_run_state_diag.json`. Coste total del diagnóstico: **759.691 tokens**
(ver incidente de techo más abajo).

### Parte A (0 tokens) — las 22 truncadas: **22/22 ATASCADO**

Ninguna celda truncada escribió un fichero en sus últimos 5 turnos; 13 de
ellas **nunca escribieron** (0 `write_file` en toda la celda; solo lecturas y
`run_tests`). En toda la corrida oficial hubo **38 `write_file`** sobre 572
llamadas a tool — el bucle casi nunca llega a escribir código.

### Parte B (`max_turns=32`) — celdas ejecutadas y veredicto

| celda | @16 | @32 | A1 | delta | qué pasó |
|---|---|---|---|---|---|
| A2_plugin-registry | 64.29 | 64.29 | 82.14 | **+0.00** | **INVALIDADA**: caída de DNS (`URLError`) al turno 6/32 → `error_llm`, solo 7.573 tokens. Intento documentado; no mide `max_turns` |
| A5_repo-cache-layer | 41.67 | **41.67** | 100.00 | **+0.00** | 30 turnos, 30 tools, **752.118 tokens**, paro `presupuesto` (duración de regulación: 1.874s > 1.800s). **0 escrituras**: 29 lecturas (¡**16× el mismo** `catalogo/servicio.py`!) + 1 `run_tests` |
| A5_workflow-statemachine | — | no ejecutada | — | — | techo excedido tras la celda 2 → `se detiene` (log) |

**Veredicto aplicado en orden D1→D2→D3: `D2_NO_CLARO`** (media de deltas
0.00 < +10) → **acción declarada: parar y consultar al dueño**. Robusto al
incidente DNS: incluso descartando la celda invalidada, la única par válida
tiene delta **+0.00**.

**Lectura técnica**: la hipótesis C1 «16 turnos no bastan» queda **refutada
para esta celda**: con el doble de turnos y 6,6× de coste, el bucle de A5 ni
siquiera intenta `write_file` y se obsesiona releyendo un fichero. Causas
estructurales visibles en las trazas (parte del porqué):
`read_file` entrega en el historial solo 2.500 chars (`_MAX_TOOL_OUT`), el
prompt inicial trae solo el árbol (sin contenido), el bucle ejecuta **1 acción
por turno** (`parse_action` se queda con el primer JSON) — mientras el
one-shot recibe todos los ficheros completos inline y reescribe de golpe.

### Incidentes (declarados, nada se esconde)

1. **DNS caído** en la celda 1 (transitorio, como en el oficial): intento
   fallido con coste **7.573 tokens**; celda invalidada, no re-ejecutada en
   este cierre (el veredicto no depende de ella).
2. **Techo excedido: 759.691 > 450.000** (Parte B) y > 500.000 (techo total
   del dueño): **+259k sobre lo autorizado**. Causa doble: (a) la proyección
   `2×coste@16` fue lineal, pero el coste real a 32 turnos crece con el
   historial acumulado (114k → 752k = 6,6×); (b) el corte solo se aplicó
   *entre* celdas y la celda 2 era obligatoria. Lección para cualquier
   corrida futura: **presupuestar por celda con holgura de historial, no por
   redoble de turnos**.

### Acción

**Se consulta al dueño antes de lanzar HITO20** (regla §0). Opciones sobre
la mesa, con la evidencia encima: **(a)** B+C1+C2 desde el principio (su
escalera), **(b)** B+C1+C2+rediseño del canal de observación del bucle
(lecturas completas / multi-acción por turno — hoy estaría dentro de «arreglar
la base del bucle»), **(c)** replantear de otra forma. HITO20 no arranca sin
su decisión.
