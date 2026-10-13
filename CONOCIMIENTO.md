# Mapa de conocimiento

> **Documento de localización.** No explica *por qué* (eso es `PROPOSITO.md`) ni
> *con qué regla se mide* (eso es `evals/BENCHMARK_SPEC.md`). Explica **dónde
> está cada cosa** para poder llegar a ella cuando haga falta.
>
> Si se aprende algo nuevo, **se anota aquí con su ruta**. Un conocimiento sin
> ruta no se puede recuperar.

---

## 1. Ecosistema — repositorios

Todos los repos giran alrededor del mismo objetivo: **conocimiento para diseñar,
crear y evaluar arneses.**

| repo | ruta local | GitHub | papel en el objetivo |
|---|---|---|---|
| **Bibliotecario** | `/mnt/c/Bibliotecario` | `VicenteVila/Bibliotecario` | **Conocimiento**: corpus de papers, grafo, blueprints, benchmark y decisiones |
| **CogniTeam** | `/mnt/c/Cogniteam` | `VicenteVila/CogniTeam` | **Dominios**: 14 dominios, 61 arquetipos, reglas/skills/workflows por dominio |
| **ReaWeb** | `/mnt/c/EW` | *(repo `reaweb-harness`)* | **Arnés de dominio web** — primer intento |
| **ReaGame** | `/mnt/c/EG` | `VicenteVila/ReaGame` | **Arnés de dominio juegos** — segundo intento |
| **TraceForge** | `/mnt/c/TraceForge` | `VicenteVila/TraceForge` | **Observabilidad**: traza de cualquier agente de inicio a fin |
| **PromptForge** | `/mnt/c/PromptForge` | `VicenteVila/PromptForge` | Versionado y regresión de prompts |
| **AgentFlow** | `/mnt/c/AgentFlow` | `VicenteVila/AgentFlow` | Orquestación de pipelines |
| **EvoForge** | `/mnt/c/EvoForge` | *(verificar)* | Evolución — ver `TraceForge/Análisis EvoForge*.html` |

### Cadena del objetivo

```
papers ──► Bibliotecario ──► blueprint ──► arnés ──► evaluación
            (corpus+grafo)                 │            │
                 ▲                         │            │
                 │                         ▼            ▼
            CogniTeam ◄── dominio ──► ReaWeb / ReaGame ──► TraceForge
            (reglas/skills/               (los arneses)    (traza = métricas
             workflows)                                      de trayectoria)
```

---

## 2. Bibliotecario — conocimiento y decisiones

**Todo el razonamiento del proyecto vive en markdown, no en código.**

| qué | dónde |
|---|---|
| **Propósito / navegación** | `PROPOSITO.md` (raíz) |
| **Regla de medición** | `evals/BENCHMARK_SPEC.md` |
| **Mapa de conocimiento** | `CONOCIMIENTO.md` (este) |
| Umbrales y diseño de métricas | `evals/BLUEPRINT_METRIC_DESIGN.md` — §3.1 umbrales |
| Decisiones numeradas | `evals/BLUEPRINT_METRIC_DESIGN.md` — §6 dec. 9-18 |
| Cierre Hito 2 | `evals/HITO2.md` |
| Plan Hito 3 | `evals/HITO3_PLAN.md` |
| Erratas y fracasos declarados | `evals/BLUEPRINT_METRIC_DESIGN.md` — §8.8-§8.13 |
| Hitos previos | `evals/HITO0.md`, `HITO1.md`, `PLAN_READING.md`, `REPORT_BLIND.md`, `REPORT_COEVOLVE.md` |

### Corpus

| qué | dónde |
|---|---|
| PDFs (63 MB, **en `.gitignore`**) | `Documentos/` — 24 ficheros |
| SQLite (chunks, documentos, nodos) | `data/bibliotecario.db` |
| Semilla del grafo (**solo 5 técnicas**) | `bibliotecario/knowledge/seed.py:15-60` |
| Ingesta | `bibliotecario/ingest/pipeline.py` — `extract()` L19-36, `ingest_dir()` L92 |
| Construcción de blueprint | `bibliotecario/agent/tools.py` — `build_blueprint`, `instantiate_agent_template`, `verify_and_*` |
| Juez Q1 | `evals/eval_q1_r4r5.py` |
| Batería de ruido | `evals/measure_q1_noise.py` |
| Resultados del juez nuevo | `evals/result_q1_noise_gemini.json`, `evals/result_q1_r4_all.json` |
| `.env` (claves, chmod 600, no trackeado) | `.env` |

### Estado de la DB (2026-10-13)

`11 documentos` · `~842 chunks` · `31 nodos` · `45 aristas` · `275 lessons`
· **`0 skills`** · **`0 memory_items`** · `20 wiki_pages`

---

## 3. Los papers — de dónde sale el método

**Nunca codificar sin haber leído el paper que lo fundamenta.**

`Documentos/` — agrupados por el papel que cumplen:

| grupo | papel | papers |
|---|---|---|
| **A — Diseño** | *cómo se crea* un arnés | `HarnessDev…`, `Harness-of-Harness…`, `RRSI…`, `HARDE…`, `SoL-Pi…`, `Combinación de ramas…`, `Un estudio empírico del diseño de arneses…` |
| **B — Evaluación** | *cómo se mide* un arnés | **`Stop Comparing LLM Agents…`**, **`EVO-BENCH…`**, `Evaluación y análisis comparativo…` |
| **C — Mejora** | *cómo se optimiza* | `Sistema de optimización autoevolutivo…`, `Aprendizaje de meta-habilidades…` |
| **D — Métricas** | *qué se mide* | `Plasticidad del agente…`, `Más allá del modelo…`, `Anatomía, arquitectura y evolución…`, `De la respuesta a preguntas a la finalización de tareas…` |
| **Marco** | estructura del arnés | `Harness as a Language…` (+ traducción ES — **duplicado**) |
| **Técnicas** | contenido dentro del arnés | `PEARL…`, `Procedural Graphs…`, `Task-CoEvolve…`, `The Optimizer Is the Agent…`, `WikiSkill…` |

### Explotados

| paper | estado | resultado |
|---|---|---|
| **Stop Comparing** | ✅ leído | Harness Card ETCSOVG · `HV`/`MV`/`RR(k)`/Context Retention/`τ` · dos protocolos válidos |
| **Evo-Bench** | ✅ leído | `D^val`/`D^eval` · criterio **`Sens(x) > 0`** · presupuesto · loop de evolución · dos bases |
| resto | ❌ sin leer | — |

---

## 4. CogniTeam — la fuente de dominios

| qué | dónde |
|---|---|
| **14 dominios, 61 arquetipos** (fuente canónica) | `cogniteam_archetypes.yaml` — `domains:` L42 |
| Prosa por dominio (**reglas/skills/workflows**) | `cogniteam_rules/<dominio>/{global-rules,agent-skills,global-workflows}.md` |
| Reglas comprobables (estructura/verificación) | `cogniteam_archetypes.yaml` → `structure`, `verification` |
| Separación general/dominio | `cogniteam/world_model/{rules_loader,knowledge_loader}.py` |
| Plantilla general del planner | `cogniteam/agents/planner_agent.py:544` `PLANNER_INSTRUCTION_TEMPLATE` |
| Los 5 dominios «soportados» | `planner_agent.py:339` `DOMAIN_WORLD_MODEL_PROMPTS` |
| Compuertas deterministas | `cogniteam/world_model/yaml_loader.py` — `validate_structure` L606, `validate_artifacts` L682 |
| Skills sembrados (155) | `.cogniteam/skills/default/skills.json` |
| Único benchmark offline | `evals/classification.yaml` — 123 casos, **solo clasificación** |

### Dominios (14)

`1_web_development` · `2_software_development` · `3_education` · `3_3d_design` ·
`4_graphic_design` · `5_video_production` · `6_marketing_growth` ·
`7_software_architecture` · **`8_game_development`** · `9_data_science` ·
`10_content_writing` · `11_devops_infrastructure` · `12_cybersecurity` ·
`13_legal_compliance` (+ `generic.generic-task`)

**Solo 5 «soportados»**: web, software, education, graphic, game.
**Solo 2 con arnés real**: **web** y **game**.

> ⚠ **Agujero:** solo **24/61** arquetipos definen `structure` y **17/61**
> `verification`. Los demás **pasan la compuerta vacía** (`score 1.0`).

---

## 5. ReaWeb — arnés web

| qué | dónde |
|---|---|
| Repo | `EW/reaweb-harness/` |
| Loop del agente | `.agent/agent.py` (`Agent.run()`) |
| Presupuesto | `.agent/budget_tracker.py` + `config/budget.yaml` (24 turnos, $5, 120 min) |
| Evaluador (10 ejes, techo 40) | `tools/domain/evaluator.py` — `WEIGHTS` L649, `_apply_blocking_gates` |
| Meta-evolución | `tools/domain/meta_editor.py` + `scripts/gate_harness_edit.py` |
| Gobernanza de skills | `tools/domain/skill_auditor.py` (WRITE/RETRIEVAL/REUSE) |
| **Suite de tareas (14)** | `benchmark/tasks.yaml` |
| **Leaderboard** | `benchmark/leaderboard.{json,md}` — mean_best **87.7** |
| Runs (~200) | `runs/` — `run_config.json` con `harness_hash` |
| Estado A/B | `AGENTS.md` — **Pausado por cuota free-tier**; PG **nulo** (p=0.25, BF01≈3.7) |
| Arquitectura propuesta | `Propuesta Arquitectura de Agente Web.docx` |
| Críticas | `Mejoras propuestas por QWEN 3.8.txt` · `Opinion repositorio ReaWeb.txt` |
| Baseline sin arnés | `Prueba Gemini/` — **69/100, 9/13 checks** |
| Documentos de diseño | `reaweb-harness/Docs/{REASONING,EVOLUTION,PG_AB_VALIDATION,TASK_CO_EVOLUTION}.md` |

**Lección dura documentada** (`Docs/PG_AB_VALIDATION.md`): el A/B expuso **cuatro
defectos silenciosos** del arnés — caché que mataba diversidad, subtask FAIL
permanente, 503, flag experimental congelado al importar.

---

## 6. ReaGame — arnés de juegos

| qué | dónde |
|---|---|
| Repo | `EG/` |
| **Suite (8 tareas, 4 arquetipos)** | `benchmark/game_tasks.yaml` |
| Suite de misevolución (M/B/P, 9) | `benchmark/game_misevo_tasks.yaml` |
| Runner | `scripts/run_benchmark.py` — ⚠ `best = last`, no `max` |
| **Gate de aceptación train/dev** | `scripts/gate_harness_edit.py` — ⚠ **defaults = tareas web**, `harness_edits` = **0 filas** |
| Dominio / cometido | `domain/archetypes/{platformas,puzzle,arcade,rpg-lite}/archetype.yaml` |
| Reglas duras (con casos reales) | `domain/archetypes/*/rules.yaml` — `contrast_cases: worked/didnt` |
| Evaluador (12 ejes, **techo 40**) | `tools/domain/evaluator.py` + `config.py` `BLOCKING_CEILING = 40` |
| Presupuesto / umbrales únicos | `config.py` — `BUDGET_DEFAULTS`, `LESSON_AUTO` (delta ≥ 4.0), `novelty < 40` |
| Memoria | `memory/memory.db` — `runs` 14, `lessons` 20, **`harness_edits` 0** |
| Lecciones duras etiquetadas `[manual]` | `memory/lessons.md` |
| Snapshots del arnés | `.agent/harness_snapshot.py` — `HARNESS_DIRS` + `task_hash` |
| **Papers de benchmark de juegos (SIN LEER)** | `GameCraft-Bench….pdf`, `GameDevBench….pdf` |
| Sprites + pipelines de assets | `Sprites/` → `scripts/build_assets.py` |

**Momento validado del umbral:** run `1171b26` codificó «juego sin cablear» como
gate P0 → **el run siguiente quedó CAPADO a total=40** (80 → 40).
Ese umbral está declarado antes de medir. **No se toca.**

---

## 7. TraceForge — el instrumento de trayectoria

| qué | dónde |
|---|---|
| Repo | `/mnt/c/TraceForge` |
| Uso básico | `import traceforge` → `configure()` → `@trace(agent=, model=)` |
| Persistencia | SQLite (`traces.db`), consultas por agente/estado/duración |
| Informes | CLI con Rich, **HTML autocontenido (Gantt + tabla)**, Markdown, JSON |
| Dashboard | Plotly, paginación, export CSV |
| **Export OpenTelemetry** | ✅ |
| **PII masking** | ✅ (emails, teléfonos, tarjetas, IPs + NER opcional) |
| Coste automático | 200+ modelos (Gemini, GPT, Claude, Llama, DeepSeek…) |
| *Streaming* | TTFT, *throughput*, latencia por chunk |
| Async | `contextvars` |

**Por qué es requisito y no añadido:** las métricas que *Stop Comparing* exige —
**`RR(k)`**, **Context Retention**, **Control Lag `τ`** — son temporales y **no
se pueden medir sin traza**. Además TraceForge cubre la capa **`O` de ETCSOVG**,
que es **la más débil en ambos arneses** (crítica nº1 de Qwen a ReaWeb:
*«echo de menos OpenTelemetry / Langfuse… el BudgetTracker es reactivo, no analítico»*).

---

## 8. Hallazgos críticos — bloqueantes conocidos

| # | hallazgo | dónde está el detalle |
|---|---|---|
| 1 | **No existe `D^eval` en ningún proyecto** — todo visible, y Bibliotecario iteró prompts contra su QA | §10.1 de `BENCHMARK_SPEC.md` |
| 2 | **`Sens(x)` no se puede calcular** — no hay score por pregunta (`r4_ok` es booleano agregado) | `evals/result_q1_r4_all.json` |
| 3 | **37/61 arquetipos sin `structure`/`verification`** → compuerta vacía | `cogniteam_archetypes.yaml` / `yaml_loader.py:612` |
| 4 | **Meta-evolución nunca ha disparado**: `skills=0`, `memory_items=0`, `harness_edits=0` | DBs de Bibliotecario y ReaGame |
| 5 | **`task_hash` frágil a acentos** → rompe series comparables | `EG/.agent/harness_snapshot.py:98-103` |
| 6 | **ReaGame: 7/8 tareas nunca ejecutadas**, no hay leaderboard | `EG/benchmark/` |
| 7 | **Gate train/dev de ReaGame apunta a tareas web** | `EG/scripts/gate_harness_edit.py:133-136` |
| 8 | **Traducción duplicada** en corpus (`Harness as a Language` + versión ES) | `Documentos/` |
| 9 | **14 de 24 ficheros del corpus sin ingerir**; 2 sin extensión | `Documentos/` + `pipeline.py:97` |
| 10 | **Juez ciego** — `gemini-3.1-flash-lite` comparte familia con agente | §8.13 de `BLUEPRINT_METRIC_DESIGN.md` |

---

## 9. Índice rápido — *«¿dónde está X?»*

| busco… | voy a… |
|---|---|
| el propósito del proyecto | `PROPOSITO.md` |
| la regla con la que se mide | `evals/BENCHMARK_SPEC.md` |
| las decisiones numeradas | `evals/BLUEPRINT_METRIC_DESIGN.md` §6 |
| los umbrales | `evals/BLUEPRINT_METRIC_DESIGN.md` §3.1 |
| qué se erró y se declaró | `evals/BLUEPRINT_METRIC_DESIGN.md` §8.8-§8.13 |
| un paper del corpus | `Documentos/` |
| el texto ya extraído de un paper | `sqlite3 data/bibliotecario.db` → tabla `chunks` |
| los dominios y sus reglas | `Cogniteam/cogniteam_archetypes.yaml` + `Cogniteam/cogniteam_rules/` |
| el arnés web | `EW/reaweb-harness/` |
| el arnés de juegos | `EG/` |
| trazar un agente | `TraceForge/` |
| los resultados de runs | `EW/reaweb-harness/runs/`, `EG/runs/` |
| las críticas externas | `EW/Mejoras propuestas por QWEN 3.8.txt`, `EW/Opinion repositorio ReaWeb.txt` |
| los papers de benchmark de juegos (**sin leer**) | `EG/GameCraft-Bench….pdf`, `EG/GameDevBench….pdf` |

---

*Regla: si algo se aprende, se anota aquí **con su ruta**. Un conocimiento sin
ruta no se puede recuperar, y uno recuperable que no se documenta se pierde igual.*
