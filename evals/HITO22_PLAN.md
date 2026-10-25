# Plan HITO22 — SD-2: benchmark de reparación con feedback y split dev/test

> **Estado: RATIFICADO por el dueño 2026-10-24.**
> Ratificado §1-§6 y el techo nuevo de **3.500.000 tokens**; alcance **12 dev +
> 12 test** y vertical slice previo. H19/H20 quedan congelados como **SD-1**;
> SD-2 es una línea nueva con línea base nueva, no una mutación de SD-1. La
> autoría y el QA son de 0 tokens; la calibración no se lanza hasta que el
> BUILD esté completo y el test congelado.

## §0 — Por qué H22 y qué se mide

H19 cerró **NO CUMPLE** (U7: media global 70,43 > 60; A1 media 97). H20 §1
midió **SATURA** con 63/63 celdas (media 82,47; A1 sigue siendo el mejor) y
H20 §6 B midió que **multi-paquete no baja a A1**: 100 en la tarea combinada,
626.036 tokens en 3/60 celdas, extrapolación ~12M. El eje “más código/paquetes”
está agotado.

**Pregunta de H22**: ¿se puede construir un benchmark cuyo éxito dependa de
**iteración con feedback** y que tenga **headroom medido antes de la corrida
oficial**, sin tocar SD-1 ni elegir tareas mirando el score de A1?

H22 es un hito de **construcción de benchmark**, no una comparación de arneses.
Si la calibración no produce headroom, H22 cierra **NO CUMPLE** con evidencia y
**no se lanza la matriz oficial**.

## §1 — Base metodológica (leída antes de codificar)

- **PROPOSITO.md**: benchmark inmutable; si cambia, es benchmark nuevo con línea
  base nueva; prohibido *teaching to the test* y bajar umbrales.
- **Stop Comparing LLM Agents Without Disclosing the Harness**: el score es
  conjunto `B(M,H)`; se exige **Harness Card**, protocolo factorial (5 arneses,
  modelo fijo) y reporte de componentes de varianza. Sin Harness Card no hay
  nota publicable.
- **Evo-Bench**: la dificultad y la sensibilidad al arnés **se miden**, no se
  suponen; validación y evaluación deben ser disjuntas; el modelo policy queda
  fijo. H22 adopta el split disjunto y la calibración de headroom, pero **no**
  selecciona tareas del test con scores: el test se congela antes de calibrar.

**Regla anti-Goodhart**: las tareas se autoran desde el constructo (§2), no
desde los scores de A1. La calibración es un **stop/go**, no un bucle de
“endurecer hasta que A1 falle”. Si falla, se para; no se editan tareas.

## §2 — Constructo y tareas

### 2.1 Constructo declarado: reparación dependiente de feedback

Una tarea pertenece a SD-2 si:

1. el workspace arranca con **≥1 test público fallando**;
2. los tests ocultos cubren comportamiento que los públicos no enumeran;
3. el camino esperado exige **al menos un ciclo ejecutar tests → diagnosticar
   → escribir → re-ejecutar** (no un cambio cosmético);
4. el requisito está en `TASK.md`; no hay requisitos solo en tests ocultos.

### 2.2 Familias (3) y reparto

| familia | qué exige | tests públicos | tests ocultos |
|---|---|---|---|
| **F1 `bugfix`** | 2-4 bugs sembrados; diagnosticar y corregir sin romper lo que pasa | fallan al inicio | límites, regresión, casos no mostrados |
| **F2 `contract`** | contrato parcialmente ejemplificado; completar bordes/errores | fallan en algunos casos | bordes, errores, idempotencia |
| **F3 `refactor`** | cambio de API/comportamiento preservando invariantes | fallan para la API nueva | compatibilidad e invariantes |

- **12 dev**: 4 dominios (`inventory`, `reservations`, `payroll`, `routing`)
  × 3 familias.
- **12 test**: 4 dominios **distintos** (`banking`, `healthcare`, `logistics`,
  `media`) × 3 familias.
- Cada tarea es un workspace independiente, **un solo paquete**, 3-6 ficheros
  de código, 4-6 tests públicos, 10-15 ocultos, `reference/` y `tests_hidden/`
  fuera del workspace. Sin red, determinista, suite <10 s.
- `TASK.md` da el contrato y dice que los tests públicos fallan, pero **no
  revela cuántos defectos hay ni en qué ficheros están**; el diagnóstico sale
  de ejecutar tests y leer el paquete.
- IDs: `sd2-dev-f1-inventory`, `sd2-test-f2-banking`, etc.
- **Vertical slice primero**: 1 dev F1 + 1 test F1, QA y revisión del dueño;
  solo después se autoran las 22 restantes. El slice test queda dentro del test
  y se congela con el resto.

### 2.3 Congelación

`evals/sd_pilot/SD2_LOCK.json` guarda SHA-256 de todos los ficheros de las 24
tareas y del split. El test se congela **antes** de la calibración. El runner
`--sd2-oficial` verifica el lock y aborta si algo cambió. Ninguna tarea se edita
después de calibrar; un cambio sería **SD-3**, no H22.

## §3 — BUILD (0 tokens LLM)

Artefactos previstos:

- `evals/sd_pilot/sd_tasks_v2/<id>/` — 24 tareas.
- `evals/sd_pilot/sd2_tasks.py` — IDs, familias, dominios, split, lint y QA
  (reutiliza `verifier.py`; no modifica `tasks.py` de H19).
- `evals/sd_pilot/sd2_sens.py` — gates nuevos, bootstrap y varianza; no
  modifica `sens.py`.
- `evals/sd_pilot/run_sd2.py` — modos `--calibracion`, `--oficial`,
  `--presupuesto`; reutiliza `harness.py`/`variants.py`/`verifier.py`.
- `evals/sd_pilot/SD2_LOCK.json`, `tests/test_sd2.py`.
- `evals/HARNESS_CARD_SD2.md` — A1-A5, modelo, prompts, herramientas, contexto,
  turnos, snapshots y presupuesto.

**QA de BUILD**: 24/24 con referencia 100 % oculta y 0 fallos públicos; vacío
con ≥1 fallo público y <100 % oculto; lint (≥2 ejes, 4 públicos, 10 ocultos,
3 ficheros); sin tests ocultos ni `reference/` dentro del workspace; lock
correcto. Evidencia `evals/results/result_sd2_build_qa.json`. **Cero llamadas
LLM.**

## §4 — Calibración dev (stop/go barato)

- 12 dev × **A1 y A5** = 24 celdas; modelo fijo
  `nvidia/nemotron-3-ultra-550b-a55b`; `max_turns=12`; cap 100.000 tok/celda;
  **techo 700.000**.
- El test **no se toca** en esta fase.

| gate | criterio |
|---|---|
| **C1** | 12/12 celdas válidas, sin `infra_error` |
| **C2** | A1 media **≤85** y **≥8/12** tareas con A1<100 |
| **C3** | A5 media **≤85**, **≥8/12** con A5<100 y **A1−A5 ≥10** puntos |
| **C4** | coste total **≤700.000** |

Si C1-C4 no se cumplen: **parar**. No se lanzan las 60 celdas, no se editan
tareas y no se recalibra el mismo set. H22 cierra **NO CUMPLE** con el coste y
la causa documentados. Un rediseño sería SD-3.

Evidencia: `evals/results/result_sd2_calibracion.json`, log
`evals/logs/sd2_calibracion.log`, `traces_sd2_calibracion.sqlite` y
`_run_state_sd2_calibracion.json`.

## §5 — Corrida oficial (solo si C1-C4 pasan)

- 12 test × 5 variantes = **60 celdas**; `max_turns=12`; cap 150.000/celda;
  **techo 2.800.000**. Proyección al arrancar: si supera el techo, se para y se
  consulta.
- **U1** variantes, modelo y turnos congelados.
- **U2** 60/60 celdas, sin huecos.
- **U3** `spread Q_h ≥15`.
- **U4** `Sens(x)` finito en **≥6/12**.
- **U5** `Sens(x)>0` en **≥6/12**.
- **U7** media global **≤60**; media A5 **≤80**; A5<100 en **≥8/12**.
- **U8 (headroom)** A1 media **≤80** y A1<100 en **≥8/12**.
- **U9** coste **≤2.800.000**.
- **U10 (integridad)** lock del test intacto, sin ediciones, sin fuga dev→test
  y Harness Card presente.

U7 y U8 son los gates primarios de saturación; U3-U5 validan `Sens(x)`. Todos
deben pasar para **CUMPLE**. Se reportan IC95 bootstrap (10.000 iteraciones,
semilla fija `20261024`) de medias y `Sens(x)`, y una descomposición descriptiva
de varianza (tarea/arnés/residual) sin convertirlo en gate.

Evidencia: `evals/results/result_sd2.json`, log `evals/logs/sd2_oficial.log`,
`traces_sd2.sqlite`, `_run_state_sd2.json`.

## §6 — Presupuesto y disciplina

- **Presupuesto nuevo H22: 3.500.000 tokens** (no se reutiliza el remanente de
  H20): calibración ≤700.000 + oficial ≤2.800.000.
- Base de proyección: costes H19 a 12 turnos; calibración ~0,56M y oficial
  ~2,2M, con margen. Si la proyección real al arrancar supera el techo, no se
  lanza.
- Corte por celda y entre celdas; celdas cortadas se documentan y excluyen del
  análisis. `infra_error` se documenta y no se re-ejecuta.
- Commits: (1) este plan, (2) vertical slice + tests, (3) 24 tareas + QA + lock,
  (4) calibración + §7, (5) oficial + cierre. Puerta verde antes de cada uno.
- Evidencia `result_*.json`, trazas y logs **intocables**; se añaden con `-f`
  si gitignore lo exige. No se toca SD-1 ni los ficheros del dueño.
- Sin C2, sin modelo débil, sin acelerador y sin cambios de umbrales.

## §7 — Cierre

### Cierre H22 — NO CUMPLE (2026-10-25)

La calibración dev se detuvo anticipadamente al comprobar que **C2 era
imposible**; no se lanzó la corrida oficial y no se editó ninguna tarea.

- **Ejecución**: 9/24 celdas (5 A1 + 4 A5), modelo
  `nvidia/nemotron-3-ultra-550b-a55b`, `max_turns=12`, cap 100.000/celda.
  Parada a los **213.859 tokens** de 700.000 (53 llamadas; 185.732 prompt +
  28.127 completion).
- **C1** ❌ parcial `4/12` tareas con A1/A5 válidas: la parada impide
  completar el set; no se usa como veredicto.
- **C2** ❌ media A1 **100,0**; `0/12` con A1<100. Las **5 celdas A1 medidas
  dieron 100** (inventory F1/F2/F3 y reservations F1/F2); aunque las 7
  restantes bajaran de 100, el máximo posible sería `7/12 < 8/12`. **C2
  imposible**.
- **C3** ❌ parcial: media A5 **81,6176**; `2/12` con A5<100; A1−A5
  **18,3824**. No se completa al parar por C2.
- **C4** ✅ **213.859 ≤ 700.000**.
- **Causa**: A1 one-shot resolvió inventory y reservations sin iteración;
  no hay headroom medido. Se para sin editar tareas ni recalibrar el mismo
  set. **No hay §5**; H22 cierra **NO CUMPLE**. Un rediseño sería **SD-3**.
- **Evidencia**: `evals/results/result_sd2_calibracion.json`,
  `evals/logs/sd2_calibracion.log`,
  `evals/sd_pilot/traces_sd2_calibracion.sqlite` y
  `evals/sd_pilot/_run_state_sd2_calibracion.json`. Lock
  `d702ac80ffc9d4f8e43088dd19e669e5cde39dfdebe2a9c7022532f4d6812609`
  intacto; Harness Card en `evals/HARNESS_CARD_SD2.md`.

Regla general: si la calibración falla, §7 registra C1-C4, coste, causa y
**NO CUMPLE**; no hay §5. Si la oficial se ejecuta, §7 registra gates, IC,
varianza, coste y veredicto **CUMPLE / NO CUMPLE**. Un fallo de U8 se reporta
como saturación, no como bug. La Harness Card se publica con el resultado; sin
ella no hay nota.

## §8 — Qué NO se hace

- No reabrir H20, no reutilizar las tareas `*-b`, no multi-paquete.
- No bajar U7/U8 ni cambiar el test después de ver scores.
- No elegir tareas del test con A1/A5; el test se congela antes.
- No usar el remanente de H20 sin declararlo; no cambiar de modelo.
- No publicar un score sin Harness Card.

## §9 — Siguiente paso

1. **RATIFICADO 2026-10-24**: §1-§6 y techo **3.500.000**.
2. Vertical slice (2 tareas, 0 tokens), QA y revisión del constructo.
3. Si el slice se aprueba: 24 tareas, QA, lock y congelación del test.
4. Solo entonces: calibración dev; si C1-C4 pasan, oficial.
5. **H22 cerrado NO CUMPLE 2026-10-25** (§7): calibración parada por C2;
   oficial no ejecutado. SD-3 no iniciado.
