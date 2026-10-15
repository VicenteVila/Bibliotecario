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
| **Regla de medición** | `evals/BENCHMARK_SPEC.md` — **ratificación parcial 2026-10-14: bloque B-1** · **scorer B-1 v2 ratificado 2026-10-15: vigente para medición nueva, v1 congelado como histórico** · §11 |
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
| PDFs (63 MB, **en `.gitignore`**) | `Documentos/` — **24 ficheros, todos con extensión** |
| SQLite (chunks, documentos, nodos) | `data/bibliotecario.db` |
| Semilla del grafo (**solo 5 técnicas**) | `bibliotecario/knowledge/seed.py:15-60` |
| Ingesta | `bibliotecario/ingest/pipeline.py` — `extract()` L19-36, `ingest_dir()` L92 |
| Construcción de blueprint | `bibliotecario/agent/tools.py` — `build_blueprint`, `instantiate_agent_template`, `verify_and_*` |
| Juez Q1 | `evals/eval_q1_r4r5.py` |
| Batería de ruido | `evals/measure_q1_noise.py` |
| Resultados del juez nuevo | `evals/result_q1_noise_gemini.json`, `evals/result_q1_r4_all.json` |
| `.env` (claves, chmod 600, no trackeado) | `.env` |

### Estado de la DB (2026-10-14)

`25 documentos` · `2296 chunks` · `126 nodos` · `180 aristas` · `275 lessons`
· **`0 skills`** · **`0 memory_items`** · `35 wiki_pages`

| tipo de nodo | antes | ahora |
|---|---|---|
| technique | 5 | **14** |
| procedure | ~26 | **98** |
| paper | 5 | **14** |
| edges | 45 | **180** |

> **Ingesta completada 2026-10-14** — antes: `11 documentos · ~842 chunks`.
> **+14 documentos · +1454 chunks.** Los 2 ficheros sin extensión fueron
> renombrados a `.pdf`; el `.docx` ya estaba en la DB (doc 4).
> `ingest_dir()` deduplica por hash — re-ingerir es seguro.

### Corpus por dominio — regla *(2026-10-15)*

> **El corpus se parte igual que el benchmark**: meta-conocimiento de arneses
> en `data/bibliotecario.db` (25 docs, **intacta**), conocimiento de dominio en
> una DB aparte por dominio. Lo que de un paper cambie una decisión del
> benchmark **no se queda implícito en el corpus**: se declara y cita en el
> spec, con enmienda y fecha.
>
> Frontera por **consumidor**, no por tema: «¿cómo se construye/evalúa un
> arnés?» → corpus general · «¿qué debe cumplir un juego / cómo se testea?» →
> corpus de dominio. **La fuente canónica ya lo hace así**
> (`cogniteam_rules/<dominio>/`). Motivos: meter papers de dominio en la DB
> general alteraría `result_retrieval.json` y las calibraciones de A-bis
> (mediciones sobre ese corpus de 25), y contaminaría criterios de un dominio
> como si fueran principios generales.

| qué | dónde |
|---|---|
| PDFs de dominio | `Documentos/<dominio>/` — hoy solo `game_development/` (**4 PDF**) |
| DB de dominio | `data/corpora/game_development.db` — `4 docs · 236 chunks` · `metadata.domain` |
| Cambio de DB | env **`BIBLIOTECARIO_DB`** (`config.db_path()`) — sin ella, la general en su ruta de siempre |
| Ingesta de dominio | `BIBLIOTECARIO_DB=data/corpora/game_development.db python3 -m bibliotecario.cli ingest-dir Documentos/<dominio>` |
| Descartados (con motivo) | `Documentos/descartados/` |

> **Los arquetipos no son carpetas**: la frontera es el **dominio** (14 en
> CogniTeam; los 61 arquetipos viven dentro de cada uno). Un paper rara vez
> sirve a un solo arquetipo → se tagea en `metadata` si acaso, sin fragmentar
> en 61 DBs. Carpetas vacías = andamio prematuro: la carpeta de un dominio
> nace con su primer PDF.

> **Descarte declarado — SAGE (2026) · 2026-10-15**: el PDF recibido es
> *«SAGE: Scalable Agentic 3D Scene Generation for Embodied AI»* (NVIDIA),
> generación de escenas 3D para IA encarnada — **no** es el paper de
> testing/harness que se pidió, y ninguna de las 60 tareas exige 3D.
> **No ingerido**; archivo movido a `Documentos/descartados/` (no borrado).
> Si aparece el SAGE de testing, se ingerirá en `game_development/`.

### 3.4 Las 14 técnicas sembradas y sus papers

**5 originales** (docs 1-5): `PEARL` · `Procedural Graphs` · `Task-CoEvolve`
· `ReASearch` · `WikiSkill`

**9 añadidas 2026-10-14** — cada procedimiento extraído del texto y verificado
en el chunk; **ninguno inventado**:

| técnica | paper | doc | aporta |
|---|---|---|---|
| **MetaSkill** | Learning Meta-Skills… AI4AI | 13 | meta-skills de test-time · banco congelado · Add/Revise/Keep |
| **Mixture of Self-Improving Branches** | MoSIB | 14 | ramas paralelas · subconjuntos de desarrollo que evolucionan · router |
| **HARDE** | HARDE | 15 | módulos trigger/monitor/feedback · probing aislado → optimización guiada |
| **JAZ** | Harness as a Language | 16 | primitivo `invoke` · delegación tail-recursive · memoria por prompting |
| **Harness-of-Harness** | HoH | 18 | 3 roles (Planner/Developer/QA) · bucle multi-día |
| **HarnessDev** | HarnessDev | 19 | Creation + Evolution · development loop de 4 pasos |
| **Malena** | How Much of a Harness… | 22 | **una sola sesión larga** · sin orquestación externa |
| **Agent as Its Own Optimizer** | Self-Evolving Harness | 23 | el modelo edita su propio arnés · presupuesto de edición con annealing |
| **SoL-Pi** | SoL-Pi | 24 | map-reduce de trayectorias · review independiente · gates de coste |

### 3.5 Los 4 papers de MEDICIÓN, no de método *(resultado honesto)*

Cuatro de los 14 **no tienen grafo procedural** — miden, no proponen un bucle.
Se declaran como `technique: null` en vez de inventarles un método:

| paper | doc | qué aporta en vez de un bucle |
|---|---|---|
| **Harness Engineering** | 12 | anatomía a nivel de código de **11 arneses de producción** · 7 dimensiones · «describes and compares, does not benchmark or rank» |
| **Beyond the Model** | 20 | ablación de **5 componentes** (tool registry, context compression, explicit planning, subagents, lazy skills) con **NanoHarness** como instrumento |
| **Agent Plasticity** | 21 | la **métrica** `P = ΔS / C` + taxonomía de fallos del bucle (`F_absent` / `F_missed` / `F_used`) |
| **An Empirical Study of Harness Design** | 25 | ablación controlada de **176 configuraciones** sobre un bucle ReAct fijo |

> **Por qué esto es conocimiento y no un hueco:** `Agent Plasticity` da la
> métrica exacta que el proyecto necesita para la capa **`O` de ETCSOVG** —
> *cuánto aprende el arnés por unidad de coste*. **NanoHarness** (doc 20) es un
> instrumento de ablación reutilizable. **No son técnicas que sembrar; son
> mediciones que citar.**

> #### El conocimiento es usable, no solo almacenado *(2026-10-14)*
>
> Verificado sin tocar el grafo: `list_procedures()` devuelve las técnicas
> nuevas con sus procedimientos — `HarnessDev` 7 · `SoL-Pi` 10 · `MetaSkill` 10
> · `HARDE` 10 · `Agent as Its Own Optimizer` 7.
>
> `build_blueprint('HarnessDev', …)` generó un blueprint **con citas reales al
> paper** (`doc:0:0`, `doc:0:6`, `doc:0:14`, `doc:0:1`, `doc:0:7`) cubriendo las
> dos etapas del método, el contrato del *seed* y los **dos ejes de evaluación
> (capacidad + eficiencia en tokens)**.
>
> → **El ciclo corpus → grafo → blueprint funciona de punta a punta** con el
> conocimiento recién ingerido.



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
| **GameCraft-Bench** | ✅ leído | ver §3.1 — **rechaza el evaluador estático**; da el scorer `BUILD × (0.15M+0.35D+0.15V+0.35A)` |
| **GameDevBench** | ✅ leído | ver §3.2 — tests **ejecutados en Godot**; categoriza por skill+editor, **no por género** |
| resto | ❌ sin leer | — |

### 3.1 GameCraft-Bench — *«can agents build playable games end to end»*

`c:\EG\GameCraft-Bench, Can agents build playable games end to end in a real game engine.pdf`
· 25 págs · arXiv:2606.17861v1 · **extracción**: `/tmp/opencode/papers/gamecraft.txt`

| | |
|---|---|
| tareas | **140** / **15 familias** (Platformer 19, Strategy 17, Tycoon 16, Open-world 15, Roguelike 14, Visual novel 11, Puzzle 8, Shooter 7…) |
| motor | **Godot 4.6.2** · Ubuntu 22.04 · Python 3.12 · Harbor |
| éxito se decide por | **replay de trazas `Π` del agente** + **juez multimodal GPT-5.5** sobre **rúbrica oculta `ρ`** |
| fórmula | `Score = BUILD × (0.15·M + 0.35·D + 0.15·V + 0.35·A)` |
| BUILD | **0 si no lanza o ninguna traza parsea → nota final = 0** *(cero, no techo)* |
| categorías | M Core Mechanics 0.15 · **D Content Depth 0.35** · V Functional Visuals 0.15 · **A Art & Presentation 0.35** |
| rúbrica | ≤24 ítems, anclados `0 / 0.5 / 1`, **tope 0.5** a lo *label-only / decorativo / widgets por defecto / formas programáticas* |
| agregación | **`max`** para requisitos puntuales · **`mean`** para propiedades persistentes |
| replay | `xdotool` + `Xvfb` + `ffmpeg` · 30 fps · 1280×720 · ≤10 demos · ≤20 s · muestreo 2 fps |
| presupuesto | agente **7200 s** · verificador **1800 s** |
| validación de tarea | **oracle** Godot que prueba que la spec es implementable y cada ítem alcanzable |
| mejores | Opus-4.7 high **41.46 %** · GPT-5.5 high 39.49 · Kimi-K2.6 30.65 · DeepSeek-V4-Pro 2.15 |
| **no mide** | *diversión* subjetiva · 3D · multijugador · audio |

**Tres desiderata** (§2.2): I *Engine Grounding* · II *Artifact Completeness*
· **III *Interactive Verification*** — *«the artifact must be run, acted upon, and
observed as an interactive system»*.

**Cita clave** (§3.3): *«source code, project structure, assets, and screenshots
may be useful for debugging, but they **do not substitute for observed behavior
under player input**.»*

**Prohibido explícitamente**: **exploración autónoma por el verificador** —
*«making scores depend on the verifier's exploration policy»*.

> **Preflight 2026-10-14 — el replay NO es ejecutable en este ecosistema hoy.**
> Medido, no supuesto:
>
> | pieza | estado |
> |---|---|
> | `Xvfb` | ✅ instalado |
> | `ffmpeg` | ✅ instalado |
> | **`xdotool`** | ❌ **ausente** |
> | **ReaGame emite trazas `Π`** | ❌ **no** |
>
> → el scorer completo de GameCraft **queda en fase B-2, bloqueado**.
> Ver `evals/BENCHMARK_SPEC.md` §5.2.1 y la **enmienda 1**.

### 3.2 GameDevBench — *evaluación por tests ejecutados*

`c:\EG\GameDevBench,Evaluating agentic capabilities through game.pdf`
· 29 págs · **extracción**: `/tmp/opencode/papers/gamedevbench.txt`

| | |
|---|---|
| tareas | **333** = 154 core + 179 variantes · **131 fáciles / 202 duras** |
| motor | **Godot 4** |
| éxito se decide por | **tests unitarios GDScript ejecutados en el motor** — `VALIDATION_PASSED` / `VALIDATION_FAILED` |
| scorer | **binario pass@1**, sin crédito parcial, **sin ejes, sin pesos, sin techo** |
| categorías | **NO géneros** — 4 *skill* (2D 33.3 %, 3D 26.7 %, UI 20.1 %, Gameplay 19.8 %) + 3 *editor* |
| validación de tarea | tests ↔ instrucción **bidireccionales** + chequeo de ambigüedad |
| presupuesto | agente 7200 s *(no explícito)* |
| mejores | Gemini 3 Pro **53.8 %** · Gemini 3 Flash 45.4 · GPT-5.4 41.1 · Qwen3.5-397B 5.4 |
| hallazgo | feedback multimodal **+10.9 pp** (GPT-5.4 41.1 → 52.0) · coste **×3.3** |
| fracasos | nodos mal ubicados **63.4 %** · métodos/props ausentes 36.2 % · física incorrecta 32.1 % |

**Cita clave** (§3.2): *«methods are… **either proxies to correctness or
non-deterministic**. GameDevBench instead uses Godot's testing framework which
allows us to **directly test game behavior**.»*

**Cita sobre taxonomía** (§3.1): *«there is **no existing taxonomy** of game
development tasks performed within a game editor or game engine.»*

**Rechaza explícitamente**: LLM-as-a-Judge para scoring (*«subject to biases»*),
CLIP (*«proxies to correctness»*).

### 3.3 Los cuatro papers y el `D^eval`

| paper | ¿split `D^val`/`D^eval`? |
|---|---|
| **Evo-Bench** | ✅ **160 / 448** — único que lo construye |
| Stop Comparing | ❌ |
| **GameCraft-Bench** | ❌ — solo **rúbrica oculta `ρ`** |
| **GameDevBench** | ❌ — solo 117 transcripciones *para sonda de contaminación* |

**Los de juegos protegen *qué se juzga dentro de una tarea*, no *cómo se
protege el set*. Evo-Bench sigue siendo la única autoridad para la estructura
del split.**

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
| **Papers de benchmark de juegos** | ✅ **ya leídos** — §3.1 GameCraft · §3.2 GameDevBench · extracciones en `/tmp/opencode/papers/` |
| **Godot del arnés** | ✅ **`EG/.tools/godot` = 4.7.1.stable** — corre headless, exit=0 |
| Sprites + pipelines de assets | `Sprites/` → `scripts/build_assets.py` |

**Momento validado del umbral:** run `1171b26` codificó «juego sin cablear» como
gate P0 → **el run siguiente quedó CAPADO a total=40** (80 → 40).
Ese umbral está declarado antes de medir. **No se toca.**

> **Preflight de comportamiento 2026-10-14** — sobre **copia temporal**,
> **ReaGame no modificado**:
>
> ```
> C1  el proyecto arranca y hay nodo jugador          PASS
> C2  el jugador es CharacterBody2D                   PASS   ← tipo real, no texto
> C3  tiene move_and_slide                            PASS
> C4  ui_left/ui_right/ui_accept registradas          PASS
> C5  se MUEVE bajo input  →  dx=85.00 px en 40 f.   PASS   ← COMPORTAMIENTO
> === RESULTADO: 5/5 · VALIDATION_PASSED ===
> ```
>
> **C5 es la diferencia de constructo.** El evaluador estático actual haría
> `grep "move_and_slide"` y aprobaría un juego con la función escrita pero
> **nunca conectada**. Este test **ejecuta el juego y mide el desplazamiento**.
> → **la fase B-1 del scorer de Capa B es viable hoy y cuesta cero.**

### 6.1 Scorer B-1 construido (2026-10-14) — y su primer hallazgo real

| pieza | ruta |
|---|---|
| motor de checks | `evals/preflight/check_suite.gd` |
| orquestador | `evals/preflight/suite_runner.py` |
| 8 suites (una por tarea) | `evals/preflight/suites/*.yaml` |
| ejecutar | `python3 evals/preflight/suite_runner.py [id-tarea]` |

**Vocabulario de checks** *(todos comportamiento, ninguno `grep`)*:
`build` · `node_exists` · `node_is` · `has_method` · `collision` · `canvas` ·
`label_match` · `scene_count` · **`moves`** · **`jump`** · **`falls`** ·
**`lands`** · **`camera_follows`**

> #### Hallazgo — el evaluador estático aprueba un juego que no arranca
>
> `workspace/current` de ReaGame: `project.godot` declara
> `run/main_scene="res://main.tscn"`. Al **ejecutar** esa escena:
>
> ```
> f=2   is_on_floor=false  vel=(0.0, 60.0)
> f=10  is_on_floor=false  vel=(0.0, 120.0)
> f=20  y=518.3            vel=(0.0, 200.0)   ← el jugador CAE SIN PARAR
> ```
>
> **El jugador cae desde el frame 0 y nunca aterriza.** `Ground` está en la
> escena pero la colisión no funciona. **El punto de entrada del juego está roto.**
>
> Mientras tanto **`levels/mision1.tscn` funciona perfectamente**:
>
> ```
> f=2   is_on_floor=true  vel=(0.0, 0.0)
> f=10  press ui_accept
> f=11  vel=(0.0, -400.0)   ← salta con el valor JUMP correcto
> f=18  y=644.0             ← apex y aterriza
> ```
>
> **El juego SÍ está hecho. Lo que está roto es el punto de entrada declarado.**
> Un jugador que lance el programa recibe una escena rota.
>
> **El evaluador estático actual lo aprueba** — `player.gd` contiene
> `move_and_slide`, `JUMP`, `GRAVITY`, todo el código correcto.
> **El scorer B-1 lo detecta**: `platformer-juego` = **9/12**, con
> `jugador-salta` FALLANDO.
>
> → **Es la primera prueba empírica de que Capa A-bis y Capa B miden cosas
> distintas**, y de que la segunda ve lo que la primera no puede.

**Resultado de las 8 suites contra el workspace actual** *(prueba del corredor,
NO medición — un workspace contiene un juego, no ocho)*:

| tarea | M | Score |
|---|---|---|
| **platformer-juego** | **9/12** | **75.00** |
| platformer-niveles | 6/10 | 60.00 |
| arcade-shooter | 5/10 | 50.00 |
| rpg-quest | 5/11 | 45.45 |
| arcade-olas | 4/9 | 44.44 |
| rpg-boss | 4/12 | 33.33 |
| puzzle-memory | 2/6 | 33.33 |
| puzzle-sliding | 2/7 | 28.57 |

**Uso correcto:** generar el juego para la tarea X → correr **solo** esa suite X.

> #### B-1 validado: discrimina *(2026-10-14)*
>
> Mismo juego, dos escenas distintas, suite `platformer-juego`:
>
> | escena | M | Score | falla |
> |---|---|---|---|
> | `res://main.tscn` *(declarada como entrada)* | 8/11 | **72.73** | meta, monedas, salto |
> | `res://levels/mision1.tscn` *(nivel real)* | 11/11 | **100.00** | — |
>
> **Brecha de 27 puntos** entre una entrada rota y un nivel que funciona.
>
> **Errata propia corregida:** la primera versión teleportaba al jugador 300 px
> hacia arriba para medir gravedad y colisión. En `mision1` eso lo metía
> **dentro de la geometría del nivel** y hacía fallar los checks.
> **Sustituido por `settles`**: sin teleport, solo esperar a asentar.
> `is_on_floor()==true` implica que la gravedad lo bajó **y** que la colisión
> lo detuvo — ambas a la vez, **sin intervenir**. `falls` queda disponible
> pero documentado como sólo válido con espacio libre encima.

> #### §8.1 — La base humana de juegos está medida *(2026-10-14, ratificada)*
>
> | escena | M | Score |
> |---|---|---|
> | `levels/mision1.tscn` — nivel funcionando | 11/11 | **100.00** |
> | `main.tscn` — entrada declarada, rota | 8/11 | **72.73** |
>
> **La base humana es un intervalo, no un número.** `100` = el arnés humano
> cuando el juego se juega. `72.73` = cuando **el punto de entrada está mal** —
> mismo código, distinta escena de arranque.
>
> **Los 27 puntos son enteramente del punto de entrada.** Eso es la evidencia
> medida de que **A-bis y B son constructos distintos**: el evaluador estático
> aprueba ambas por igual; el de ejecución las separa en 27.
>
> **Regla:** toda generación futura se reporta **relativa a este intervalo**.
> Bajo `72.73` = por debajo de un humano con el punto de entrada roto.

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
| ~~1~~ | ~~**`D^eval` está bloqueada por TAREAS, no por diseño** — 8 tareas dejan ~2 de eval, sin potencia estadística. Umbral declarado: **≥56 tareas totales** para ≥20 de `D^eval` (ratio Evo-Bench 448/160)~~ | ✅ **RESUELTO 2026-10-14** — suite ampliada a **60 tareas** (8+52) en `evals/game_tasks_expanded.yaml`, umbral ≥56 cumplido; Puzzle=3 y Shooter=3 declarados en déficit; §4.4 de `BENCHMARK_SPEC.md` |
| ~~2~~ | ~~**`Sens(x)` no se puede calcular** — no hay score por pregunta (`r4_ok` es booleano agregado)~~ | ✅ **PARCIALMENTE RESUELTO 2026-10-14** — era cierto solo para el brazo **R4/Q1**. **Para juegos no aplica**: B-1 sí emite puntuación numérica **por tarea** (`res.score`, float, JSON). Lo que sigue faltando para `Sens(x)` son los **K arneses auxiliares** (coste), §10.2.1 de `BENCHMARK_SPEC.md` |
| 22 | **El split fiel a Evo-Bench está bloqueado por COSTE** — exige `Sens(x)`, que a su vez exige K arneses auxiliares evaluados sobre las 60 tareas; generarlos consume claves a `target_h: 3`. Un split aleatorio **no** es Evo-Bench y se declara placeholder | §10.2.1 de `BENCHMARK_SPEC.md` |
| ~~23~~ | ~~**B-1 no cubre 31 de las 60 tareas** — sus 5 `kind`s de comportamiento sólo aplican a avatares cinéticos; en Card/Idle/Rhythm/VN/Strategy/Tycoon/Simulation/Puzzle la verificación **colapsa a `label_match` + `node_exists`** (= evaluador estático). Además victoria/derrota/reinicio **jamás se activan** en ninguna de las 60: sólo se comprueba que exista un nodo *llamado* Win/Restart~~ | ✅ **CERRADO 2026-10-14 (enmienda 2)** — el dueño autorizó **A1**; los 5 `kind`s nuevos (`hud_value_changes`, `state_after_action`, `wait_accumulates`, `reaches_state`, `restart_resets`) están en **`check_suite_v2.gd`** (v1 intacto) y **validados**: separan un fixture cableado de uno roto por **83.33 pts** donde v1 los puntúa igual. v2 = benchmark nuevo **ratificado 2026-10-15** (dueño: «Ratifica v2») — vigente para medición nueva, v1 congelado como histórico · §5.2.2 y §11 enm. 2 |
| 3 | **37/61 arquetipos sin `structure`/`verification`** → compuerta vacía | `cogniteam_archetypes.yaml` / `yaml_loader.py:612` |
| 4 | **Meta-evolución nunca ha disparado**: `skills=0`, `memory_items=0`, `harness_edits=0` | DBs de Bibliotecario y ReaGame |
| 5 | **`task_hash` frágil a acentos** → rompe series comparables | `EG/.agent/harness_snapshot.py:98-103` |
| 6 | **ReaGame: 7/8 tareas nunca ejecutadas**, no hay leaderboard | `EG/benchmark/` |
| 7 | **Gate train/dev de ReaGame apunta a tareas web** | `EG/scripts/gate_harness_edit.py:133-136` |
| 8 | **Traducción duplicada** en corpus (`Harness as a Language` + versión ES) | `Documentos/` |
| ~~9~~ | ~~**14 de 24 ficheros del corpus sin ingerir**~~ | ✅ **RESUELTO 2026-10-14** — 25 docs · 2296 chunks |
| 10 | **Juez ciego** — `gemini-3.1-flash-lite` comparte familia con agente | §8.13 de `BLUEPRINT_METRIC_DESIGN.md` |
| 11 | **El evaluador de ReaGame mide código, no juego** — ambos papers de juegos lo rechazan | §5.2.0 de `BENCHMARK_SPEC.md` |
| 12 | **Inversión de prioridades**: GameCraft da 0.35 a Depth/Art y 0.15 a Mechanics; ReaGame al revés | §5.2.1 de `BENCHMARK_SPEC.md` |
| 13 | **El agente puede leer su propia rúbrica** — GameCraft exige rúbrica **oculta** | §5.2.1 de `BENCHMARK_SPEC.md` |
| 14 | **Ningún paper de juegos tiene `D^eval`** — solo Evo-Bench construye el split | §10.1 de `BENCHMARK_SPEC.md` |
| 15 | **Arquetipos por género**: respaldados por GameCraft, **rechazados por GameDevBench** | §10.2 de `BENCHMARK_SPEC.md` |
| 16 | **B-2 bloqueada**: falta `xdotool` y ReaGame **no emite trazas `Π`** — el replay de GameCraft no es ejecutable | §5.2.1 enmienda 1 de `BENCHMARK_SPEC.md` |
| ~~17~~ | ~~**B-1 está construido pero nunca ha medido un juego real** — el workspace actual es una escena rota; falta correr la suite tras una generación~~ | ✅ **PARCIALMENTE RESUELTO 2026-10-15 (smoke B-1 end-to-end)** — primera generación real (`card-memory-precision` · `openai/gpt-oss-120b`): el generador produjo escena+script con HUD ES correcto (`Tiempo:` · `Parejas: 0/8` · `Intentos:` · `Combo:`) y nodos `Victoria`/`GameOver`/`Restart`, pero **0/4 generaciones con sintaxis limpia** (backticks · `onready` Godot 3 · `HorizontalAlignment.CENTER` · `async func`/función anidada) — reparación manual de 3 líneas de sintaxis + 1 propiedad de API (`autowrap`→`autowrap_mode`). El smoke **destapó y corrigió un bug real del motor** (enmienda 3 de §11: los checks estáticos corrían antes de `_ready()`); tras el fix el mismo juego pasa **10/10** con las agujas ES validadas en runtime (fixtures de regresión intactas: 9/9 y 4/4). **Sigue faltando** la medición con protocolo completo (N tareas × N generaciones con presupuesto LLM declarado). `evals/preflight/suite_runner_v2.py` · resultados del smoke 2026-10-15 |
| 18 | **`main.tscn` de ReaGame está roto** — el jugador cae sin aterrizar; `levels/mision1.tscn` sí funciona | §6.1 de `CONOCIMIENTO.md` |
| ~~19~~ | ~~**`seed.py` sigue con 5 técnicas**~~ | ✅ **RESUELTO 2026-10-14** — 14 técnicas · 98 procedimientos · §3.4 |
| ~~20~~ | ~~**El modelo por defecto de Groq ya no existe** — `llama-3.3-70b-versatile` devuelve **HTTP 404 `model_not_found`**; la key además da **403** en `/models` y de forma intermitente en llamadas~~ | ✅ **RESUELTO 2026-10-15** — key rotada por el dueño (nunca se muestra ni se commitea). El 403 era **Cloudflare error 1010**: el UA por defecto de urllib está bloqueado; el UA propio del proyecto (`bibliotecario/1.0 (+https://github.com/VicenteVila/Bibliotecario)`) **es aceptado**, así que `llm.py` no cambia. Modelo por defecto → **`openai/gpt-oss-120b`** (`llama-3.3-70b-versatile` sigue de baja). **Límite declarado del tier libre: TPM 8000** — prompts grandes de reparación rebotan con HTTP 413; alternativas vivas del lineup: `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`. `bibliotecario/config.py:15-20` · `.env` (gitignored) |
| 21 | **Bug corregido: `chat_template_kwargs` se enviaba a Groq** — parámetro vLLM que Groq rechaza con HTTP 400 y **tumbaba el fallback del round-robin entero** | `bibliotecario/core/llm.py:147` — **arreglado 2026-10-14** |

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
| papers de **dominio** (juegos) | `Documentos/game_development/` · DB `data/corpora/game_development.db` |
| el PDF descartado y el motivo | `Documentos/descartados/` · `CONOCIMIENTO.md` §2 «Corpus por dominio» |
| **las 14 técnicas sembradas** | `CONOCIMIENTO.md` §3.4 · código en `bibliotecario/knowledge/seed.py` |
| **los 4 papers de medición (sin bucle)** | `CONOCIMIENTO.md` §3.5 — *Harness Engineering · Beyond the Model · Agent Plasticity · Empirical Study* |
| el texto ya extraído de un paper | `sqlite3 data/bibliotecario.db` → tabla `chunks` |
| los dominios y sus reglas | `Cogniteam/cogniteam_archetypes.yaml` + `Cogniteam/cogniteam_rules/` |
| el arnés web | `EW/reaweb-harness/` |
| el arnés de juegos | `EG/` |
| trazar un agente | `TraceForge/` |
| los resultados de runs | `EW/reaweb-harness/runs/`, `EG/runs/` |
| las críticas externas | `EW/Mejoras propuestas por QWEN 3.8.txt`, `EW/Opinion repositorio ReaWeb.txt` |
| los papers de benchmark de juegos (**YA LEÍDOS**) | `/tmp/opencode/papers/{gamecraft,gamedevbench}.txt` |
| los PDFs originales de juegos | `EG/GameCraft-Bench….pdf`, `EG/GameDevBench….pdf` |
| el reencuadre del evaluador de ReaGame | `evals/BENCHMARK_SPEC.md` §5.2.0 |
| el scorer de Capa B **B-1** (tests en Godot) | `evals/BENCHMARK_SPEC.md` §5.2.1 |
| el scorer de Capa B **B-2** (replay, bloqueado) | `evals/BENCHMARK_SPEC.md` §5.2.1 + enmienda 1 |
| el scorer B-1 (tests de comportamiento) | **`evals/preflight/suite_runner.py`** + `suites/*.yaml` + `check_suite.gd` |
| **las 52 suites v2 de las tareas reales** | `evals/preflight/suites_v2/<id>.yaml` — escritas 2026-10-15 desde el texto **antes de cualquier generación**, congeladas al escribirse; lint `evals/preflight/lint_suites_v2.py` (52/52, 551 checks); método y exclusiones → §5.2.2.c |
| **la base humana de juegos** (72.73–100.00) | `evals/BENCHMARK_SPEC.md` §8.1 · hallazgo en §6.1 |
| el preflight de comportamiento (5/5) | `evals/preflight/test_behaviour.gd` · hallazgo en §6.1 |
| el binario de Godot del arnés | `EG/.tools/godot` — **4.7.1.stable** |
| **la suite ampliada de juegos (60 tareas)** | `evals/game_tasks_expanded.yaml` · §4.4 de `BENCHMARK_SPEC.md` |
| **por qué B-1 no cubre 31 de esas 60** | `evals/BENCHMARK_SPEC.md` §5.2.2 — auditoría de cobertura por familia |
| **contraste de v2 con la literatura (5 papers de dominio)** | `evals/BENCHMARK_SPEC.md` §5.2.2.b — 17 clases: **8 cubiertas · 4 parciales · 5 sin cubrir** — los **3 huecos cerrados y validados 2026-10-15** (A cota de recurso · B error de runtime · C sincronía rítmica); **v2 ratificado 2026-10-15** (dueño: «Ratifica v2»), vigente para medición nueva; recuento previo 6/5/6 estaba mal (errata declarada) |
| **el scorer B-1 v2 (21 checks + BUILD, cierra esa brecha)** | `evals/preflight/check_suite_v2.gd` + `suite_runner_v2.py` · validado en `fixtures/v2_{ok,broken}/` · suites de las 52 tareas en `suites_v2/` · §11 enm. 2 + **enm. 3** (bugfix estáticos/`_ready`, 2026-10-15) · §5.2.2.c · **primer smoke end-to-end 2026-10-15: generación real `card-memory-precision` = 10/10 tras reparación manual de sintaxis** (hallazgo 17 parcialmente cerrado) |

---

*Regla: si algo se aprende, se anota aquí **con su ruta**. Un conocimiento sin
ruta no se puede recuperar, y uno recuperable que no se documenta se pierde igual.*
