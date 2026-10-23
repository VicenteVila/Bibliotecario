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

---

## §0.3 — Diagnóstico escalado-b: protocolo DECLARADO (2026-10-23, ratificado por el dueño)

> Origen: decisión del dueño en `Decisión sobre la escalera HITO20.txt`
> (b, pero primero como diagnóstico escalado a 3 tareas con cap por turno y
> criterio de «aclara» pre-registrado; recalibrar coste antes de comprometer
> 17×12; si b no aclara ni con lecturas completas, c se justifica ya con
> datos — apuntando al canal de observación y al modelo de coste, no al loop
> entero). Ratificación del dueño con 4 ajustes: **CAP 18.000**; **margen
> 25-30 %** (se aplica 30 %, el conservador); **pre-registro de
> `infra_error`** (celdas que agotan reintentos se excluyen de E1; <2
> válidas → E3 por infraestructura); **test explícito de preservación de la
> entrada inicial bajo poda** en la puerta de BUILD.

### Pregunta única

¿Con **lecturas completas + multi-acción por turno + cap por turno**, el
bucle progresa (escribe y sube score) y su coste por turno queda acotado?

### Celdas y condición

- Las mismas 3 celdas del diagnóstico §0.1 (comparabilidad directa):
  `A2_plugin-registry` (score@16=64,29 · A1=82,14 · 92.549 tok),
  `A5_repo-cache-layer` (41,67 · 100,00 · 114.467 tok),
  `A5_workflow-statemachine` (0,00 · 100,00 · 116.571 tok).
- `max_turns=17`, modelo `nvidia/nemotron-3-ultra-550b-a55b` (fijo).
- Condición nueva = **canal b** (BUILD; el canal oficial de H19 queda
  intacto e intocado):
  1. **Lecturas completas**: `read_file` entrega hasta `_MAX_READ` (8.000
     chars) al historial (el oficial corta a `_MAX_TOOL_OUT`=2.500).
  2. **Multi-acción por turno**: se ejecutan todas las acciones JSON del
     turno en orden (el oficial solo la primera).
  3. **Cap por turno**: `CAP_PROMPT_TOKENS=18.000` tokens de input por
     llamada (estimación chars/4); al excederse, poda por antigüedad las
     entradas del historial **salvo la inicial**, con marcador
     `[N entradas antiguas omitidas por cap de turno]`.
  4. **C1 robustez**: los fallos de red transitorios (URLError / name
     resolution / 503 …) se clasifican retryable y reintentan con backoff
     (el A2 del §0.1 murió por DNS sin reintento).
  5. **Snapshots**: score oculto en los turnos 8 y 12 (copia de workspace +
     verificador determinista, **0 tokens LLM**) — curva intra-celda.
  6. **Observabilidad**: `evals/sd_pilot/observador.py` (informe por
     celda/turno desde las trazas) y el analizador de rachas de la Parte A
     quedan guardados como herramientas reproducibles.
- **Techo total 1.500.000 tokens**; **tope duro 450.000 por celda** con
  corte mid-cell documentado (lección del incidente 759k: cap por llamada +
  cap por celda, no solo corte entre celdas). Con CAP=18k el techo queda
  holgado (3 × ~376k ≈ 1,13M + overhead).

### Criterio «aclara» pre-registrado (E1/E2/E3)

`Δscore = score@17(canal b) − score@16_oficial` (misma celda). **Celdas
`infra_error`** (`llm_error` no vacío tras agotar reintentos):
**excluidas** del recuento de E1/E2; si quedan **<2 celdas válidas → E3
por infraestructura** (consulta al dueño; no se concluye nada sobre el
canal).

- **E1 ACLARA** (las 4, sobre las celdas válidas):
  1. ≥2/3 con Δscore ≥ **+10**;
  2. ≥2/3 con **≥1 `write_file`**;
  3. ≥2/3 sin corte de 450k **y** pendiente de tokens/turno de los últimos
     5 turnos ≤ media de los primeros 5 (el cap acota; celda que termina
     `final` antes del turno 10 se considera acotada);
  4. los 3 informes del observador existen y son legibles.
- **E2 NO_ACLARA**: ninguna celda con Δ > +5, **o** las válidas todas con
  0 writes → «c» justificado con datos (canal de observación + modelo de
  coste, no el loop entero); **no hay corrida 17×12**; se redacta la
  propuesta de c para ratificación del dueño.
- **E3 AMBIGUO**: el resto (incluido <2 válidas por `infra_error`) → se
  para y se consulta.

### Recalibración de coste pre-registrada (antes de comprometer 17×12)

`factor_i = tok@17_canal_b / tok@16_oficial` por celda medida. Proyección
17×12 = A1 oficial fijo + (A2…A5 oficiales × **el peor factor medido**;
A3/A4 con el máximo de los factores medidos) ×12, **+30 % de margen**
(conservador del rango 25-30 % fijado por el dueño). **Si proyecta >7M →
no se lanza y se consulta al dueño.**

### Saturación (queda para §1)

El diagnóstico **valida el mecanismo de snapshots, no la conclusión de
saturación, que se decide en §1 con 12 pares** (score@12 vs @17 emparejado
por tarea, IC95 bootstrap de Δ positivo → no satura → «c» justificado para
HITO21; si no → satura → «c» cancelado).

### Alcance lateral declarado

Tareas = las 12 congeladas de H19; **B** (tareas endurecidas nuevas) y
**C2** (modelo débil) **no entran en esta fase**; si se quieren, se añaden
por enmienda al ratificar §1.

### Disciplina de commits (§4)

Declaración → BUILD+tests → corrida+evidencia+cierre §0.3. Evidencia:
`evals/results/result_sens_sd_diagb.json` + log `sens_sd_diagb_run.log` +
`evals/sd_pilot/traces_diagb.sqlite` + `_run_state_diagb.json`.

### §0.3 Resultado (CERRADO 2026-10-23 → **E1_ACLARA**)

Corrida única 2026-10-23 13:30-13:38 (~7,5 min), canal b, 17 turnos, 3
celdas, techo 1,5M. **Coste total: 77.441 tokens** (19 llamadas; sin
cortes; 0 `infra_error`; sin 429/DNS — la clave PILOTO y el clasificador
C1 quedaron activos pero no hicieron falta en esta corrida).

| celda | @16 oficial | @17 canal b | Δ | A1 | writes | paro | tok@16 | tok@17 | factor |
|---|---|---|---|---|---|---|---|---|---|
| A2_plugin-registry | 64,29 | **100,00** | +35,71 | 82,14 | 2 | final@6 | 92.549 | 21.259 | 0,23 |
| A5_repo-cache-layer | 41,67 | **100,00** | +58,33 | 100,00 | 1 | final@4 | 114.467 | 18.841 | 0,16 |
| A5_workflow-statemachine | 0,00 | **100,00** | +100,00 | 100,00 | 2 | final@9 | 116.571 | 37.341 | 0,32 |

**E1 cumplida en las 4 condiciones**: Δ≥+10 en 3/3; writes≥1 en 3/3; sin
corte ni pendiente creciente (máx 7.293 tok/turno; el cap 18k nunca bindió:
es guarda, no restricción activa); informes legibles (3/3,
`evals/results/informes_diagb/`). E2/E3 no aplican. Snapshots: solo
A5_workflow llegó al turno 8 (`score@8=0.0` → final@9=100) — el mecanismo
funciona; las otras dos terminaron antes (4 y 6 turnos).

**Lectura técnica (el reverso del diagnóstico §0.1)**: el colapso del
oficial no era «faltan turnos» ni «faltaba presupuesto»: era el **canal de
observación**. Con lecturas completas + multi-acción, las celdas leen todo
lo necesario en 1-2 turnos, escriben y terminan con `final` antes del
turno 9, con score 100 y **4-6× más baratas**. Los arneses A2/A5 no están
rotos: estaban ciegos y mancos (2.500 chars por lectura, 1 acción por
turno).

**Recalibración de coste (§0.3)**: factores 0,23/0,16/0,32 → proyección
17×12 = **2.042.105 tokens con margen 30 %** (COSTE_OK; 3,4× por debajo
del techo de 7M). La corrida 17×12 con canal b es viable.

**Consecuencias declaradas**: E1 → se redacta **§1** (17×12 con canal b,
techo declarado 2,1M, criterio de saturación) para ratificación del dueño.
C2 (modelo débil) y (c) replanteo quedan sin soporte empírico por ahora.
Nota honesta para §1: con canal b las celdas terminan antes del turno 12
→ el criterio emparejado @12 vs @17 daría Δ≈0 por definición (saturación
trivial = DONE); §1 propondrá una curva distinta (snapshots en turnos
tempranos 2/4/6/8 sobre las celdas que no terminan, y/o el contraste
oficial@16 vs b@17 ya medido).

Evidencia: `evals/results/result_sens_sd_diagb.json`, informes
`evals/results/informes_diagb/` (3 .md), log
`evals/logs/sens_sd_diagb_run.log`, trazas
`evals/sd_pilot/traces_diagb.sqlite` + `_run_state_diagb.json`. Commits:
declaración `4bbe48a`, BUILD `645b063`, evidencia+cierre (este).
