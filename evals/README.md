# `evals/` — qué es cada cosa

75 ficheros en la raíz, más `results/` (89), `logs/` (37) y `preflight/`
(159). Esta es la
clase de cada uno, el decodificador de nombres y las reglas. Los
**veredictos por hito** no se duplican aquí: viven en la tabla «el Hito N»
de `CONOCIMIENTO.md` §8 (fuente única).

## Mapa por clases

| clase | n | dónde | qué es | regla |
|---|---|---|---|---|
| **Evidencia** `result_*.json` | 89 | `results/` | salida estructurada de cada corrida (gates, scores, usage, commits) | **intocable**: no se borra ni se edita; es la prueba de lo medido (mudada 2026-10-22) |
| **Runners** `run_*.py` | 22 | raíz | scripts de una corrida; su pareja es `results/result_<mismo nombre>.json` + `logs/run_<mismo nombre>.log` | se ejecutan con `.venv/bin/python`; los del pasado son de un solo uso (archivados) |
| **Evaluadores/utilidades** `.py` | 19 | raíz | `corpus_lock.py` (infra citada por código), `eval_q1_r4r5.py`/`eval_end2end.py`/`eval_retrieval.py`, `judge*.py`, calibradores, `diagnose_*`, `validate_golden.py` | `corpus_lock.py` + `CORPUS_LOCK.json` están **citados por `bibliotecario/` y tests** → no moverlos sin barrido |
| **Planes y reportes** `HITO*.md` + specs | 27 | raíz | 21 hitos (`HITO0-2.md` reportes; `HITO3-21_PLAN.md` planes con §0 estado → §5 cierre/veredicto; HITO20 **CERRADO NO CUMPLE** (§1 SATURA; §6 B abortado NO VIABLE POR COSTE); HITO21 **cerrado NO CUMPLE** 2026-10-24, b3 no adoptado) + `BENCHMARK_SPEC.md` (la regla), `BLUEPRINT_METRIC_DESIGN.md` (umbrales/decisiones), `PLAN_READING/POSICIONAL_PLAN/REPORT_BLIND/REPORT_COEVOLVE` | el "código constitucional": se citan por docenas de sitios → no moverlos |
| **Logs** `*.log` | 37 | `logs/` | stdout de su `run_<mismo nombre>.py` homónimo | históricos; leer como evidencia, no editar (mudados 2026-10-22) |
| **Datos** | 9 | `golden_*.jsonl` (datasets gold), `calib_r4_gold.json`, `game_tasks_expanded.yaml` (60 tareas, citado), `CORPUS_LOCK.json` | referenciados por tests/evals → no mover sin barrido |

## `sd_pilot/` — piloto `Sens(x)` (Hito 19, dominio `software_development`)

Arnés mínimo conmutable A1-A5 sobre 12 tareas duras; todo congelado en
§1.B de `HITO19_PLAN.md` (rutas, parámetros, ids, esquema de traza):

| fichero | qué es |
|---|---|
| `harness.py` | bucle observe-reason-act + herramientas (`read_file`/`write_file`/`run_tests`), PFs, regulación, skills, trazas |
| `variants.py` | `VARIANTS` A1-A5 (parámetros congelados) |
| `tasks.py` | `TASK_IDS` (12 H19) + `B_TASK_IDS`/`B_TASK_AXES` (12 B, multi-paquete), ejes de dureza, `lint_tasks()`, `qa_task()` |
| `build_b_tasks.py` | HITO20 §6: genera las 12 tareas B copiando/prefijando dos fixtures H19 (idempotente; no toca las originales) y ejecuta QA |
| `verifier.py` | pytest público (herramienta del agente) y oculto (`m_h(x)`) |
| `sens.py` | Pearson, `Q_h^(−x)`, gates U2-U7, umbrales congelados |
| `run_pilot.py` | modos `--g0` / `--oficial` / `--diagnostico` (HITO20 §0.1) / `--diagnostico-b` (§0.3, canal b) / `--corrida-b` (§1, matriz 17×12 canal b + brazo forzado) / `--hito21` (4 residuales + 4 controles, canal b3 experimental para reproducir HITO21, techo 1,8M) / `--b` (§6, 12 tareas *-b, canal b2, techo 4,2M) / `--presupuesto` (con `--base-b2` para B) / `--debug-celda` (BUILD) |
| `parse_tolerante.py` | HITO21 Fase A: recuperación acotada de `write_file` con triples comillas; idempotente si el JSON ya es válido |
| `fase_a_offline.py` | HITO21 Fase A: replay 0-tokens sobre `traces_corrb.sqlite` → `results/result_hito21_fase_a.json` |
| `observador.py` | informes por celda/turno desde `traces_*.sqlite` (canal de observación §0.3, E1.4) |
| `trazas_analisis.py` | Parte A reproducible (rachas ATASCADO/PROGRESA, §0.1) — fija el snippet ad-hoc original |
| `skills_pack/` | 4 skills congelados (idénticos en A4 y A5) |
| `sd_tasks/<id>/` | las 12 fixtures H19 y las 12 `*-b` de H20 §6: `TASK.md` + `workspace/` + `tests_hidden/` + `reference/` |
| `traces.sqlite`, `_run_state_oficial.json` | trazas TraceForge y estado por celda de la corrida oficial (reanudable) |
| `traces_g0.sqlite`, `traces_diag.sqlite`, `_run_state_diag.json` | trazas del G0, del diagnóstico HITO20 y estado por celda del diagnóstico |
| `traces_h21.sqlite`, `_run_state_h21.json` | trazas y estado de la corrida b3 de HITO21 (8 celdas) |
| `traces_b.sqlite`, `_run_state_b.json` | trazas y estado del intento B de HITO20 §6 (abortado en 3/60 celdas; no reanudar) |

Evidencia: `results/result_sens_sd_g0.json` (dictámen G0) y
`results/result_sens_sd_pilot.json` (corrida oficial) + `logs/sens_sd_g0.log`
y `logs/sens_sd_pilot_run.log`. Diagnóstico HITO20 (§0.1 del plan):
`results/result_sens_sd_diag_trazas.json` (Parte A, 0 tokens),
`results/result_sens_sd_diag.json` (Parte B) + `logs/sens_sd_diag_run.log`.
HITO21: `results/result_hito21_fase_a.json` (Fase A offline),
`results/result_hito21.json` + `results/informes_hito21/` (corrida b3,
cerrada NO CUMPLE por G3; b3 no adoptado). HITO20 §6 B (BUILD + intento abortado): `results/result_b_build_qa.json`
(12/12 referencia 100 %, vacío <100 %) y
`results/result_sens_sd_b_abort.json` (3/60 celdas, 626.036 tok,
extrapolación ~12M; no es resultado oficial).
Tests: `tests/test_sens_sd_pilot.py` (puros, sin LLM).

## `preflight/` (159 ficheros) — la evaluación **viva**

Estructurado por tema (no tocar su organización sin motivo): `suites/` y
`suites_v2/` (tests de comportamiento B-1), `juez_b2.py` + `rubricas/` (juez
multimodal B-2 y rúbricas ocultas ρ), `run_fase2_b2.py` (corrida oficial
H16 U1-U6), `run_fase2_b2_h17.py` + `prefiltro_b2.py` (corrida H17 con la
enmienda Opción B: prefiltro no-LLM + gate U7) y `movimiento_b2.py` +
`run_fase2_b2_h18.py` (corrida H18 con la enmienda híbrida: métrica M_mov
determinista + juez solo V/A), `pi_*.py`/`*.gd` (trazas Π y replay),
`lint_suites_v2.py`, `results/` (evidencia B-1/B-2), `fixtures/`,
`scripts/`. Reglas congeladas: ver §3 de `HITO16_PLAN.md`,
§1.B-§3 de `HITO17_PLAN.md`, §1.B-§3 de `HITO18_PLAN.md` y
§5.2.1/§5.2.2 de `BENCHMARK_SPEC.md`.
Decodificador de nombres de la evidencia H17: `result_fase2_b2_h17.json`
= corrida oficial F3 (NO CUMPLE, veredicto en `HITO17_PLAN.md` §5);
`result_fase2_b2_h17_f1.json` y `_f2.json` = intentos incompletos por
HTTP 503 del endpoint (conservados con su coste); `h17_f{1,2,3}_run.log`
= stdout de cada intento. Evidencia H18: `result_fase2_b2_h18.json`
= corrida oficial F1 (**CUMPLE**, Score_final 0.9187, veredicto en
`HITO18_PLAN.md` §5); `h18_run.log` = stdout.

## Decodificador de nombres

| patrón | significado |
|---|---|
| `HITO0.md`…`HITO2.md` | reportes de los hitos fundacionales (no eran planes) |
| `HITO3_PLAN.md`…`HITO21_PLAN.md` | plan + cierre del hito N (§5 = veredicto final; H17 cerrado NO CUMPLE 2026-10-22; H18 cerrado **CUMPLE** 2026-10-22; H19 cerrado NO CUMPLE 2026-10-23; H20 **CERRADO 2026-10-24 NO CUMPLE** (§1 SATURA; §6 B **ABORTADO NO VIABLE POR COSTE**: 3/60 celdas, 626.036 tok, extrapolación ~12M > techo 4,2M; BUILD 12/12 QA y modo `--b` quedan como artefactos); H21 **CERRADO 2026-10-24 NO CUMPLE** — G3, b3 no adoptado, default b2) |
| `result_fase<N>_h<X>.json` | evidencia de la fase N en el intento de hito X (serie de brazos H1…H21 de la fase 1) |
| `result_fase2_b2.json` | corrida oficial del **Hito 16** (B-2 etapa 2, U1-U6) |
| `result_q1_r4r5.json` | fila maestra de juicios del juez Q1 (columna `arm` = brazo) |
| `result_blind_*`, `result_abst_*` | ensayos ciegos de QA y pruebas de abstención |
| `result_smoke_*` | humo (coste mínimo, sin umbral) |
| `result_sens_sd_g0.json`, `result_sens_sd_pilot.json` | G0 humo y corrida oficial del **Hito 19** (`Sens(x)`); su stdout es `logs/sens_sd_g0.log` y `logs/sens_sd_pilot_run.log` |
| `result_sens_sd_diag_trazas.json`, `result_sens_sd_diag.json` | **Hito 20** §0.1: diagnóstico de celdas truncadas (Parte A 0 tokens, Parte B `max_turns=32`); stdout en `logs/sens_sd_diag_run.log` |
| `result_sens_sd_corridab.json`, `result_b_build_qa.json`, `result_sens_sd_b_abort.json` | **Hito 20** §1 (matriz canal b, SATURA), §6 B (QA de BUILD 0 tokens) y §6 B (aborto por coste: 3/60 celdas, 626.036 tok; no es resultado oficial) |
| `run_<X>.py` → `results/result_<X>.json` + `logs/run_<X>.log` | trío runner → evidencia → stdout del mismo experimento |
| `*_prev*.json` | corrida anterior conservada antes de repetir (historial, no borrar) |

## Cómo se ejecuta algo de aquí

- Siempre `.venv/bin/python`. Los runners de juez necesitan env:
  `Q1_API_KEY`/`Q1_BASE_URL` (patrón de export en `_endpoint()` de
  `preflight/juez_b2.py`; la clave sale de `.env`, nunca se imprime).
- Cada hito documenta su comando exacto en su plan. Las corridas oficiales
  se ejecutan **una vez** y su resultado va a la evidencia del punto anterior.
- Puerta antes de commit: ver `AGENTS.md` (raíz).

## Regla de mantenimiento

Al crear cualquier fichero nuevo en `evals/`, añádelo a la tabla de su clase
aquí. Si un día se mueve algo a subdirectorios, **el movimiento y el barrido
de todas las referencias (busca `grep -rn '<ruta_vieja>'` hasta 0 — en la
mudanza B2: 19 markdown y 40 .py, 22 rutas únicas) van en el MISMO commit
con la puerta verde**; un enlace roto en la cadena de evidencia es peor que
el desorden. Ojo con el sed: `s|evals/result_|evals/results/|g` **come el
prefijo `result_`** — guarda con `s|evals/result_|evals/results/result_|g`
y verifica con un path conocido. Los JSON y `.log` en sí **no se editan**:
solo cambian sus rutas en código y documentación.
