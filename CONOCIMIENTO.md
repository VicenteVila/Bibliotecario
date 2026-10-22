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
| Plan Hito 4 | `evals/HITO4_PLAN.md` |
| Plan Hito 5 | `evals/HITO5_PLAN.md` |
| Plan Hito 6 | `evals/HITO6_PLAN.md` |
| Plan Hito 7 | `evals/HITO7_PLAN.md` |
| Plan Hito 8 | `evals/HITO8_PLAN.md` |
| Plan Hito 9 | `evals/HITO9_PLAN.md` |
| Plan Hito 10 | `evals/HITO10_PLAN.md` |
| Plan Hito 11 | `evals/HITO11_PLAN.md` |
| Plan Hito 12 | `evals/HITO12_PLAN.md` |
| Plan Hito 13 | `evals/HITO13_PLAN.md` |
| Plan Hito 14 | `evals/HITO14_PLAN.md` |
| Plan Hito 15 | `evals/HITO15_PLAN.md` |
| Plan Hito 16 | `evals/HITO16_PLAN.md` — **CERRADO 2026-10-22 · NO CUMPLE** (§5) |
| Plan Hito 17 | `evals/HITO17_PLAN.md` — **RATIFICADO 2026-10-22** (opción B — prefiltro no-LLM; gates U1-U7 ☑ antes de implementar; aún sin corrida) |
| Erratas y fracasos declarados | `evals/BLUEPRINT_METRIC_DESIGN.md` — §8.8-§8.13 |
| Hitos previos | `evals/HITO0.md`, `HITO1.md`, `PLAN_READING.md`, `REPORT_BLIND.md`, `REPORT_COEVOLVE.md` |

### Corpus

| qué | dónde |
|---|---|
| PDFs (**en `.gitignore`**) | `Documentos/` — **26 ficheros en la raíz** (77 MB) + `game_development/` (5) + `descartados/` (1) |
| SQLite (chunks, documentos, nodos) | `data/bibliotecario.db` |
| Capa de cada documento | `documents.corpus_capa` — `fundacional` / `evaluacion` / `extendido` (multivalor) |
| Congelación del corpus de evaluación | `evals/corpus_lock.py` (`label`/`build`/`check`) → `evals/CORPUS_LOCK.json` |
| Filtro de capas en el retrieval | env **`BIBLIOTECARIO_CAPAS`** (`memory/retriever.py: allowed_capas()`) |
| Semilla del grafo (**solo 5 técnicas**) | `bibliotecario/knowledge/seed.py:15-60` |
| Ingesta | `bibliotecario/ingest/pipeline.py` — `extract()` L19-36, `ingest_dir()` L92 |
| Construcción de blueprint | `bibliotecario/agent/tools.py` — `build_blueprint`, `instantiate_agent_template`, `verify_and_*` |
| Juez Q1 | `evals/eval_q1_r4r5.py` |
| Batería de ruido | `evals/measure_q1_noise.py` |
| Resultados del juez nuevo | `evals/results/result_q1_noise_gemini.json`, `evals/results/result_q1_r4_all.json` |
| `.env` (claves, chmod 600, no trackeado) | `.env` |

### Estado de la DB (2026-10-21, tras higiene 16/17)

`25 documentos` · `2255 chunks` · `126 nodos` · `180 aristas` · `275 lessons`
· **`0 skills`** · **`0 memory_items`** · `35 wiki_pages`

| capa | docs | chunks |
|---|---|---|
| `fundacional,evaluacion` | 5 (doc 1-5) | 413 |
| `evaluacion,extendido` | 5 (doc 6-10) | 429 |
| `extendido` | 15 (doc 11-15, 18-27; **16 y 17 borrados**) | 1413 |

| tipo de nodo | antes (2026-09) | ahora |
|---|---|---|
| technique | 5 | **14** |
| procedure | ~26 | **98** |
| paper | 5 | **14** |
| edges | 45 | **180** |

> **Ingesta completada 2026-10-14** — antes: `11 documentos · ~842 chunks`.
> **+14 documentos · +1454 chunks.** Los 2 ficheros sin extensión fueron
> renombrados a `.pdf`; el `.docx` ya estaba en la DB (doc 4).
>
> **Lote 1 (2026-10-21)**: +2 documentos (`Recurrent Harness for Agentic
> Continual Learning`, `Self-Evolving Agent Harness`) · **+117 chunks**,
> ambos en capa `extendido`, declarados en `CORPUS_LOCK.json` como lote 1.
>
> ~~⚠️ **«`ingest_dir()` deduplica por hash — re-ingerir es seguro» era
> demasiado optimista**~~: la dedup comparaba el **texto extraído**, y 4 ficheros
> (docs 13, 17, 18, 23) se extrajeron en un entorno ligeramente distinto, con
> **1-2 caracteres de diferencia** (un `\n` desplazado alrededor de un
> diacrítico combinante). Re-ingerir la raíz los volvió a insertar como
> documentos nuevos (26-31) y hubo que borrarlos. **Resuelto el 2026-10-21**:
> el upsert por `path`+hash absorbe esa deriva (ver «Ingesta idempotente»),
> los 4 duplicados ya no existen y una re-ingesta de la raíz da `0 insertados`.

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
| PDFs de dominio | `Documentos/<dominio>/` — hoy solo `game_development/` (**5 PDF**) |
| DB de dominio | `data/corpora/game_development.db` — `5 docs · 333 chunks` · `metadata.domain` |
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

### Capas de corpus y `CORPUS_LOCK` — *(2026-10-21)*

> **Origen**: revisión adoptada (`§ El marco correcto: separación de corpus y
> versionado`) — «define las tres capas y el `CORPUS_LOCK.json` **antes de
> ingerir el primer paper nuevo**». Hecho en ese orden: capas → lock → lote 1.

| capa | qué es | ¿crece? | versionado |
|---|---|---|---|
| `fundacional` | los 5 papers de los que arranca el grafo (`seed.py`, set original) | **no** (congelado) | hash |
| `evaluacion` | papers sobre los que están escritas las preguntas ciegas: **doc 1-10** | **no** (congelado) | hash + lote |
| `extendido` | el resto, y todo lo que entre después | sí | por lotes |

Una capa **no es una carpeta**: se guarda al ingerir en `documents.corpus_capa`
(multivalor, coma-separada — los cinco fundacionales son *también* diana de
preguntas, y los doc 6-10 entraron crecidos pero ahora están congelados).
Se etiqueta **en la ingesta** (`pipeline.store(capa=...)`, `--capa` en la CLI),
nunca a posteriori.

| pieza | dónde |
|---|---|
| Columna + migración idempotente | `core/storage.py:init_db()` → `ALTER TABLE documents ADD COLUMN corpus_capa` |
| Etiqueta por defecto y validación | `ingest/base.py` — `CAPAS`, `CAPA_DEFAULT='extendido'`, `normalize_capa()` |
| Etiquetado derivado (no a mano) | `evals/corpus_lock.py label` — `evaluacion` = unión de `doc_id` de **todos** los `golden*.jsonl`; `fundacional` = por **título** (no por id: si la BD se reconstruye, los ids se mueven) |
| Lock | `evals/corpus_lock.py build` → `evals/CORPUS_LOCK.json` (paper_hash, sha256 del fichero, chunks, capas, lote, sha de cada golden) |
| Comprobación | `evals/corpus_lock.py check` — `fatal` (rompe) vs `avisos` |
| Filtro de retrieval | env **`BIBLIOTECARIO_CAPAS`** (`memory/retriever.py: allowed_capas()`) — sin la variable, **sin filtro** (comportamiento de siempre) |
| Evidencia de grafo también filtrada | `agent/tools.py: retrieve_evidence()` — si no, el filtro solo valdría en `search()` |
| Eval | `evals/eval_end2end.py --capas evaluacion` (+ `--sin-lock` para tests/smoke); guarda `meta.corpus = {capas, lock_verificado}` |

**Estado**: `label` + `build` + `check` OK. Lote 0 = doc 1-25, **lote 1 = doc
26-27**. Con `BIBLIOTECARIO_CAPAS=evaluacion`, `recall@1=0.933 · recall@3=1.0 ·
MRR@10=0.956` — **idéntico a sin filtro** (la eval de QA va a doc 1-5) y el
top-10 no contiene ningún doc fuera de la capa; sin filtro, el ranking de las
15 preguntas del golden **no cambia ni una fila** tras el lote 1
(`evals/results/result_retrieval.json`, respaldo en `result_retrieval_prev_20260929.json`).

**Alcance declarado (lo que NO lleva filtro)**: la *fuente* de los blueprints
(`_fuente_numerica`/`fuente_completa`, por `procedure → doc_id`) lee
`fundacional`+`extendido` y no se filtra — es lo que pide el marco (los
blueprints leen corpus que crece). Si algún día se evalúa un blueprint filtrado,
esa fuente habrá que meterla en el filtro.

**Pendientes**: los 2 papers del lote 1 **no se siembran en el grafo**
(`knowledge/seed.py` solo crea nodos de `TECHNIQUES` conocidas; sembrar
papers de arneses = experimento nuevo con línea base propia, `HITO3_PLAN.md` §7) ·
~~`.env` con `NVIDIA_MODEL` ignorado en silencio~~ → **arreglado 2026-10-21**:
`_load_env()` se ejecuta antes de leer `NVIDIA_MODEL`/`GROQ_MODEL`/
`NVIDIA_FALLBACK_MODEL`/`BIBLIOTECARIO_DATA_DIR` (antes corría al final del
módulo y esas cuatro constantes se leían antes de que el `.env` existiera;
sigue mandando lo exportado, `setdefault`) · `tests/test_config_env.py` (3) ·
~~limpieza de 7/16/17~~ → hecha: ver «Higiene de duplicados» ·
~~citas mal mapeadas de `study-5`~~ → **corregidas 2026-10-21**: junto con la
huérfana `[doc:16:0]`, las citas de los tres métodos de la frase «…utilizan
pipelines especializados» (`[doc:1:0]` de EvoSkill y `[doc:15:0]` de
Trace2Skill) apuntaban a PEARL y a HARDE, donde esos nombres **no aparecen**;
las tres → `[doc:5:38]` (Related Work de WikiSkill, que sí los nombra a los
tres) · `tests/test_study.py::test_corpus_real_sin_citas_a_documentos_inexistentes`
(146 citas en la wiki, 0 huérfanas). **Sigue pendiente** una auditoría
semántica de las 146 citas fuera de esa frase: solo se verificaron
huérfanas (todas) y los nombres de métodos de `study-5`.

### Ingesta idempotente — upsert semántico — *(2026-10-21)*

**Problema**: `store()` deduplicaba solo por `sha256(texto extraído)` y
devolvía temprano. Dos consecuencias medidas: (a) una mejora del extractor
nunca llegaba a una fila ya guardada (por eso existía `backfill_bibliography`);
(b) si la extracción derivaba **un solo carácter** (combinante diacrítico junto
a un salto de línea), el mismo fichero entraba como documento nuevo —4
duplicados reales (docs 13, 17, 18, 23) y una fila huérfana más (doc 16,
mismo `path` que el 7).

**Solución** — `ingest/pipeline.py`: `_find_existing()` / `_find_by_path()` /
`_merge_meta()` / `_write_chunks()`.

| orden de búsqueda | cuándo aplica | por qué |
|---|---|---|
| `paper_hash` | siempre, primero | contenido idéntico = mismo documento; además es la columna UNIQUE, mirarla primero imposible chocar contra ella |
| `arxiv.id` (`json_extract` + `idx_documents_arxiv`), **y solo si además coincide `path`** | 24/25 docs tienen id | misma clave **y mismo fichero** = mismo documento: v1/v2 y PDF/DOCX/OCR dejan de duplicar |
| `path` + título normalizado (`_find_by_path`) | mismo fichero, texto distinto | deriva del extractor → reindexa **esa** fila; título distinto ⇒ es otro documento y se inserta |

> **La guarda de `arxiv.id` importa**: sin acuerdo de `path` se devuelve
> `None` (con warning) y el fichero entra como fila nueva. Una traducción
> conserva el título original, así que «mismo arXiv + mismo título» no
> distingue *misma obra, otro idioma* de *mismo paper* — pisar un doc de
> `evaluacion` con texto en otro idioma no se recupera, mientras que un
> duplicado se limpia a mano. Es lo que evitó que la re-ingesta oficial
> machacara el doc 7 (inglés) con la traducción.

| rama | condición | `IngestResult.action` | escribe |
|---|---|---|---|
| duplicado | hash + fila intactos | `duplicado` | **nada** |
| metadatos | hash igual; meta, título o path cambió | `metadatos actualizados` | `UPDATE documents`, sin re-embedder |
| texto nuevo | misma clave, hash distinto | `actualizado` | fila + chunks + wiki `raw-<id>` · **`corpus_capa` intacta** |
| alta | sin fila | `insertado` | fila con la capa de la corrida |

Reglas de seguridad: `_merge_meta` da prioridad a lo nuevo **solo si no está
vacío** (páginas/OCR no se borran); el hash se consulta **primero**, así que
escribir `paper_hash` en un `UPDATE` no puede chocar con `UNIQUE`; y **no** se
pone `UNIQUE(arxiv_id)` — había 3 filas con `2609.26891` (7/16/17) y la
restricción reventaría `init_db` (hoy queda 1 sola, pero la guarda se mantiene:
la unicidad la resuelve la aplicación) — `init_db` solo crea
`idx_documents_arxiv` (índice de expresión) + `idx_documents_path`.
`ingest_dir` devuelve `acciones`, para que «25 ficheros, 0 inserts» sea un dato
del JSON y no una suposición.

**Evidencia**:
- *copia de BD, dos corridas* → corrida 1 `{'duplicado': 17, 'actualizado': 4,
  'metadatos actualizados': 5}` con **27 docs · 2413 chunks · 37 wiki
  intactos**; corrida 2 `{'duplicado': 26}`: punto fijo.
- *BD real, tras la higiene* → `ingest_dir(Documentos)`: **25 ficheros, 25 ok,
  `{'duplicado': 17, 'actualizado': 3, 'metadatos actualizados': 5}`,
  `insertado: 0`** en 38 s, con **25 docs · 2255 chunks · 35 wiki · 0 chunks sin
  embedding** (reindizados 13/18/23 = mismos que en la copia, menos el 17 ya
  borrado; metadatos de 1-5). `corpus_lock build` → `check` **OK** ·
  `eval_retrieval` **idéntico a antes de la higiene** (`recall@1=0.933`,
  `@3/@5=1.0`, `MRR@10=0.967`) · **418/418 tests** · ruff limpio.
Tests: `tests/test_upsert.py` (8).

### Higiene de duplicados — filas 7/16/17 — *(2026-10-21)*

`2609.26891` («Harness as a Language») vivía en **3 filas**: doc 7 (inglés,
`evaluacion,extendido`), doc 16 (inglés re-extraído, `extendido`) y doc 17
(traducción ES, `extendido`) — 158 chunks contaban el mismo paper tres veces y
la traducción pesaba doble en la recuperación. Hecho ese día, en este orden:

1. **Respaldo** `data/bibliotecario.db` → `/tmp/opencode/bibliotecario_before_higiene_20261021.db` (API `sqlite3.backup`, WAL incluido).
2. **La traducción sale del inbox**: `Documentos/Harness como lenguaje….pdf` →
   `Documentos/traducciones/` (carpeta nueva, al lado de `descartados/`; no se
   borra nada y `ingest_dir` no entra en subcarpetas, así la re-ingesta no la
   re-crea).
3. **Borrado de 16 y 17** con `storage.get_conn()` + sus páginas
   `raw-16`/`raw-17`. *Lección medida*: con un `sqlite3.connect` crudo la
   cascada **no se dispara** (`PRAGMA foreign_keys` por defecto OFF aunque el
   DDL diga `ON DELETE CASCADE`) → quedaron 158 chunks huérfanos que hubo que
   borrar aparte; `storage._connect` sí pone `foreign_keys=ON`, así que usar
   **ese** conector.
4. **Cita huérfana reescrita**: `study-5` citaba `[doc:16:0]` para «SkillOpt…»
   y ese texto **no está** en doc 16 (cita posicional mal mapeada); el chunk
   que sí sostiene la frase es `[doc:5:38]` (Related Work: «Trace2Skill … and
   SkillOpt … use specialized agent pipelines»). Ver pendiente de `[doc:15:0]`
   arriba.
5. **Re-ingesta + lock + eval** con los números de «Evidencia» de arriba.

Estado resultante: **1 fila por paper**, `documents` sin duplicados de
contenido ni de traducción; `knowledge/seed.py` resuelve JAZ por **título**
(→ doc 7, no hace falta tocar nada); los `evals/results/result_*.json` históricos que
mencionan al doc 16 quedan como registro de corridas pasadas.

### Tokenizador compartido (canal keyword) — *(2026-10-21)*

**Problema**: cuatro dialectos distintos de «palabra», todos con guillotina de
longitud `{4,}` (o `len(t) > 3`), y solo uno de ellos veía cifras:

| dónde | antes | efecto |
|---|---|---|
| `memory/retriever._tokens` (kw 0.3) | `[a-záéíóúñü]{4,}`, sin stoplist, **sin dígitos** | se comía `why`, `how`, `RAG`, `OCR`, `τ=5` |
| `agent/tools._doc_keyword_chunks` | `[a-z0-9\-]{4,}` + stoplist propia, y conteo por **subcadena** | `"use"` contaba dentro de `"users"` |
| `agent/tools._toks` (similitud de fuente) | igual que el retriever | divergía de `deep_sweep` |
| `knowledge/pearl.seed_nodes` | `split()` crudo + `len(t) > 3` | `failure?` se buscaba literal con `?`; `RAG` no entraba |

**Ahora**: un único módulo `core/tokens.py` — cifra (`10`) **o** compuesto
con guion (`task-coevolve`, `path-entity`) **o** ≥3 letras; stoplist compartida
EN+ES (`STOP`, aplicada en los cuatro sitios; `drop_stop=False` para quien
necesite las palabras vacías); orden preservado (`token_list`) porque las
semillas del grafo lo usan; y `count_terms()` cuenta **tokens exactos**, no
subcadenas.

**Medido** (15 preguntas del golden, ranking híbrido completo,
`evals/eval_retrieval.py`): `recall@1=0.933` (igual), `recall@3/5=1.0` (igual),
**`MRR@10 0.956 → 0.967`** (`wiki-1` pasa de rank 3 a 2). Variantes descartadas
por igualdad o peor resultado: `{3,}` literal de la propuesta, `{4,}`+cifras.
*Verificado tras la higiene 16/17: mismas cifras exactas.*
El **compuesto con guion es imprescindible**: trocearlo en `task` + `coevolve`
hacía que términos presentes en casi todos los chunks diluyeran el léxico y el
chunk con `earliest candidate` bajara del puesto 8 al 12, rompiendo
`test_cierre_incluye_el_dato_literal`. Tests: `tests/test_tokens.py` (7).

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
| **JAZ** | Harness as a Language | 7 | primitivo `invoke` · delegación tail-recursive · memoria por prompting |
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
| **Marco** | estructura del arnés | `Harness as a Language…` (doc 7; la traducción ES vive en `Documentos/traducciones/`, fuera del inbox) |
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
| 4 | **Meta-evolución nunca ha disparado**: `skills=0`, `memory_items=0`, `harness_edits=0`. **CERRADO 2026-10-16 (Hito 4, CUMPLE 5/5)**: el ciclo está cableado en la ruta productiva — firma de fallo por run (`last_error` en el estado), evolución a la 2ª aparición (K=2) en `RuntimeHarness.meta_evolve`, `auto_pf_*` + `auto_skill_*` persistidos (tablas nuevas/propias: `harness_edits`, `skills`, `memory_items`) y rehidratación al reiniciar registro+harness. Medido con runs guionizadas 0 tokens y umbrales ratificados antes de correr: H5 dispara (1/1), H6 se usa en proceso (`auto_pf_1` en R3), H7 contadores llenos (1/1), H8 durabilidad (rehidrata y vuelve a disparar), C1 control (run limpia 0 auto_pf, suite 281 verde). Quedan abiertos `MT.recall` sin cablear en lectura, meta-evolución fuera de `run_blueprint` y la herencia de `auto_pf_*` en evals que no usen DB hermética | `evals/HITO4_PLAN.md` §6 · `evals/results/result_hito4_meta.json` · `harness/edits.py` · `loop.py` (Hito 4) |
| 5 | **`task_hash` frágil a acentos** → rompe series comparables | `EG/.agent/harness_snapshot.py:98-103` |
| 6 | **ReaGame: 7/8 tareas nunca ejecutadas**, no hay leaderboard | `EG/benchmark/` |
| 7 | **Gate train/dev de ReaGame apunta a tareas web** | `EG/scripts/gate_harness_edit.py:133-136` |
| 8 | **Traducción duplicada** en corpus (`Harness as a Language` + versión ES) | `Documentos/` |
| ~~9~~ | ~~**14 de 24 ficheros del corpus sin ingerir**~~ | ✅ **RESUELTO 2026-10-14** — 25 docs · 2296 chunks |
| 10 | **Juez ciego** — `gemini-3.1-flash-lite` comparte familia con agente · **ventana RESUELTA 2026-10-17 (E13: `FUENTE_MAX=160000` en `q1`, fuente completa sin truncar) — residual vivo: el juez erra por nombre-exacto incluso con toda la fuente visible (quejas falsas de PG: `refiner`/`mutation` presentes)** · **cuantificado en H11 (2026-10-17): la ventana de fuente con la que el juez «verifica» es ≤10% del paper en las 5 técnicas (PEARL 6,1% · PG 0,9% · ReASearch 0,9% — 1.195 de 138.667 chars — · TCE 10,4% · Wiki 7,9%); `_source_for` hace `LIKE` con etiquetas en español contra texto en inglés y casi no matchea → «el texto fuente no menciona…» declarado contra ≥90% de fuente invisible; explica la cola bottomless de moles de ReASearch** · **E12 en H12 (2026-10-17): enmienda 1 de ventana rica (chunk0+citados+top-10 híbrido, `fuente_verificable`) → RECHAZADA 0/4 en recalibración — todas las quejas nuevas de los 4 aprobados son FALSAS contra la fuente completa (PEARL «converges faster» 2×, TCE 0.125/0.025 exactos + Table D/E, Wiki gating 16×/rbest 10×/qwen 98×, PG mutation 11×); veredictos R4/R5 = función de la ventana: ninguna ventana corta probada es estable (tiny → inverificable en ReASearch; recuperada → falsos positivos en los 4)** · **E13 en H13 (2026-10-17): fuente completa (`FUENTE_MAX=160000`, sin truncar, PROMPT intacto) → 3/4 restaurados — PEARL/TCE/Wiki aprueban, confirmando que sus quejas E12 eran falsas — pero PG cae con quejas MIXTAS (2 falsas por nombre-exacto: `refiner` 23× y `mutation` 11× presentes en su fuente; 1 verdadera: `lesson`/`persist` 0× en 131.899 chars) y ReASearch cae con solo 2 quejas ambas verdaderas (`refiner` 0×, `pre-release` 0×) → la ventana NO era el único problema: el criterio R4 confunde «no con ese nombre» con «no existe», y con la fuente completa la cola de moles se encoge a 1-2 reparaciones verdaderas** · **H21 en H14 (2026-10-17): con fuente completa la reparación NO converge — PG muere por V1 (227 < 1121) tras cadena de quejas mezcla falsas/estructurales y vacíos de sección; ReASearch tiene 2 quejas × 10 rondas de familia ESTRUCTURAL («Módulo 1/2/3», «Orden de Ejecución» — el paper no define esa arquitectura) y 6 de 10 ediciones no-op → la fabricación de ambos es pervasiva del documento, no una lista finita de moles: lo que la ventana ciega aprobaba, la fuente completa lo rechaza** | §8.13 de `BLUEPRINT_METRIC_DESIGN.md` · `evals/HITO11_PLAN.md` §5 · `evals/HITO12_PLAN.md` §5 |
| 11 | **El evaluador de ReaGame mide código, no juego** — ambos papers de juegos lo rechazan | §5.2.0 de `BENCHMARK_SPEC.md` |
| 12 | **Inversión de prioridades**: GameCraft da 0.35 a Depth/Art y 0.15 a Mechanics; ReaGame al revés | §5.2.1 de `BENCHMARK_SPEC.md` |
| 13 | **El agente puede leer su propia rúbrica** — GameCraft exige rúbrica **oculta** | §5.2.1 de `BENCHMARK_SPEC.md` · **mitigación en producción desde Hito 16 (2026-10-22)**: ρ de `platformer-juego` vive en `evals/preflight/rubricas/` (fuera del workspace, nunca se copia) con gate **U5** = 0 coincidencias de `B2-` en workspace y copia temporal → **0/0 medidos en la corrida oficial**; el sesgo de autoría de la ρ (riesgo c pre-declarado) lo gatean U2+U4 y ambos **fallan** en la corrida (sin maquillaje) → ver `evals/HITO16_PLAN.md` §5 |
| 14 | **Ningún paper de juegos tiene `D^eval`** — solo Evo-Bench construye el split | §10.1 de `BENCHMARK_SPEC.md` |
| 15 | **Arquetipos por género**: respaldados por GameCraft, **rechazados por GameDevBench** | §10.2 de `BENCHMARK_SPEC.md` |
| 16 | **B-2 desbloqueada en etapa 1 (Hito 15, CUMPLE 2026-10-17)**: ReaGame **no emite trazas `Π`** → se resolvió con grabador inyectado (`evals/preflight/pi_capture.gd` + `pi_actor.gd` vía autoloads en copia temporal) que persiste `t_ms` por tick (determinista, T2 byte-idéntico); `xdotool` instalado sin root extrayendo los .deb a `~/opt/xdotool/`. **Entorno WSL mide dos bloqueos nuevos**: (a) `/tmp/.X11-unix` es tmpfs **ro** → Xvfb solo arranca con `-listen tcp -ac` y display `localhost:99` (puerto 6099; unix primero, TCP después); (b) sobre `:0` (WSLg) x11grab devuelve **frames negros** (XWayland no espeja + ventana en 364,266) → forzar `--position 0,0` y usar Xvfb = ruta primaria. Corrida T1-T5 **TODA SÍ** (8 eventos/3833 ms/schema []; replay 14 frames 0 negros lum 78.31; hash ReaGame intacto; suite 350). Evidencia: `evals/preflight/results/b2_etapa1/` + `evals/HITO15_PLAN.md` §5. **Queda para etapa 2 (Hito 16): scorer B-2, rúbrica `ρ`, juez multimodal** · **Etapa 2 CERRADA 2026-10-22 (Hito 16) · NO CUMPLE**: scorer con ρ oculta + juez `gemini-3.1-flash-lite` construido (`eea92ab` declaración → `196d54b` implementación → `20cad5d` ratificación §2-§3 **antes de medir**), corrida oficial única → **U1 ✅ (JSON estricto 15/15, 1 intento) · U3 ✅ (Δ=0.0, temp 0) · U5 ✅ (0 hits ρ) · U6 ✅ (BUILD 1.0, M_B1 0.8333, llamadas 5/10, suite 425, ruff, clave-scan) · U2 ❌ (juez caucho: 14 frames negros lum 0.000 puntuados con 10 presencias ≠0, Score_B2_negro 0.7762 > 0.30) · U4 ❌ (default−idle = 0.0 < 0.10: Score idéntico 0.3096 pese a default evolucionar 5,38% de píxeles vs 1,61% de idle)**. 4 intentos previos sin medición (0 suite ancla inexistente → 1 Π vacía de `idle` → 2-3 503 del proveedor con bugs de reintento ya corregidos), coste efectivo 0; tokens 82.855 y 5 llamadas en la corrida con datos. Evidencia: `evals/results/result_fase2_b2.json` + `evals/HITO16_PLAN.md` §5 (incl. verificación del instrumento: negros = 0.000 lum, recálculo `agregar` = almacenado, EG intacto) | §5.2.1 enmienda 1 de `BENCHMARK_SPEC.md` |
| ~~17~~ | ~~**B-1 está construido pero nunca ha medido un juego real** — el workspace actual es una escena rota; falta correr la suite tras una generación~~ | ✅ **RESUELTO 2026-10-15** — smoke end-to-end: juego real (`card-memory-precision`, reparado a mano) = **10/10** con las agujas ES validadas en runtime (y bug del motor corregido en el proceso, enm. 3). Después, **primera medición pequeña declarada** (§5.2.2.d, tres series, 28 generaciones, 121k+ tokens): **baseline fijada = 0.00** — 0/28 con `BUILD>0` (ver hallazgo 24). B-1 ya mide generaciones reales; lo que falta ahora es un generador que produzca juegos cargables | `evals/BENCHMARK_SPEC.md` §5.2.2.d + enm. 3 de §11 · JSONL en `evals/preflight/results/` |
| ~~24~~ | ~~**Baseline B-1 v2 = 0.00: el generador de tier libre no produce `.tscn` cargables** — 0 de 28 generaciones arrancaban escena~~ | ✅ **RESUELTO 2026-10-15 (serie 3, scaffold)** — con el harness fijando `project.godot`+`main.tscn` y el modelo escribiendo sólo `main.gd` (árbol por código en `_ready`): **10/10 generaciones con `BUILD>0`**, **global 31.40** (idle 75 · card 56.67 · platformer 52.94 · peor 9.09), y bucle de reparación con evidencia del motor probado: **10 → 80** en una ronda. La causa del 0/28 era el `.tscn`, no la lógica del juego. §5.2.2.d · `evals/preflight/results/measure_b1_serie3.jsonl` |
| 25 | **El tier libre de Groq aborta los bucles de reparación (429)** — `agotada/sobrecargada` mató las reparaciones en 7/8 tareas de la serie 3 (sólo 10 llamadas de las 24 del presupuesto); decisión pendiente de tier/contraparte de generación. ~~Y `node_exists` no ve los textos de UI~~ → ✅ **parte instrumento RESUELTA 2026-10-15 (enmienda 4 de §11)**: `node_exists` acepta ahora texto de `Label`/`Button` cuando ningún nombre coincide (validado: fixtures 9/9 · 1/9 · 4/4 intactas; micro-juego de sólo texto PASS; serie 3 no re-escalada por pérdida de workspaces en `/tmp`) | §5.2.2.d · enm. 4 de §11 · `evals/preflight/check_suite_v2.gd` |
| 18 | **`main.tscn` de ReaGame está roto** — el jugador cae sin aterrizar; `levels/mision1.tscn` sí funciona | §6.1 de `CONOCIMIENTO.md` |
| ~~19~~ | ~~**`seed.py` sigue con 5 técnicas**~~ | ✅ **RESUELTO 2026-10-14** — 14 técnicas · 98 procedimientos · §3.4 |
| ~~20~~ | ~~**El modelo por defecto de Groq ya no existe** — `llama-3.3-70b-versatile` devuelve **HTTP 404 `model_not_found`**; la key además da **403** en `/models` y de forma intermitente en llamadas~~ | ✅ **RESUELTO 2026-10-15** — key rotada por el dueño (nunca se muestra ni se commitea). El 403 era **Cloudflare error 1010**: el UA por defecto de urllib está bloqueado; el UA propio del proyecto (`bibliotecario/1.0 (+https://github.com/VicenteVila/Bibliotecario)`) **es aceptado**, así que `llm.py` no cambia. Modelo por defecto → **`openai/gpt-oss-120b`** (`llama-3.3-70b-versatile` sigue de baja). **Límite declarado del tier libre: TPM 8000** — prompts grandes de reparación rebotan con HTTP 413; alternativas vivas del lineup: `qwen/qwen3.8-27b`, `openai/gpt-oss-20b`. `bibliotecario/config.py:15-20` · `.env` (gitignored) |
| 21 | **Bug corregido: `chat_template_kwargs` se enviaba a Groq** — parámetro vLLM que Groq rechaza con HTTP 400 y **tumbaba el fallback del round-robin entero** | `bibliotecario/core/llm.py:147` — **arreglado 2026-10-14** |
| 26 | **HILO CERRADO 2026-10-17 por el dueño: H1 NO CUMPLE definitivo** — 9 intentos (Hito 5→14) + 2 enmiendas (E12 rechazada 0/4, E13 3/4) medidas con umbrales ratificados antes de cada corrida; balance final bajo instrumento honesto (fuente completa): **3/5 aprobados** (PEARL/TCE/Wiki) y **2 por arquitectura inventada pervasiva** (PG muere por V1 tras quejas estructurales; ReASearch 10 rondas con cola estructural sin converger) — la cláusula H5' 5/5 no es alcanzable editando con este corpus y esta mecánica; lo que la ventana ciega aprobaba, la fuente completa lo rechaza (hallazgo 10). Se conserva toda la evidencia; la vía «regeneración con juez honesto en el bucle de generación» queda declarada como posible enmienda futura pero NO iniciada. **H1 del Hito 3 NO CUMPLE: la ruta del arnés (p4) suspende R4/R5** — primer intento **1/5 · 1/5**; reparación R1 declarada (1 vuelta con las frases del juez) → **R4 3/5 · R5 1/5**; umbral 100% intacto, cerrado sin segunda tirada. El juez sirve de crítico accionable para R4 (2 de 4 arneses quedaron con 0 fabricaciones) y **no para R5** (0 de 4 se movieron). `verify_and_mark` no ve fabricaciones sin puntero (ReASearch `verificado=True` y suspendido por el juez); 3 de 5 arneses salieron con **0 punteros resueltos** y el juez no los suspendió por eso (TCE aprobó con 0/10): resolución y atribución son fallos distintos. → **Intento 2 (Hito 5, CERRADO 2026-10-17): la cláusula se alcanza y el cierre no** — juez en el bucle con evidencia completa (frases del juez + violaciones mecánicas + huérfanas nuevas + fuente, ≤3 rondas, umbrales ratificados) → **R4 5/5 · R5 5/5**, pero **G1 4/5** (ReASearch perdió sus 2 citas resolubles) y **G2 2/5** (PEARL pierde `## Bibliografía`; WikiSkill renombra todos los `##`) → **NO CUMPLE** con H5 y C1 (291) cumplidos. Degeneración medida: PG final 488 chars y ReASearch 440 (borrador de razonamiento del modelo) — **el juez los aprobó R4/R5** y rechazó el stub de WikiSkill; el C1 declarado (no vacío/`(`) no los caza. Final del intento: **0/5 con punteros resueltos** (el modo B empeoró). Abierto para un intento 3: reparación que no degenere (marcado in-place o draft validado con rechazo), validación de la salida del `generate()`, integridad del juez (hallazgo 10) → **Intento 3 (Hito 6, CERRADO 2026-10-17): las guardas 5/5 y la cláusula a 3/5** — mecanismo declarado: reparación mecánica determinista primero (`attribution.mech_repair`: normalizar punteros, demotear, marcar huérfanas — 0 tokens, sin reescribir) y **validación de cada salida** V1 ≥50% de longitud / V2 encabezados base / V3 resueltas, con 1 reintento y 2.º rechazo = arnés fallo → **G1 5/5 · G2 5/5 (primeras veces en cerrar)** · H5' **3/5** (PEARL r2 · TCE r0 · **PG se recupera**: su stub de 485 chars —el caso exacto del intento 2— rechazado por V1, reintento 2243 aprueba R4/R5 y disco restaurado 488→2360) · C1' cae por los 2 fail-fast → **NO CUMPLE**. ReASearch y WikiSkill no convergen en 2 intentos (pierden `## Bibliografía`, truncan <50%); WikiSkill r1 pasa la validación y lo suspende el juez (V1-V3 no ven lo semántico → pega al hallazgo 10); V2 en igualdad literal castiga los espacios finales de la propia base (`«Bibliografía  »`). 18 llamadas de las ≤50 declaradas; **el disco de ReASearch sigue en el stub de H12 (517 chars) porque ninguna reparación suya llegó a aceptarse**. Abierto: presupuesto de intentos/reparación por secciones, V2 con espacios declarado, restauración de ReASearch → **Intento 4 (Hito 7, CERRADO 2026-10-17): la base buena se sostiene y el marcado puro no basta** — localizador guiado LLM (solo `N -> M | eco` con eco ≥20 verificado; matching literal medido inviable, LCS 8–27) + `marcar_lineas` con **cero reescritura** (imposible por construcción), base = mejor estado aprobado conocido, M4 saneó ReASearch 517→5432 → **G1 5/5 · G2 5/5 · C1' SÍ** (sin fail-fast) y **H5' otra vez 3/5** (PEARL/PG/TCE r0 estables, temp 0) → **NO CUMPLE**. Los 2 frasan: ReASearch con **ambas quejas ancladas en encabezados** (l9/l18 — inmarcables sin romper V2) y WikiSkill **marcando la línea exacta de la queja** (l37, única ocurrencia de «estratificado») cuya queja R5 se repite idéntica 3 rondas más → **las marcas R6 no giran el veredicto del juez** (o la queja pide borrado = reescritura). Localizador: 5/10 salidas sin parsear, frases ausentes sin acreditar, rondas no-op tras la primera marca. 21 de ≤32 llamadas; diagnóstico completo en `evals/HITO7_PLAN.md` §5 → **Intento 5 (Hito 8, CERRADO 2026-10-17): la máscara sí mata la cita, pero el juez es whack-a-mole** — M5 edición con plantilla fija (MASCARA + punteros conservados, encabezados intactos, 0 generación), localizador con pre-normalización y frases ausentes acreditadas → **G1 5/5 · G2 5/5 · C1' SÍ** y **H5' 3/5** → **NO CUMPLE**. Primera vez que la edición gira un veredicto: Wiki l37 enmascarada hace desaparecer «estratificado» del texto y el juez r1 **cambia de queja**; ReASearch r0 enmascara [10,19] y r1 cita cosas distintas. Pero **cada ronda revela la siguiente fabricación** (ReASearch: 4 quejas distintas en 4 rondas, base H1R nunca aprobada → inviable en ≤3 rondas) y WikiSkill muere con **4 salidas `sin líneas parseables` seguidas** tras su r0 efectivo (pre-normalización insuficiente; salidas crudas sin persistir). **M5b jamás disparó**: los `encabezados` del intento 1 se descartan al reintentar (parse final `enc=[]`) — bug medido, declarado para intento 6. 21 de ≤32 llamadas; `evals/HITO8_PLAN.md` §5 → **Intento 6 (Hito 9, CERRADO 2026-10-17): los arreglos A y C funcionan y el fuego seguía encendido por los corchetes** — encabezados-eco alimentan M5b (**SÍ disparó**: 5 secciones vaciadas incluidos l9/l18 de H7), 6 rondas, salida cruda persistida → **G1 5/5 · G2 5/5 · C1' SÍ** y **H5' 3/5** → **NO CUMPLE**. Coste 37/45 (juicios exactos 17/17). Whack-a-mole confirmado a escala (ReASearch ≥7 quejas distintas, Wiki 4→4); **la salida cruda demuestra que la deriva de formato es `[1] -> …` con corchetes** (imita la lista `[i]` del prompt): ReASearch r5/r6 señaló la línea-mole 26 («bloqueo suave», la queja viva) y el encabezado-título, y los corchetes los invalidaron — fuego apagable con normalizar corchetes + suficientes rondas. Base ReASearch 5196→3326 (V1 64% intacto). `evals/HITO9_PLAN.md` §5 → **Intento 7 (Hito 10, CERRADO 2026-10-17): los corchetes cierran el formato y WikiSkill aprueba — ReASearch se topa con los DOS muros pre-declarados** — `[N]` en frase/destino (arreglo A, la deriva medida en H9) + techo de 8 rondas/36 loc (arreglo B) → **G1 5/5 · G2 5/5** y **H5' 4/5** (récord) → **C1' NO** → **NO CUMPLE**. **WikiSkill APRUEBA en run5: primera vez en 7 intentos** — 0 `sin parseables` en toda la corrida (los 5 casos de H9 eliminados), 5 máscaras consecutivas drenan 5 quejas (estratificado → filtrado → Validación pre-release → propuesta → latencia) → R4=OK R5=OK; la mecánica completa queda demostrada punta a punta. ReASearch: **riesgo (a) — cola de moles profunda**: quejas EVOLUCIONANDO en cada ronda efectiva hasta run7 (≥8 pares distintos, run5==run6 solo por no-op); **riesgo (b) — V1**: vaciados de sección consumieron 5196→2994 en 7 rondas, la edición r8 (2 máscaras → 2562) cae a **36 chars del suelo 2598** → rechazada, causa `validacion_tras_edicion` registrada, arnés `ok=False` → C1' NO; sin maquillaje, ambos riesgos pre-declarados en §2. Lección para intento 8: M5b es cara en chars y probablemente innecesaria (H15 solo-máscaras mató anclajes en encabezados; H17 Wiki máscalas de una línea mataron quejas de sección) → solo-máscaras blinda V1 por matemática (2598 chars ≈ decenas de moles). Coste 35/57 (17 juicios + 18 loc), 0 generaciones, suite 323. `evals/HITO10_PLAN.md` §5 → **Intento 8 (Hito 11, CERRADO 2026-10-17): la máscara quirúrgica blinda V1 y expone que el juez no ve la fuente** — span del eco (`parse_localizador.ecos` + `editar_m5(…, ecos=)`, costo 12-158 chars/edición vs 213-416) + 10 rondas + base Wiki = su aprobado H17 → **G1 5/5 · G2 5/5 · C1' SÍ restaurado** (0 fallos; ReASearch termina 2828 > suelo 2598) y **H5' 4/5** → **NO CUMPLE**. Wiki aprueba r0 con base propia. **Riesgo (b) medido**: cola de ReASearch >10 — 11 juicios con quejas todas distintas hasta agotar rondas. **Forense de decisión (hallazgo 10 cuantificado)**: ventana del juez para ReASearch = **1.195 de 138.667 chars (0,86%)**, y sistemática en las 5 (0,9%-10,4%) — `_source_for` hace `LIKE` con etiquetas ES contra texto EN → el juez declara «no menciona» contra ≥90% de fuente invisible; dos lecturas (juez ciego → cola finita con ventana de chunks citados / doc genuinamente fabricado → inalcanzable por edición), ambas discriminables con la misma enmienda → **decisión enmienda-vs-cierre del dueño**. Coste 31/52, suite 328. `evals/HITO11_PLAN.md` §5 → **Intento 9 (Hito 12, CERRADO 2026-10-17): la enmienda 1 se RECHAZA en su propia recalibración — el intento 9 no corrió** — enmienda declarada (ventana por blueprint: chunk0 + citados + top-10 híbrido, `fuente_verificable`, `eval_q1_r4r5.py` byte-idéntico), ratificada por el dueño, implementada con 334 tests → **E12: 0/4 obligatorios aprueban con la ventana rica** (PEARL/PG/TCE/Wiki caen en R4) → §1.D **ENMIENDA RECHAZADA, abort antes de filas H19** (0 filas, 5 juicios). Forense: **las 4 quejas nuevas son FALSAS** (términos verificables en la fuente completa: PEARL 2×, TCE 0.125/0.025 exactos + Tables D/E, Wiki 16×/98×, PG 11×) — la ventana rica-por-recuperación produce falsos positivos; ReASearch sí mezcla verdaderas (`pre-release` 0×). **Salto del hallazgo 10: los veredictos R4/R5 son función de la ventana y ninguna ventana corta probada es estable.** Opciones al dueño: A cerrar H1 / B enmienda 2 fuente completa (63-139K chars, E13) / C verificación mecánica. `evals/HITO12_PLAN.md` §5 → **Enmienda 2 (Hito 13, CERRADO 2026-10-17): fuente completa 3/4 y la puerta 4/4 la rechaza — el único fallo es de PG, cuya aprobación previa era ella misma artefacto** — declaración (`b0d6ab6`) e implementación (`4cde8b6`: `FUENTE_MAX=160000` en `q1` con PROMPT intacto + `fuente_completa` en `tools.py` + runner `run_fase1_h20.py`) ANTES de medir, enmienda + umbrales ratificados; **E13: PEARL/TCE/Wiki OK restaurados** · **PG R4+R5 FALLA** · ReASearch FALLA → **3/4 → §1.D ENMIENDA 2 RECHAZADA, abort, 0 filas H20, coste 5 juicios, suite 338**. Forense de PG con los 131.899 chars visibles: `lesson` 0×/`persist` 0× → queja de lessons **VERDADERA** (la aprobación H17/H18 de PG con ventana 0,9% era artefacto: PG nunca aprobó a un juez que viera su fuente); `refiner` 23× y `mutation` 11× («Feedback-Driven Mutation», «mutation engine» edita aristas del grafo) → quejas **FALSAS** — **incluso con fuente completa el juez erra por nombre-exacto**. ReASearch con fuente completa queda en **1 R4 + 1 R5, ambas verdaderas** — los moles anteriores (stagnation advisory, search-tree…) existen en la fuente y ya no se acusan → **la cola por fin es finita y de 1-2 reparaciones**. Balance al cierre: 3/5 con aprobación verdadera bajo juez que ve su fuente (PEARL/TCE/Wiki) · PG 1-2 quejas verdaderas + 2 falsas encadenables · ReASearch 1-2 verdaderas → decisión del dueño: **A** puerta re-declarada (≥3/4 + forense) e intento 9 con PG y ReASearch al bucle de reparación · **B** cerrar H1 con la evidencia · **C** enmienda 3 de tolerancia semántica (rompe PROMPT intacto). `evals/HITO13_PLAN.md` §5 → **Intento 9 (Hito 14, CERRADO 2026-10-17): NO CUMPLE — los dos arneses fallan por contenido, no por falta de rondas** — puerta forense (aserción E13, 0 llamadas) OK; brazo `H21` con fuente completa → **H5' 3/5** (PEARL/TCE/Wiki r0) · G1 5/5 · G2 5/5 · **C1' NO** → **NO CUMPLE**; coste 18/25 juicios, 21/32 locs, 0 generaciones, suite 338. **PG: riesgos (a)+(b)** — 4 quejas r0 (2 falsas nombre-exacto + 2 verdaderas) → máscaras → quejas estructurales («Módulo 1-3»/«Dependencias» — el paper no describe esa arquitectura) → vacíos de sección → edición r4 = **227 < 1121 (suelo de base 2243) → `validacion_tras_edicion`, `ok=False`**. **ReASearch: riesgo (d)** — cola NO de 1-2 sino **estructural**: 2 quejas × 10 rondas («Módulo 1/2/3», «Orden de Ejecución», umbrales pre-release), fabricación pervasiva que las máscaras individuales no matan; **6 de 10 ediciones no-op** (M1 sin parseables/frase ausente/número fuera de rango) y con no-op el juez repite queja; 5196→2993 con suelo intacto; `NO APRUEBA tras 10`. **Lección del intento 9: bajo el instrumento honesto, H1 no se alcanza editando — la falla de PG y ReASearch es arquitectura inventada en todo el documento (sus aprobaciones previas eran artefacto de la ventana ciega); haría falta regeneración con el juez honesto en el bucle de generación, no de edición.** `evals/HITO14_PLAN.md` §5 | Fase 1 de `evals/HITO3_PLAN.md` · `evals/results/result_q1_r4r5.json` (arm `H1`, `H1R`, `H12`, `H13`) · `evals/run_fase1.py` · `evals/run_fase1_repara.py` · **`evals/HITO5_PLAN.md` §6** · `evals/results/result_fase1_h12.json` · `evals/run_fase1_h12.py` · **`evals/HITO6_PLAN.md` §5** · `evals/results/result_fase1_h13.json` · `evals/run_fase1_h13.py` |
| 27 | **H4 del Hito 3 NO CUMPLE: el A/B de arneses no separa con n=6** — 18/18 runs, 0 infra; placebo OK (0 dentro del IC de FULL−PLAC); **separación NO** (LOW−FULL diff=2.0, IC95=[−0.185, 4.185] — 0 **dentro**). Tres señales: (a) dirección invertida — LOW (4.833) > FULL (2.833), 3/6 de FULL salieron `[doc:?]` vacío; (b) el placebo pasó por **IC ancho, no por igualdad** (A=2.833 vs A'=1.333 con la misma config); (c) **n=6 con juez ruidoso no tiene potencia** — 2.0 puntos de diferencia y el IC cruza 0. Umbral (4) intacto; re-corrida que quiera CUMPLE necesita más n o diseño más estable, con declaración previa del dueño | Fase 4 de `evals/HITO3_PLAN.md` · `evals/results/result_fase4_h4.json` (`h4: false`) · `evals/run_fase4_h4.py` |

---

## 9. Índice rápido — *«¿dónde está X?»*

| busco… | voy a… |
|---|---|
| **cómo trabajar en este repo (reglas, puerta, trampas)** | `AGENTS.md` (raíz) · mapa de `evals/` → `evals/README.md` |
| el propósito del proyecto | `PROPOSITO.md` |
| la regla con la que se mide | `evals/BENCHMARK_SPEC.md` |
| las decisiones numeradas | `evals/BLUEPRINT_METRIC_DESIGN.md` §6 |
| los umbrales | `evals/BLUEPRINT_METRIC_DESIGN.md` §3.1 |
| qué se erró y se declaró | `evals/BLUEPRINT_METRIC_DESIGN.md` §8.8-§8.13 |
| un paper del corpus | `Documentos/` |
| papers de **dominio** (juegos) | `Documentos/game_development/` · DB `data/corpora/game_development.db` |
| el PDF descartado y el motivo | `Documentos/descartados/` · `CONOCIMIENTO.md` §2 «Corpus por dominio» |
| la traducción ES (fuera del inbox, no borrada) | `Documentos/traducciones/` · `CONOCIMIENTO.md` §2 «Higiene de duplicados» |
| **las capas del corpus y el congelado de la eval** | `CONOCIMIENTO.md` §2 «Capas de corpus y CORPUS_LOCK» · `evals/corpus_lock.py` (`label`/`build`/`check`) · `evals/CORPUS_LOCK.json` · filtro `BIBLIOTECARIO_CAPAS` |
| **la ingesta idempotente (upsert por hash → arXiv+path → path)** | `CONOCIMIENTO.md` §2 «Ingesta idempotente» · `ingest/pipeline.py` (`_find_existing`, `_merge_meta`) · `tests/test_upsert.py` |
| **la higiene 16/17 y la guarda anti-pisado** | `CONOCIMIENTO.md` §2 «Higiene de duplicados» · respaldo `/tmp/opencode/bibliotecario_before_higiene_20261021.db` |
| **el tokenizador del canal keyword (siglas, cifras, stoplist)** | `CONOCIMIENTO.md` §2 «Tokenizador compartido» · `core/tokens.py` · `tests/test_tokens.py` · medición `evals/eval_retrieval.py` |
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
| el scorer de Capa B **B-2** (replay + juez multimodal) | `evals/BENCHMARK_SPEC.md` §5.2.1 + enmienda 1 — **desbloqueado en H15, construido y corrido en H16 (2026-10-22)** |
| el scorer B-1 (tests de comportamiento) | **`evals/preflight/suite_runner.py`** + `suites/*.yaml` + `check_suite.gd` |
| **las 52 suites v2 de las tareas reales** | `evals/preflight/suites_v2/<id>.yaml` — escritas 2026-10-15 desde el texto **antes de cualquier generación**, congeladas al escribirse; lint `evals/preflight/lint_suites_v2.py` (55 suites / 576 checks desde H16: 52 reales + 2 fixtures + la ancla `platformer-juego`, exenta porque no está en `game_tasks_expanded.yaml`); método y exclusiones → §5.2.2.c |
| **la base humana de juegos** (72.73–100.00) | `evals/BENCHMARK_SPEC.md` §8.1 · hallazgo en §6.1 |
| el preflight de comportamiento (5/5) | `evals/preflight/test_behaviour.gd` · hallazgo en §6.1 |
| el binario de Godot del arnés | `EG/.tools/godot` — **4.7.1.stable** |
| **la suite ampliada de juegos (60 tareas)** | `evals/game_tasks_expanded.yaml` · §4.4 de `BENCHMARK_SPEC.md` |
| **por qué B-1 no cubre 31 de esas 60** | `evals/BENCHMARK_SPEC.md` §5.2.2 — auditoría de cobertura por familia |
| **contraste de v2 con la literatura (5 papers de dominio)** | `evals/BENCHMARK_SPEC.md` §5.2.2.b — 17 clases: **8 cubiertas · 4 parciales · 5 sin cubrir** — los **3 huecos cerrados y validados 2026-10-15** (A cota de recurso · B error de runtime · C sincronía rítmica); **v2 ratificado 2026-10-15** (dueño: «Ratifica v2»), vigente para medición nueva; recuento previo 6/5/6 estaba mal (errata declarada) |
| **el scorer B-1 v2 (21 checks + BUILD, cierra esa brecha)** | `evals/preflight/check_suite_v2.gd` + `suite_runner_v2.py` · validado en `fixtures/v2_{ok,broken}/` · suites de las 52 tareas en `suites_v2/` · §11 enm. 2 + **enm. 3** (bugfix estáticos/`_ready`, 2026-10-15) · §5.2.2.c · **primer smoke end-to-end 2026-10-15: generación real `card-memory-precision` = 10/10 tras reparación manual de sintaxis** (hallazgo 17 parcialmente cerrado) |
| **la corrida oficial B-2 etapa 2 (ρ oculta, juez multimodal, gates U1-U6)** | `evals/HITO16_PLAN.md` §5 — **NO CUMPLE 2026-10-22** · filas `evals/results/result_fase2_b2.json` · código `evals/preflight/{juez_b2.py, run_fase2_b2.py}` · ρ `evals/preflight/rubricas/platformer-juego.json` · evidencia `evals/preflight/results/b2_etapa2/` |
| **el Hito 3 — plan, umbrales H1-H4 y fases** | `evals/HITO3_PLAN.md` — **CERRADO 2026-10-16** (§9). H1 NO CUMPLE (hallazgo 26) · H2 CUMPLE · H3 CUMPLE con enmienda 1 · H4 NO CUMPLE (hallazgo 27). Arreglo de cierre vacío del loop: `b6740f4`. Hilos abiertos: verificación de atribución (H1), potencia del A/B (H4), juez ciego (hallazgo 10) |
| **el Hito 4 — meta-evolución (hallazgo 4)** | `evals/HITO4_PLAN.md` — **CERRADO 2026-10-16 · CUMPLE 5/5** (§6). Umbrales H5-H8+C1 declarados (`05852c5`) y ratificados por el dueño ANTES de medir; corrida oficial `evals/results/result_hito4_meta.json` con runs guionizadas 0 tokens y DB hermética. Cableado: `harness/edits.py` (tabla `harness_edits`, K=2), `RuntimeHarness.meta_evolve` + `skill_hints`, rehidratación de `auto_pf_*`/`auto_skill_*` en `pfs.py`/`layers.py`, firma `last_error` en `loop.py`. Regresión: `tests/test_meta_evolution.py` (281 tests verdes) |
| **el Hito 5 — cierre de H1 (hallazgo 26)** | `evals/HITO5_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§6). Declaración (`6f17a6a`) e implementación (`c5d5691`) ANTES de medir; umbrales ratificados por el dueño («Ratificar y medir ya») con el env del juez confirmado por él. Resultado: **H5 5/5** (la cláusula de H1 se alcanza por primera vez) · **G1 4/5** (ReASearch 2→0 resueltas) · **G2 2/5** · C1 (291 tests) → **NO CUMPLE global**; PG final 488 chars y ReASearch 440 (borrador de razonamiento del modelo) aprobados por el juez R4/R5. Runner `evals/run_fase1_h12.py` (arm `H12`, juez en el bucle ≤3 rondas, 17 llamadas de las ≤29 declaradas); detector de huérfanas nuevo: `attribution.check_orphan_claims` sumado al informe de `verify_and_mark` (0 tokens, sin reescritura). Filas: `evals/results/result_fase1_h12.json` + juicios `arm=H12` en `evals/results/result_q1_r4r5.json` |
| **el Hito 6 — intento 3 de H1 (hallazgo 26)** | `evals/HITO6_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`6a12f64`) e implementación (`7129440`) ANTES de medir; umbrales ratificados por el dueño («Ratificar y medir ya») con el env del juez confirmado por él. Resultado: **G1 5/5 · G2 5/5** (primeras veces) · **H5' 3/5** (PEARL r2 · PG r1 · TCE r0) · C1' NO (2 fail-fast) → **NO CUMPLE global**; el bloqueo de degradación funciona (stub de 485 rechazado por V1, reintento 2243 aprueba; disco de PG restaurado 488→2360). Runner `evals/run_fase1_h13.py` (arm `H13`, mec 0 tokens + validación V1/V2/V3 con reintento, 18 llamadas de las ≤50 declaradas); nuevos en `attribution.py`: `mech_repair`, `validate_structure`, `encabezados` (+`pos` en `check_attributions`). Filas: `evals/results/result_fase1_h13.json` + juicios `arm=H13` en `evals/results/result_q1_r4r5.json` |
| **el Hito 7 — intento 4 de H1 (hallazgo 26)** | `evals/HITO7_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`d897423`) e implementación (`df59908`) ANTES de medir; desviación §0 ratificada (localizador LLM pequeño en vez de matching literal — LCS medido 8–27), umbrales y env ratificados («Ratificar y medir ya»). Resultado: **G1 5/5 · G2 5/5 · C1' SÍ** (sin fail-fast) · **H5' 3/5** → **NO CUMPLE global**; 0 reescrituras imposibles por construcción, M4 saneó ReASearch 517→5432, veredictos r0 estables. Fracasos: quejas ancladas en encabezados (ReASearch, inmarcables sin romper V2) y marca exacta sin giro de veredicto (WikiSkill l37 → juez repite la queja ×3 → **marcas R6 no honradas**). Runner `evals/run_fase1_h14.py` (arm `H14`, 21 llamadas de las ≤32 declaradas); nuevos en `attribution.py`: `localizador_prompt`, `localizador_reintento`, `parse_localizador`, `marcar_lineas`. Filas: `evals/results/result_fase1_h14.json` + juicios `arm=H14` en `evals/results/result_q1_r4r5.json` |
| **el Hito 8 — intento 5 de H1 (hallazgo 26)** | `evals/HITO8_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`ddb24c2`) e implementación (`cd75e9a`) ANTES de medir; umbrales y riesgos de §1 pre-declarados, ratificados por el dueño («Ratificar y medir ya»). Resultado: **G1 5/5 · G2 5/5 · C1' SÍ** · **H5' 3/5** → **NO CUMPLE global**; 0 generaciones (MASCARA fija), V1/V2 sin fallos. **Hallazgo positivo de la serie**: por primera vez la edición gira un veredicto — máscara de la línea citada (Wiki l37: «estratificado» sale del texto) y el juez **cambia de queja** (whack-a-mole revelado: ReASearch 4 quejas distintas en 4 rondas, base H1R nunca aprobada). Muertes: WikiSkill 4 `sin líneas parseables` seguidas tras r0 efectivo; **M5b nunca disparó** (encabezados del intento 1 descartados al reintentar — bug medido, pendiente de intento 6). Runner `evals/run_fase1_h15.py` (arm `H15`, 21 llamadas de las ≤32 declaradas); nuevos en `attribution.py`: `editar_m5`, `mascarar_lineas`, `mascara_seccion`, `MASCARA` + 3 arreglos del parser (flechas/viñetas, frases ausentes, clave `encabezados`). Filas: `evals/results/result_fase1_h15.json` + juicios `arm=H15` en `evals/results/result_q1_r4r5.json` |
| **el Hito 9 — intento 6 de H1 (hallazgo 26)** | `evals/HITO9_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`ce26baf`) e implementación (`3547bbd`) ANTES de medir; umbrales + coste ≤45 ratificados con los riesgos pre-declarados. Resultado: **G1 5/5 · G2 5/5 · C1' SÍ** · **H5' 3/5** → **NO CUMPLE global**; 37/45 llamadas (juicios exactos 17/17), V1/V2 sin fallos con 5 secciones vaciadas. **M5b dispara de verdad** (encabezados con eco: secciones [9,18] — los anclajes vivos de H7 — más [11] y [1,13]); 6 rondas drenan más moles (whack-a-mole a escala ≥7 quejas). **La salida cruda persistida caza la deriva**: el modelo escribe `[1] -> …` con corchetes (imita la lista `[i]` del prompt) — ReASearch r5/r6 apuntó a la línea-mole 26 y al título con eco y los corchetes los invalidaron. Runner `evals/run_fase1_h16.py` (arm `H16`); parser con formato tolerante (separadores, prefijos, negrilla, eco-prefijo, encabezados-eco) + `loc["salida"]`. Filas: `evals/results/result_fase1_h16.json` + juicios `arm=H16` en `evals/results/result_q1_r4r5.json` |
| **el Hito 10 — intento 7 de H1 (hallazgo 26)** | `evals/HITO10_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`8328999`) e implementación (`000185a`) ANTES de medir; umbrales + coste ≤57 ratificados con los riesgos pre-declarados. Resultado: **G1 5/5 · G2 5/5 · H5' 4/5** (récord) · **C1' NO** → **NO CUMPLE global**; 35/57 llamadas (17 juicios + 18 loc, 0 generaciones), suite 323. **WikiSkill aprueba en run5: primera vez en 7 intentos** — corchetes `[N]` → 0 `sin parseables` en toda la corrida → 5 máscaras consecutivas drenan 5 quejas → R4=OK R5=OK (mecánica completa demostrada). **ReASearch: los dos muros pre-declarados se quemaron** — cola de moles ≥8 pares distintos evolucionando hasta run7 (riesgo a) y V1 a 36 chars del suelo: vaciados 5196→2994, edición r8 → 2562 < 2598 → `validacion_tras_edicion`, `ok=False` (riesgo b); sin maquillaje. Lección: solo-máscaras (sin M5b) blinda V1 por matemática. Runner `evals/run_fase1_h17.py` (arm `H17`); parser con `[N]` en frase/destino. Filas: `evals/results/result_fase1_h17.json` + juicios `arm=H17` en `evals/results/result_q1_r4r5.json` |
| **el Hito 11 — intento 8 de H1 (hallazgo 26)** | `evals/HITO11_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`2e3acab`, con errata del costo de máscaras del Hito 10) e implementación (`9d9357f`) ANTES de medir; umbrales + coste ≤52 ratificados con los riesgos pre-declarados. Resultado: **G1 5/5 · G2 5/5 · C1' SÍ** (0 fallos, V1 2828 > 2598 tras 10 rondas) · **H5' 4/5** → **NO CUMPLE global**; 31/52 llamadas (15 juicios + 16 loc, 0 generaciones), suite 328. **Máscara quirúrgica del eco**: ediciones de 12-158 chars (vs 213-416 de línea completa), `ecos` aditivo en `parse_localizador`, fallback a línea completa; WikiSkill aprueba r0 con su base aprobada H17. **Riesgo (b) medido**: cola de ReASearch >10 moles (11 juicios, quejas todas distintas). **Forense decisivo (hallazgo 10 cuantificado)**: ventana de fuente del juez = 1.195/138.667 chars (0,86%) para ReASearch; las 5 técnicas 0,9%-10,4% — `LIKE` con etiquetas ES sobre texto EN en `_source_for`; cola bottomless explicada por juez sin fuente → decisión enmienda-vs-cierre. Runner `evals/run_fase1_h18.py` (arm `H18`). Filas: `evals/results/result_fase1_h18.json` + juicios `arm=H18` en `evals/results/result_q1_r4r5.json` |
| **el Hito 12 — intento 9 de H1 / enmienda 1 (hallazgo 26)** | `evals/HITO12_PLAN.md` — **CERRADO 2026-10-17 · ENMIENDA RECHAZADA, intento 9 NO CORRIDO** (§5). Declaración (`25680f6`) e implementación (`cb55a95`) ANTES de medir; enmienda + umbrales ratificados por el dueño. **E12 recalibración: 0/4 obligatorios aprueban con la ventana rica** → §1.D abort antes de filas H19 (0 filas, 5 juicios, sin localizadores). Forense: las 4 quejas nuevas de PEARL/PG/TCE/Wiki son **falsas** contra la fuente completa (términos presentes: 2× / mutation 11× / 0.125+0.025+Tables D-E / gating+rbest+qwen 98×); ReASearch mezcla verdaderas y falsas. Lección: veredictos R4/R5 dependen de la ventana; ninguna ventana corta probada es estable. Nuevos: `fuente_verificable` en `bibliotecario/agent/tools.py` (chunk0+citados+top-10 híbrido sin LLM), fase `_calibracion`/E12 con abort en `evals/run_fase1_h19.py`, 6 tests → suite **334**. Juicios `arm="E12"` en `evals/results/result_q1_r4r5.json`; sin filas H19 |
 | **el Hito 13 — intento 9 de H1 / enmienda 2 (hallazgo 26)** | `evals/HITO13_PLAN.md` — **CERRADO 2026-10-17 · ENMIENDA 2 RECHAZADA, intento 9 NO CORRIDO** (§5). Declaración (`b0d6ab6`) e implementación (`4cde8b6`) ANTES de medir; enmienda + umbrales ratificados por el dueño. **E13 con fuente completa (`FUENTE_MAX=160000`, PROMPT intacto): PEARL/TCE/Wiki OK (restauran — confirmación del forense E12), PG FALLA, ReASearch FALLA → 3/4 → §1.D abort antes de filas H20** (0 filas, 5 juicios, sin localizadores). Forense: quejas de PG mixtas (lessons VERDADERA — `lesson`/`persist` 0× — + refiner/mutation FALSAS por nombre-exacto con la fuente completa a la vista); ReASearch con fuente completa queda en **1 R4 + 1 R5, ambas verdaderas** → cola finita de 1-2 reparaciones (primera vez). Nuevo: `fuente_completa(tech)` en `bibliotecario/agent/tools.py`, `FUENTE_MAX` en `evals/eval_q1_r4r5.py`, runner `evals/run_fase1_h20.py`, 4 tests → suite **338**. Juicios `arm="E13"` en `evals/results/result_q1_r4r5.json`; sin filas H20. Balance: 3/5 con aprobación verdadera (PEARL/TCE/Wiki) · A/B/C al dueño |
 | **el Hito 14 — intento 9 de H1 / puerta forense (hallazgo 26)** | `evals/HITO14_PLAN.md` — **CERRADO 2026-10-17 · NO CUMPLE** (§5). Declaración (`68d91c0`) e implementación (`aabf050`) ANTES de medir; umbrales + coste + riesgos (a)-(e) ratificados por el dueño. Puerta forense = aserción del patrón E13 (0 llamadas nuevas) → OK; corrida oficial con brazo `H21` y fuente completa → **H5' 3/5 · G1 5/5 · G2 5/5 · C1' NO**; coste 18/25 juicios, 21/32 locs, 0 generaciones, suite 338. **PG** muere por V1 (227 < 1121) tras cadena de quejas falsas+estructurales con vacíos de sección (riesgos a+b); **ReASearch** no converge en 10 rondas: 2 quejas/ronda de familia **estructural** (Módulo 1/2/3, Orden de Ejecución) + 6 de 10 ediciones no-op (riesgo d). Rotación LLM operó sin abortar (c). Conclusión del hilo: **bajo instrumento honesto la falla de PG/ReASearch es arquitectura inventada pervasiva — editable no converge; regeneración sería otra enmienda**. Runner `evals/run_fase1_h21.py`; filas `evals/results/result_fase1_h21.json` + juicios `arm="H21"` |
 | **el Hito 15 — B-2 etapa 1: trazas `Π` + replay sin juez (hallazgo 16)** | `evals/HITO15_PLAN.md` — **CERRADO 2026-10-17 · CUMPLE** (§5). Declaración (`fac658e`) e implementación (`71b2ef7`) ANTES de medir; T1-T5 + riesgos (a)-(e) + congelados ratificados por el dueño; corrida oficial única con **coste 0 tokens LLM**. **T1** captura 8 eventos/3833 ms/schema [] · **T2** dos capturas byte-idénticas (t_ms por tick; Xvfb == `:0`) · **T3** replay exit 0, 14 frames 0 negros, lum 78.31, 0 fallos xdotool, ventana 0,0, frame inspeccionado = juego real · **T4** hash ReaGame intacto (`255883e3…`, 651 archivos) · **T5** suite 350 + ruff. Dos bloqueos WSL medidos y resueltos en la corrida (riesgo a): `/tmp/.X11-unix` tmpfs **ro** → Xvfb por **TCP** (`-listen tcp -ac`, `localhost:99`), y `:0` da frames negros → `--position 0,0` + Xvfb; la ruta `:0` fallida queda en `report_b2.json` como evidencia. Artefactos: `evals/preflight/{pi_capture.gd,pi_actor.gd,pi_schema.py,replay_pi.py,pi_scripts/default.json}` + `tests/test_pi_pipeline.py` (12) + `evals/preflight/results/b2_etapa1/` (mp4/frames gitignorados). **No ratificados (Hito 16): scorer B-2, rúbrica `ρ`, juez multimodal** |
 | **el Hito 16 — B-2 etapa 2: scorer con juez multimodal sobre ρ oculta (hallazgos 13 y 16)** | `evals/HITO16_PLAN.md` — **CERRADO 2026-10-22 · NO CUMPLE** (§5). Declaración (`eea92ab`) e implementación (`196d54b`) ANTES de medir; §2-§3 + fila §11 ratificados por el dueño (`20cad5d`, 2026-10-21) **antes de la corrida**; ningún umbral tocado tras medir. Corrida oficial única con datos (intento 4): **U1 ✅ · U3 ✅ · U5 ✅ · U6 ✅ · U2 ❌ · U4 ❌** → NO CUMPLE. **U2**: juez caucho — 14 frames negros puros (lum 0.000) con 10 presencias ≠0 y Score_B2 0.7762 > 0.30. **U4**: Score(default)=Score(idle)=0.3096 (Δ=0) pese a default evolucionar 5,38% de píxeles vs 1,61% idle; B-1 sí prueba `jugador-mueve dx=200` → discrepancia replaey↔B-1 para el dueño. 4 intentos previos sin medición (suite ancla inexistente → Π vacía de `idle` → 503 sin reintento → 503 con reintento) con coste efectivo 0; corrida: **5/10 llamadas, 82.855 tokens, Score_final (dato) 0.4346, M_B1 0.8333** (9/11: Coin/Goal en `levels/mision1.tscn`, no en `main.tscn`). Artefactos: `evals/preflight/{juez_b2.py, run_fase2_b2.py, rubricas/platformer-juego.json, suites_v2/platformer-juego.yaml, pi_scripts/idle.json}` + `tests/test_juez_b2.py` (26) → suite **425**; evidencia `evals/results/result_fase2_b2.json` + `evals/preflight/results/b2_etapa2/` |
| **el Hito 17 — grounding del juez (ratificado + implementado)** | `evals/HITO17_PLAN.md` — **DECLARADO `10ae417` → RATIFICADO `35ffca6` 2026-10-22 (opción B — prefiltro no-LLM; gates §2 U1-U7 ☑ ANTES de implementar y de medir) → IMPLEMENTADO (§1.B)**: `evals/preflight/{prefiltro_b2.py, run_fase2_b2_h17.py, rubricas/grounding-trampa.json}` + enmienda 5 de §11 de `BENCHMARK_SPEC.md` + 10 tests (`tests/test_prefiltro_h17.py`). Prefiltro: caso con TODOS los frames planos → juez no llamado (0 llamadas), ítems 0 por construcción (U2 por construcción). U7: trampa sintética al juez crudo (con ≥0.5 / vacío = 0). Motivación: fallos de grounding de H16 (U2 caucho 0.7762; U4 Δ=0.0) — citas en «Anexo A» de `evals/HITO16_PLAN.md` §5. **Pendiente: corrida oficial única → §5 (veredicto)**; sin llamadas al juez hasta entonces. Commits ASCII; disciplina §4 |
| **los arneses regenerados por la ruta verificada** | `evals/run_fase1.py` + `evals/run_fase1_repara.py` · filas `H1`/`H1R` en `evals/results/result_fase1_h1.json` y `result_fase1_h1r.json` · juicios en `evals/results/result_q1_r4r5.json` · producto en `data/agents/<slug>/BLUEPRINT.md` (gitignored) |
| **el arnés como composición de las 4 capas (Fase 2 del Hito 3)** | decisión del dueño 2026-10-16 · plantilla generada en `bibliotecario/agent/tools.py` (`instantiate_agent_template`, con `bp=` opcional para regenerar sin LLM) · medición H2 en `evals/run_fase2_h2.py` → `evals/results/result_fase2_h2.json` · 277 tests y fila D 5/5 en verde con el arnés nuevo |

---

*Regla: si algo se aprende, se anota aquí **con su ruta**. Un conocimiento sin
ruta no se puede recuperar, y uno recuperable que no se documenta se pierde igual.*
