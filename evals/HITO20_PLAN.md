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

---

## §1 — Corrida oficial 17×12 con canal b (PLANTILLA CONDICIONAL)

> **Estado**: PLANTILLA DECLARADA 2026-10-23 tras **E1_ACLARA** (§0.3). **No
> autoriza corrida**: la corrida solo se lanza tras (i) commit de §1
> definitivo con los números inyectados en §1.3 y (ii) visto bueno del
> dueño. Los umbrales de §1.1-§1.2 quedan pre-registrados aquí; el techo
> es una **fórmula derivada**, no un número comprometido.

### §1.0 — De dónde sale el techo (derivation, anti-6,13M)

Las dos proyecciones modelan cosas distintas y esto queda escrito para que
nadie (incluido el agente dentro de dos semanas) las confunda:

- **6.131.772** (`--presupuesto` cúbico, PRE canal b): supone que TODAS las
  celdas de bucle gastan los 17 turnos con historial creciente; calibrado
  en celdas atascadas de H19 + A5_repo@30. Es el techo del arnés VIEJO.
- **El canal b cuesta MÁS por turno** (medido: A2 serie
  [1014,1250,3804,3839,4059,**7293**] tok/turno; el oficial de A2
  promediaba ~5,8k) **pero las celdas convergen y paran**: en §0.3 las 3
  celdas terminaron con `final` en los turnos **4/6/9** (no 16-17).
- La proyección de §1 aplica el **factor medido** por celda (§0.3
  pre-registró la receta antes de correr): `12 × Σ base_oficial(v) ×
  factor_v`, con factores E1 = 0,2297 (A2) y 0,3203 (máx, A3/A4/A5):
  **1.570.850** sin margen.
- **Sesgos declarados** (por eso el techo es fórmula, no número):
  (a) factores de 3 celdas, y eran las atascadas (más beneficiadas);
  (b) las bases por variante incluyen celdas que ya terminaban solas y
  reciben factor de atascada → proyección **conservadora hacia abajo**;
  (c) celda que no converja y llegue a 17 con canal b ≈ factor 0,66
  (17 turnos al ritmo medido de A5_workflow), no 0,32.

### §1.1 — Estructura (pre-registrada; no depende de inyección)

- **17 turnos × 12 tareas** congeladas de H19 × 5 variantes A1-A5, **canal
  b** idéntico al diagnóstico (código congelado en `645b063`: lecturas
  completas, multi-acción, snapshots).
- **Toco duro 450.000 tokens por celda** (mid-cell, corta y documenta) y
  corte entre celdas al techo de §1.3. Celdas cortadas se marcan
  `cortada` y se excluyen del análisis de saturación primario.
- **`infra_error`**: mismas reglas que §0.3 (celdas con `llm_error` tras
  agotar reintentos se excluyen de análisis; no se re-ejecutan).
- Snapshots: **turno 12** (primario) y **2/4/6/8** (descriptivos, sin
  test — apoyo visual de la curva).

### §1.2 — Criterio de saturación primario (pre-registrado)

- Par por tarea: `Δ_i = score@12_i − score@final_i` donde `final` es el
  estado al turno 17 (o el `final` temprano; celda terminada antes del
  12 → score@12 = score@final → Δ=0). 12 pares.
- **IC95 bootstrap por remuestreo de pares (10.000 iteraciones, semilla
  fija 20261023)** sobre la media de Δ.
- Si el IC95 de la media de Δ es **positivo (excluye 0)** → el agente
  **NO satura** a 17 → (c) justificado para HITO21; si no → **satura** →
  (c) cancelado. Un solo test primario; los snapshots 2/4/6/8 no generan
  hipótesis adicionales (anti falsos positivos por comparaciones
  múltiples).
- Nota de lectura declarada: con canal b muchas celdas terminan antes
  del 12; Δ=0 masivo es saturación por DONE (respuesta legítima), no un
  bug del criterio.

### §1.3 — Techo (FÓRMULA; los números se inyectan, no se comprometen)

```
techo_corrida = min(7.000.000 − gastado_HITO20, proyección_17×12 × 1,30)
proyección_17×12 = 12 × Σ_v base_oficial(v) × factor_v × 1,30
factor_A1 = 1 (one-shot fijo); factor_A2/A3/A4/A5 = medidos en §0.3
```

- **Valores inyectados hoy (2026-10-23, tras E1)**: factores
  A2=0,2297 · A3/A4/A5=0,3203 (máx de las celdas medidas) ·
  proyección sin margen = **1.570.850** · gastado §0.3 = **77.441** →
  **techo derivado = 2.042.105**.
- **Si al inyectar la proyección supera 7M → NO se lanza y se consulta**
  (regla pre-registrada, §0.3).
- Este techo se **rederiva al inicio de la corrida oficial** con los
  valores vigentes de gastado y factores; si difiere del valor de arriba
  por más del margen, se documenta en el log antes de arrancar.

### §1.4 — Herencias y márgenes

- **Margen 25-30 %** (fijado por el dueño en §0.3): se aplica **30 %**
  (conservador); la referencia empírica del margen es el 69 % de desvío
  del §0.1 previo.
- **Cap por turno 18.000**: **heredado** de §0.3 donde nunca bindió
  (máx 7.293 tok/turno observado); si la corrida oficial lo bindió de
  forma recurrente, se documenta y solo se cambia por enmienda declarada
  ANTES de re-ejecutar celdas afectadas.
- Canal b y snapshot@12 congelados con el BUILD `645b063`; el canal
  oficial de H19 permanece intocado.

### §1.5 — Qué NO queda fijado aquí

- **Ningún techo numérico como compromiso** (es derivado de §1.3).
- Ningún gate de score nuevo (si el dueño quiere gates de la corrida
  oficial, se declaran en la enmienda de §1 definitivo, antes de medir).
- Modelo (fijo `ultra-550b` por decisión previa) y B/C2: sin cambios
  respecto a §0.3 (alcance lateral declarado allí).

### §1.6 — Disciplina

Commit de esta plantilla → inyección de números + visto bueno del dueño →
corrida única oficial (modo a declarar en §1 definitivo, sobre el patrón
`--oficial`) → §5 con veredicto de saturación y comparación vs H19
(descriptiva: la matriz oficial bajo canal b vs la de H19).

### §1 Enmienda 1 (ratificada por el dueño 2026-10-23: 3 ajustes + menor)

La plantilla §1 queda **ratificada con enmienda**; esta sección **suprime y
sustituye** §1.2 y §1.3 íntegramente. §1.0, §1.1, §1.4, §1.5 y §1.6
siguen en pie salvo donde se indique.

#### E1-Ajuste 1 — La saturación se mide con brazo de turnos forzados, no con @12 vs @17 natural

Se **suprime** el test primario @12 vs @17 sobre celdas con parada
natural: con convergencia temprana (final@4/6/9) ese test daría Δ=0 **por
construcción** (el agente paró, no saturó) y cancelaría (c) por un
artefacto del diseño. En su lugar:

- **Brazo forzado (ii)**: las **3 celdas del diagnóstico §0.3**
  (A2_plugin-registry, A5_repo-cache-layer, A5_workflow-statemachine)
  se re-corren con canal b y **parada temprana desactivada** (se ignora
  `final`; si el agente declara DONE, el harness le reprompta «continúa:
  revisa y mejora») hasta el **turno 17**. Coste estimado con los ritmos
  medidos: 111-142k tok/celda → **~0,39M** (coincide con el ~0,5M
  estimado por el dueño).
- **Test primario de saturación** (solo brazo forzado): `Δ_i =
  score@17_forzado − score@12_forzado` emparejado por celda (**n=3**);
  IC95 bootstrap (10.000, semilla 20261023). **Positivo (excluye 0) →
  NO satura → (c) justificado HITO21**; incluye 0 o negativo → **satura
  (turnos 12-17 no aportan ni forzados) → (c) cancelado**. Caveat
  pre-registrado: n=3 da potencia limitada; el veredicto se lee con la
  desviación por celda visible en la evidencia, no solo con el IC.
- **Fallback (i)**: si el checkpoint (E1-Ajuste 2) obliga a parar antes
  de completar el brazo forzado, §1 se cierra declarando explícitamente
  que **mide convergencia, no saturación**, y la pregunta de (c) queda
  para HITO21 con otro diseño (no se cancela (c) por falta de dato).
- Los snapshots 2/4/6/8 de la matriz principal quedan **descriptivos**
  (apoyo visual de la curva), sin hipótesis ni test.

#### E1-Ajuste 2 — Techo duro 7M con checkpoint en 2,65M (se suprime el corte a 2,04M)

Se **suprime** `techo_corrida = min(7M − gastado, proyección×1,3)` como
corte de corrida. Queda:

- **Techo duro global: 7.000.000 tokens** (pool HITO20; gastado §0.3 =
  77.441 descontado del ledger).
- **Checkpoint: 2.654.737 tokens** (= proyección recalibrada 2.042.105 ×
  1,3). Al alcanzarlo: **si <70 % de celdas completadas → se PARA y se
  consulta al dueño**; si ≥70 % → se continúa hasta 7M.
- **Tope por celda 450k** (mid-cell) permanece: protege contra celda
  desbocada, no contra el total (60 celdas × 450k = 27M teóricos; el 7M
  es el que acota).
- Si la corrida completa bajo 7M: se documenta la desviación vs
  proyección. Si se corta en 7M: **hallazgo fuerte** (el modelo de coste
  falla por factor ≥1,3; ver E1-Ajuste 3). La corrida NO se amplía jamás
  sin enmienda.

#### E1-Ajuste 3 — Derivación del peor caso (corrige y RETRACTA el 0,66 anterior)

El 0,66 citado en §1.0(c) era una extrapolación **sin fundamento**; se
retracta y se sustituye por esta derivación, hecha sobre las series
medidas de §0.3 (coste/turno creciente + aplanamiento por el **CAP
18k**, que limita el prompt a 18k tok ≈ máx ~20k tok/turno):

| celda (§0.3) | tok reales (turnos usados) | extrap. a 17 (crecimiento +0,7-0,9k/turno, techo ~11k) | vs su @16 oficial | factor peor caso |
|---|---|---|---|---|
| A2_plugin-registry | 21.259 (6) | ~136.400 | 92.549 | **1,47** |
| A5_repo-cache-layer | 18.841 (4) | ~142.200 | 114.467 | **1,24** |
| A5_workflow-statemachine | 37.341 (9) | ~110.900 | 116.571 | **0,95** |

- **Efecto del CAP, declarado**: sin poda, el historial crecería sin
  cota y los turnos 10-17 superarían los 20k tok/turno (factor ≫2); el
  CAP 18k es la pieza que aplana el crecimiento y deja el peor caso en
  0,95-1,47. Es el motivo de que el upper bound sea verificable.
- **Proyección superior de la matriz completa** (factor 1,0-1,22 según
  la media de la tabla): **6,66M-8,1M con margen**, es decir, el peor
  caso **puede exceder 7M**. E1-Ajuste 2 existe exactamente para esto:
  o se completa bajo 7M (y se documenta la desviación del modelo), o se
  corta en 7M como hallazgo. El escenario «4,42M» derivado del 0,66
  queda anulado.
- Los factores 0,16-0,32 de §1.3 inyectados siguen siendo los del caso
  **convergente** (medido); los de esta tabla son el caso **no
  convergente** (extrapolado). La corrida distingue ambos registrando
  por celda: turnos usados, paro (`final`/`max_turns`/`cortada`) y
  coste total — la comparación de esos tres campos con esta tabla es el
  test empírico del modelo de coste.

#### E1-Ajuste menor — Score absoluto de convergencia junto al Δ

El score absoluto al que converge cada celda se registra y se lee
**junto al Δ** (E1 y saturación): Δ≥+10 con score final 15 no es lo
mismo que Δ≥+10 con score final 100. Los informes de observador y el
`result_*.json` ya lo contienen; queda explícito que la lectura del
veredicto usa ambos números.

#### Impacto en BUILD (pre-registrado antes de la corrida)

- Modo **brazo forzado** en harness/run_pilot (ignorar `final`,
  reprompt de continuación, snapshots @12/@17, ledger compartido con la
  matriz principal para el checkpoint).
- Lógica de **checkpoint 2.654.737** con regla 70 % y parada
  documentada.
- Tests puros: (a) forzado ignora `final` y para en 17; (b) checkpoint
  dispara parada/continúa según % de celdas; (c) ledger acumula matriz
  + brazo forzado. Puerta completa antes de la corrida.

### §1 Enmienda 2 (pre-registro complementario del dueño 2026-10-23: 3 críticos)

Suplementa §1 y Enmienda 1; no contradice nada de lo anterior.

#### E2-Crítico 1 — Granularidad de «celda» y cap 450k (ACLARADO, sin cambio de cap)

- **Celda = 1 variante × 1 tarea** (confirmado en código:
  `Cell(variant, task_id, ...)`); la matriz son **60 celdas** (12 tareas ×
  A1-A5) y el brazo forzado añade **3** (las celdas §0.3 re-corridas).
- **Corrección de lectura**: 1,47 / 1,24 / 0,95 de la tabla de E1-Ajuste 3
  son **factores** (tok@17_forzado / tok@16_oficial), no millones. El
  peor caso **por celda** es ~136.400 / ~142.200 / ~110.900 **tokens**,
  todos **bajo el cap 450k** con margen 3,2-4,0×. El cap **no trunca el
  peor caso por celda**; los 6,66-8,1M son el **total de la matriz**
  (dominio del techo 7M, no del cap). **El cap 450k queda sin cambio.**

#### E2-Crítico 2 — Orden de ejecución, truncamiento y análisis (PRE-REGISTRADO)

- **Orden**: estratificado por variante con **semilla 20261023**: por
  tercios, cada tercio del orden contiene 4 celdas de cada variante
  (20 celdas/tercio). El truncamiento no puede concentrar una variante.
- **Proyección por celda** (para las reglas del 80 %):
  `proy_celda = PRESUPUESTO_BASE_16[variante] × factor_inyectado`
  con `FACTORES_INYECTADOS = {A1:1.0, A2:0.2297, A3:0.3203, A4:0.3203,
  A5:0.3203}` (medidos en §0.3). Brazo forzado: 130.000 tok/celda.
- **Regla de truncamiento** (la celda en curso, al alcanzar el techo de
  7M): si su gasto < 80 % de `proy_celda` → **se completa** (overshoot
  documentado, acotado además por su cap 450k); si ≥ 80 % → **corte
  mid-cell** con `stopped_by = truncated_by_ceiling`. Celdas no iniciadas
  cuando el techo queda agotado: `no_ejecutada_por_techo`.
- **Análisis**: las celdas `truncated_by_ceiling` y
  `no_ejecutada_por_techo` se **excluyen de E1/E2/E3 y de la saturación
  primaria** y se reportan aparte. **Tasa de truncamiento >20 % es en sí
  un resultado** que justifica (c) con independencia del rendimiento.

#### E2-Crítico 3 — Reprompt del brazo forzado (PRE-REGISTRADO)

- **Texto exacto del reprompt** (inyectado por el harness en cada turno
  tras `final`):
  «Turno {n}/{total}. Revisa el estado, identifica una mejora concreta
  pendiente y ejecútala; si no hay ninguna, escribe SIN_MEJORA y explica
  por qué.»
- **Clasificación por turno forzado**: `write` si ejecuta ≥1
  `write_file`; `sin_mejora` si no escribe y la respuesta contiene
  `SIN_MEJORA` **o** consiste únicamente en reemitir `final`; `otro` en
  el resto. Ledger por celda: `forced_turns / forced_writes /
  forced_sin_mejora`.
- **Regla**: si ≥80 % de los turnos forzados son `sin_mejora` → celda
  marcada `convergencia_real`; su Δ se interpreta como **saturación
  genuina**. Si <80 %, Δ mide la mejora real por turnos forzados.

#### E2-Importante 1 — Reconciliación del coste del brazo forzado (0,39M)

0,39M = **suma de las extrapolaciones por celda** de E1-Ajuste 3
(136,4k + 142,2k + 110,9k = 389,5k). El 11k/turno citado es el **techo
por turno** bajo CAP 18k (18k prompt + ~2k salida), no la media: la
media del brazo forzado proyectado es ~6,5-8,3k tok/turno. Misma fórmula
que el 2,04M (extrapolación de series medidas, con aplanamiento por
CAP). Se compromete **~0,39M** con este desglose.

#### E2-Importante 2 — Regla de decisión del checkpoint (PRE-REGISTRADA)

Al alcanzar **2.654.737** con **<70 %** de celdas completadas (de las 63
previstas: 60 matriz + 3 brazo forzado), se evalúa la proyección total
restante (`acumulado + pendientes×26.181 + forzadas_pendientes×130.000`)
y se aplica **sin consulta en caliente** (árbol ratificado por el dueño):

| Proyección total | Acción pre-registrada |
|---|---|
| ≤ 7M | continuar hasta el techo |
| 7M – 8,5M | continuar **aceptando truncamiento** (la información de las completadas vale más) |
| > 8,5M | **reducir matriz**: solo una celda por variante (regla determinista: la tarea de mayor `usage.total_tokens` en H19 oficial para esa variante) + brazo forzado si el presupuesto queda |

≥70 % completadas al llegar al checkpoint → continuar sin drama. El
brazo forzado (test primario de saturación) se ejecuta **siempre que
quede presupuesto**; si el techo lo impide → **fallback (i)** declarado
en E1-Ajuste 1 (§1 mide convergencia, no saturación).

#### Tests exigidos por el dueño (puerta, antes de cualquier corrida)

1. Granularidad del cap: celda sintética del peor caso (~136k) con cap
   450k llega a 17 turnos sin corte `presupuesto`.
2. Orden estratificado (semilla, 4×variante/tercio) + regla del 80 %
   (completar vs `truncated_by_ceiling`).
3. Reprompt forzado: celda que converge en turno 4 → turnos 5-17
   producen `write_file` o `SIN_MEJORA` registrado en el ledger;
   ≥80 % sin_mejora → `convergencia_real`.

## §5 — Veredicto de la fase §1 (CERRADO 2026-10-24; corrige la primera redacción)

> **Errata declarada**: la primera versión de este §5 (commit `3e62021`)
> afirmaba «100 % de las celdas terminaron con `final`» y «≥80 % SIN_MEJORA
> en las tres celdas forzadas». **Ninguna de las dos se sostiene contra
> `result_sens_sd_corridab.json`**; se corrigen aquí con las cifras
> verificadas. La evidencia no se toca.

**Alcance**: esta fase cierra §1 (matriz 17×12 con canal b + brazo forzado).
**No** cierra HITO20 completo: **B (tareas endurecidas) no se ejecutó** en
esta fase (§0.3, alcance lateral declarado).

### Corrida

- 63/63 celdas (60 matriz + 3 forzadas); **2.686.674 tokens** (38,4 % del
  techo de 7M; 387 llamadas). Desviación vs proyección 2.042.105: **+31,6 %**
  (justo por encima del margen del 30 %; el upper bound 6,66-8,1M no ocurrió).
- **Truncamiento: 0/63**. Checkpoint 2.654.737: **no disparado**; el cruce
  ocurrió durante el brazo forzado, después de que la matriz ya estuviera
  completa (≥70 % → la regla pre-registrada habría dicho «continuar»). El
  chequeo solo se evalúa tras celdas de matriz: **hallazgo de proceso** para
  el Paso 2 (heartbeat/checkpoint también en el brazo forzado).
- Paradas: **42 `final` · 12 `one_shot` (A1) · 4 `max_turns` · 3
  `max_turns_forzado` · 2 `error_llm`**. La afirmación «100 % final» era falsa.
- `infra_error`: `A2_dsl-parser` (score 13,04) y `A2_cli-subcommand` (25,53),
  ambos «todos los proveedores LLM fallaron»; excluidos del análisis, no
  re-ejecutados (§1.1).

### Matriz (60 celdas comparables)

- Media **82,47** (H19: 70,43); Δ medio vs @16 oficial **+12,04**; 19 celdas
  con Δ≥+10; 3 con Δ<0. E1 se cumple sobre 58 válidas → **E1_ACLARA**.
- Por variante: A1 **98,49** · A2 **76,92** · A3 **83,72** · A4 **73,99** ·
  A5 **79,25**. Las 12 A1 son one-shot; las 48 restantes siguen el bucle
  canal b (media ~78,5).
- **24 celdas con 0 escrituras**: las 12 A1 por diseño + **12 no-A1**
  (4 `max_turns` + 8 que pararon con `final`). El canal b no elimina el
  modo «leer y no escribir» en todas las celdas.

### Saturación (test primario pre-registrado)

- Brazo forzado n=3: `score@12 = score@17 = 100` en las tres celdas;
  **Δ = [0,0,0]**; IC95 bootstrap **[0,0]** → **SATURA** (por regla
  pre-registrada: (c) cancelado).
- Ledger: A5_repo-cache-layer 10/10 `sin_mejora` y A5_workflow-statemachine
  13/13 → `convergencia_real`; **A2_plugin-registry 6/13 (46 %), no
  convergencia_real** (sus 7 turnos «otro» no produjeron ninguna escritura
  forzada). `forced_writes = 0` en las tres.
- **Caveat de techo**: las tres ya estaban a 100 en el turno 12; Δ=0 mide
  ausencia de mejora posible, no necesariamente agotamiento del bucle. La
  regla pre-registrada manda SATURA igualmente; n=3 y sin headroom quedan
  declarados.

### Residuales y veredicto

- **4 celdas `max_turns` con 0 escrituras** (A2_checkout-rounding 311.323 tok ·
  A3_checkout-rounding 327.999 · A4_dsl-parser 140.406 · A5_plugin-registry
  140.179) son el límite medido del canal b: la mejora no es universal.
- **Veredicto**: §1 **CERRADO**; saturación = SATURA → (c) cancelado como
  justificación general, con el residual de 4 celdas anotado para HITO21.
  El coste quedó bajo techo y la comparativa es E1_ACLARA. **HITO20 (B+C1)
  sigue pendiente**: esta fase fue el diagnóstico/canal, no el endurecimiento.

Evidencia: `evals/results/result_sens_sd_corridab.json` +
`evals/results/informes_corridab/` (63 .md), log
`evals/logs/sens_sd_corridab_run.log`, trazas
`evals/sd_pilot/traces_corrb.sqlite` y estado `_run_state_corrb.json`.

## §6 — B (tareas endurecidas): BUILD y protocolo (RATIFICADO 2026-10-24)

> **Estado**: **ABORTADO 2026-10-24 — NO VIABLE POR COSTE**. El dueño
> ratificó 12 tareas B multi-paquete, N=12 y techo 4.200.000. El BUILD y el
> modo B se validaron, pero la corrida se detuvo tras **3/60 celdas y
> 626.036 tokens**: el coste real extrapola a ~12M, muy por encima del techo.
> No hay `result_sens_sd_b.json` ni Score oficial; el intento queda
> documentado en §6.7. No reanudar.

### §6.0 — Qué pregunta B y por qué ahora

HITO21 midió que el canal b2 no basta: **G3 falló** y la media global subió
(72,28 vs 38,42 base) porque tres tareas se saturaron. HITO20 §1 midió que
con las tareas de H19 el agente **satura** (SATURA, IC95 [0,0]). B no repite
esas preguntas: mide si **tareas de mayor alcance** (dos paquetes por tarea,
mismo contrato congelado) bajan la saturación y la media global por debajo
del umbral U7. C1 (reintentos/robustez del canal b) ya está activo en b2; B
no cambia C1.

### §6.1 — Set de tareas (12, N=12)

Cada tarea B es un **monorepo con dos fixtures congeladas de H19**. No se
edita ningún original de H19: se copian workspace, reference, tests públicos
y tests ocultos; los tests se prefijan para evitar colisiones. El eje de
endurecimiento declarado es **`multi-paquete`** (alcance): el agente debe
satisfacer ambos contratos, no solo uno. La lista de pares es un ciclo:

| # | tarea B | paquete A | paquete B |
|---|---|---|---|
| 1 | `checkout-rounding-repo-cache-layer-b` | checkout-rounding | repo-cache-layer |
| 2 | `repo-cache-layer-dsl-parser-b` | repo-cache-layer | dsl-parser |
| 3 | `dsl-parser-interval-scheduler-b` | dsl-parser | interval-scheduler |
| 4 | `interval-scheduler-seeded-bugs-billing-b` | interval-scheduler | seeded-bugs-billing |
| 5 | `seeded-bugs-billing-cli-subcommand-b` | seeded-bugs-billing | cli-subcommand |
| 6 | `cli-subcommand-workflow-statemachine-b` | cli-subcommand | workflow-statemachine |
| 7 | `workflow-statemachine-batch-coalescer-b` | workflow-statemachine | batch-coalescer |
| 8 | `batch-coalescer-schema-validator-b` | batch-coalescer | schema-validator |
| 9 | `schema-validator-plugin-registry-b` | schema-validator | plugin-registry |
| 10 | `plugin-registry-csv-diff-engine-b` | plugin-registry | csv-diff-engine |
| 11 | `csv-diff-engine-config-migration-b` | csv-diff-engine | config-migration |
| 12 | `config-migration-checkout-rounding-b` | config-migration | checkout-rounding |

**Limitación declarada**: cada dominio aparece dos veces (una como paquete A
y otra como B), así que las 12 tareas B **no son independientes** entre sí.
B mide el efecto de duplicar alcance, no 12 dominios nuevos; `Sens(x)` se
calcula igual (12 tareas), pero la lectura de Q_h debe tenerlo en cuenta.
Si el dueño quiere dominios independientes, este set se sustituye antes de
la corrida y se rehace el BUILD.

### §6.2 — BUILD y QA (0 tokens LLM)

- Generador reproducible: `evals/sd_pilot/build_b_tasks.py` (idempotente;
  copia y prefija tests; no toca H19).
- Registro: `B_TASK_IDS`/`B_TASK_AXES` en `evals/sd_pilot/tasks.py`; las 12
  tareas de H19 siguen intactas.
- QA ejecutado: `lint_tasks(B_TASK_IDS) == []`; **12/12 referencia = 100 %
  ocultos**; **12/12 referencia pasa todos los públicos** (0 fallos); **12/12
  workspace vacío falla ≥1 público** y **<100 % ocultos** (mínimo 22,06,
  máximo 69,09). Evidencia: `evals/results/result_b_build_qa.json`.
- El QA de BUILD no es una corrida ni produce Score; solo certifica que la
  referencia y el suelo están bien construidos.

### §6.3 — Matriz y gates (pre-registrados; N=12)

- **60 celdas** = 12 tareas B × 5 variantes A1-A5; `max_turns=17`; **canal
  b2** (el default adoptado; **no b3**); sin brazo forzado (B no mide
  saturación forzada, mide U7). Orden **task-major** (tarea × A1-A5): si el
  techo corta, deja tareas completas.
- Cap por celda **450.000 tokens** (mid-cell, corta y documenta); corte entre
  celdas al techo de §6.4. Snapshots en turno 12 (descriptivo).
- **B0 BUILD**: §6.2 completo (12/12 QA) — ya cumplido.
- **B1 completitud**: 60/60 celdas puntuadas, sin `llm_error`, sin celdas
  cortadas ni no ejecutadas. Cualquier corte o error hace **B1 falla**; B2/B3
  se reportan pero quedan **no concluyentes**. No se excluye ninguna celda:
  los umbrales U3/U4/U5/U7 están fijados sobre 12 tareas y no se reescalan.
- **B2 Sens(x)**: U3 spread ≥15; U4 finitos ≥6/12; U5 positivos ≥6/12
  (umbrales de H19, **sin tocar**).
- **B3 U7 (primario)**: `media_global ≤ 60`; `media_A5 ≤ 80`;
  `a5_below_100 ≥ 8/12`. Es el mismo U7 de H19; N=12 permite reutilizarlo
  sin reescalar.
- **B4 coste**: total ≤ **4.200.000 tokens**; si la proyección B de §6.4
  supera el techo, **no se lanza**.
- **B5 canal**: las 60 celdas declaran `canal=b2` y `canal_b_version=b2`
  (ninguna b3).

**Lectura primaria**: si B3 pasa, B reduce la saturación medida por U7 en
este set; si falla, B **no** la reduce y el dueño decide C2/cierre. B2 es
condición de medida (si falla, no hay Sens válida). No se reinterpreta
`Score_final` como nota si B1/B4/B5 fallan.

### §6.4 — Techo y proyección

- Techo duro de B: **4.200.000 tokens** (ratificado por el dueño
  2026-10-24), dentro del remanente de H20
  (7.000.000 − 2.686.674 = 4.313.326).
- Proyección B pre-registrada: `12 × Σ_v base_b2(v) × 1,35 × 1,30`, con
  `base_b2` = media medida en H20 §1 (A1 5.469 · A2 47.182 · A3 67.491 ·
  A4 34.763 · A5 41.725 tok/celda), factor de alcance **1,35** y margen
  **1,30**. Resultado: **4.141.020** ≤ 4.200.000 (margen 58.980).
- El modelo cúbico de `--presupuesto` **no se usa en B**: H20 §1 midió que
  sobreestima (6,1M) porque las celdas b2 convergen y paran. Comando:
  `run_pilot.py --presupuesto --base-b2 --max-turns 17 --n-tareas 12
  --techo 4200000` -> `COSTE_OK`.
- **Riesgo declarado**: el margen es estrecho (1,4 % del techo); si el coste
  real supera 4,2M, B1/B4 fallan y no hay veredicto de score. No se amplía
  el techo tras medir sin enmienda del dueño.
- Evidencia esperada: `evals/results/result_sens_sd_b.json`,
  `evals/results/informes_b/`, `evals/logs/sens_sd_b_run.log`,
  `evals/sd_pilot/traces_b.sqlite`, `_run_state_b.json`.

### §6.5 — Disciplina

Commit del BUILD + §6 → ratificación (HECHA 2026-10-24) → implementación
del modo B + tests (HECHA) → proyección inyectada (HECHA) → corrida única →
cierre de §6 con veredicto.
Los originales de H19 y los umbrales de `sens.py` no se tocan. El QA de
BUILD (`result_b_build_qa.json`) se conserva como evidencia; no se borra.

### §6.6 — Estado de implementación

1. Ratificación del dueño: **HECHA** 2026-10-24 (12 multi-paquete, 4,2M).
2. Modo B en `run_pilot.py` (`--b`): **HECHO**; matriz
   `B_TASK_IDS × VARIANT_NAMES`, canal b2, `max_turns=17`, cap 450k,
   snapshots@12, estado/trazas/informes B y evaluador B0-B5. Tests puros
   de `evaluar_b`/`presupuesto_b` (sin LLM): verdes.
3. Proyección B inyectada: **HECHA** (§6.4, 4.141.020 ≤ 4,2M).
4. Corrida única: **ABORTADA** 2026-10-24 tras 3/60 celdas; ver §6.7.
   No reanudar (`--b --resume`).


### §6.7 — Intento B abortado (2026-10-24): NO VIABLE POR COSTE

**Decisión del dueño**: abortar y documentar, sin gastar el resto del techo.

- **Ejecutado**: 3/60 celdas, **626.036 tokens** (A1 16.447 · A2 303.687 ·
  A3 305.902). A2 y A3 alcanzaron `max_turns=17`; A2 hizo **0 escrituras** y
  A3 **21**. Scores: A1 **100** (one-shot), A2 **39,24**, A3 **93,67**.
- **Causa**: el alcance multi-paquete dispara lecturas/escrituras por celda
  (~304-306k en A2/A3). La proyección de §6.4 (4.141.020) queda invalidada;
  extrapolación ~12M para 60 celdas. A1 sigue resolviendo la tarea combinada
  al 100 %, así que B tampoco muestra evidencia de bajar U7 por dificultad.
- **Gates**: B0 **PASA** (QA BUILD 12/12); B1 **FALLA** (3/60); B2/B3 **no
  evaluados** (matriz incompleta); B4 **FALLA** por extrapolación (coste
  medido 626.036, techo 4.200.000); B5 b2 en las 3 celdas. No hay veredicto
  de score ni `CUMPLE`.
- **Evidencia**: `evals/results/result_sens_sd_b_abort.json` (registro de
  aborto, no resultado oficial), `evals/sd_pilot/_run_state_b.json`,
  `evals/sd_pilot/traces_b.sqlite`, `evals/logs/sens_sd_b_run.log`. El
  `result_sens_sd_b.json` **no existe** y no debe crearse a mano.
- **Contabilidad**: H20 acumula 2.686.674 + 626.036 = **3.312.710 tokens**
  (47,3 % de 7M); quedan 3.687.290. No se autoriza otra corrida B con este
  diseño.
- **Siguiente decisión (dueño)**: (a) cerrar H20 con B no viable; (b)
  rediseñar B más barato (p. ej. `max_turns=12`, tareas de un solo paquete
  endurecidas, o menos variantes con enmienda de umbrales) y declarar nuevo
  techo; (c) otra alternativa. **Nada de esto está autorizado todavía.**
