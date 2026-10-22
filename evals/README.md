# `evals/` — qué es cada cosa

199 ficheros en la raíz (más `preflight/` con 159). Esta es la clase de cada
uno, el decodificador de nombres y las reglas. Los **veredictos por hito** no
se duplican aquí: viven en la tabla «el Hito N» de `CONOCIMIENTO.md` §8
(fuente única).

## Mapa por clases (raíz)

| clase | n | qué es | regla |
|---|---|---|---|
| **Evidencia** `result_*.json` | 89 | salida estructurada de cada corrida (gates, scores, usage, commits) | **intocable**: no se borra ni se edita; es la prueba de lo medido |
| **Runners** `run_*.py` | 22 | scripts de una corrida; su pareja es `result_<mismo nombre>.json` + `run_<mismo nombre>.log` | se ejecutan con `.venv/bin/python`; los del pasado son de un solo uso (archivados) |
| **Evaluadores/utilidades** `.py` | 19 | `corpus_lock.py` (infra citada por código), `eval_q1_r4r5.py`/`eval_end2end.py`/`eval_retrieval.py`, `judge*.py`, calibradores, `diagnose_*`, `validate_golden.py` | `corpus_lock.py` + `CORPUS_LOCK.json` están **citados por `bibliotecario/` y tests** → no moverlos sin barrido |
| **Planes y reportes** `HITO*.md` + specs | 23 | 17 hitos (`HITO0-2.md` reportes; `HITO3-16_PLAN.md` planes con §0 estado → §5 cierre/veredicto) + `BENCHMARK_SPEC.md` (la regla), `BLUEPRINT_METRIC_DESIGN.md` (umbrales/decisiones), `PLAN_READING/POSICIONAL_PLAN/REPORT_BLIND/REPORT_COEVOLVE` | el "código constitucional": se citan por docenas de sitios → no moverlos |
| **Logs** `.log` | 37 | stdout de su `run_*.log` homónimo | históricos; leer como evidencia, no editar |
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
| `HITO3_PLAN.md`…`HITO16_PLAN.md` | plan + cierre del hito N (§5 = veredicto final) |
| `result_fase<N>_h<X>.json` | evidencia de la fase N en el intento de hito X (serie de brazos H1…H21 de la fase 1) |
| `result_fase2_b2.json` | corrida oficial del **Hito 16** (B-2 etapa 2, U1-U6) |
| `result_q1_r4r5.json` | fila maestra de juicios del juez Q1 (columna `arm` = brazo) |
| `result_blind_*`, `result_abst_*` | ensayos ciegos de QA y pruebas de abstención |
| `result_smoke_*` | humo (coste mínimo, sin umbral) |
| `run_<X>.py` → `result_<X>.json` + `run_<X>.log` | trío runner → evidencia → stdout del mismo experimento |
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
de todas las referencias (99 rutas en markdown, 71 en código) van en el MISMO
commit con la puerta verde**; un enlace roto en la cadena de evidencia es peor
que el desorden.
