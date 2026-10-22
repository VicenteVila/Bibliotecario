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
| **Planes y reportes** `HITO*.md` + specs | 24 | raíz | 18 hitos (`HITO0-2.md` reportes; `HITO3-17_PLAN.md` planes con §0 estado → §5 cierre/veredicto; `HITO17_PLAN.md` está en fase de declaración, sin §5) + `BENCHMARK_SPEC.md` (la regla), `BLUEPRINT_METRIC_DESIGN.md` (umbrales/decisiones), `PLAN_READING/POSICIONAL_PLAN/REPORT_BLIND/REPORT_COEVOLVE` | el "código constitucional": se citan por docenas de sitios → no moverlos |
| **Logs** `*.log` | 37 | `logs/` | stdout de su `run_<mismo nombre>.py` homónimo | históricos; leer como evidencia, no editar (mudados 2026-10-22) |
| **Datos** | 9 | `golden_*.jsonl` (datasets gold), `calib_r4_gold.json`, `game_tasks_expanded.yaml` (60 tareas, citado), `CORPUS_LOCK.json` | referenciados por tests/evals → no mover sin barrido |

## `preflight/` (159 ficheros) — la evaluación **viva**

Estructurado por tema (no tocar su organización sin motivo): `suites/` y
`suites_v2/` (tests de comportamiento B-1), `juez_b2.py` + `rubricas/` (juez
multimodal B-2 y rúbricas ocultas ρ), `run_fase2_b2.py` (corrida oficial
U1-U6), `pi_*.py`/`*.gd` (trazas Π y replay), `lint_suites_v2.py`,
`results/` (evidencia B-1/B-2), `fixtures/`, `scripts/`. Reglas congeladas:
ver §3 de `HITO16_PLAN.md` y §5.2.1/§5.2.2 de `BENCHMARK_SPEC.md`.

## Decodificador de nombres

| patrón | significado |
|---|---|
| `HITO0.md`…`HITO2.md` | reportes de los hitos fundacionales (no eran planes) |
| `HITO3_PLAN.md`…`HITO17_PLAN.md` | plan + cierre del hito N (§5 = veredicto final; H17 aún en declaración, sin §5) |
| `result_fase<N>_h<X>.json` | evidencia de la fase N en el intento de hito X (serie de brazos H1…H21 de la fase 1) |
| `result_fase2_b2.json` | corrida oficial del **Hito 16** (B-2 etapa 2, U1-U6) |
| `result_q1_r4r5.json` | fila maestra de juicios del juez Q1 (columna `arm` = brazo) |
| `result_blind_*`, `result_abst_*` | ensayos ciegos de QA y pruebas de abstención |
| `result_smoke_*` | humo (coste mínimo, sin umbral) |
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
