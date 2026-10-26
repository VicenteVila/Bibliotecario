# HITO26 — producto 0-token: compilar conocimiento y conectar coevolve

Estado: **CERRADO 2026-10-26 — H26-B Fase 1 CERRADA; Fase 2 ejecutada en
`HITO27_PLAN.md`**. Este hito no mide arneses ni lanza LLM. Cierra la línea SD
y ataca los huecos de producto que quedaron abiertos: `skills=0`,
`memory_items=0`, `coevolve` sin llamantes y `MT.recall` sin ruta de uso.

## 1. Objetivo

Convertir conocimiento ya pagado en artefactos usables, sin gastar tokens:

1. Compilar las páginas `study` de la wiki a `memory_items`.
2. Compilar el grafo procedimental a `skills` transferibles.
3. Exponer una foto read-only del pool Task-CoEvolve para planificar B-1/B-2.
4. Dar al agente una tool determinista para recuperar memoria.
5. Dejar B-1/B-2 y la medición de transferencia para una fase posterior con
   plan, techo y gates propios.

## 2. Alcance y disciplina

- **0 tokens LLM**: no se llama a `generate()`, `refiner`, `study_paper` ni a
  ningún proveedor. Los embeddings no son necesarios en este corte.
- No se toca `evals/BENCHMARK_SPEC.md`, `CORPUS_LOCK.json`, evidencia H22-H24
  ni fixtures SD.
- No se lanza SD-5, B-1, B-2 ni ninguna corrida de agente.
- `compile` es **dry-run por defecto**; solo escribe con `--apply`.
- Antes de un `--apply` sobre `data/bibliotecario.db`: copia de seguridad
  explícita. Los tests usan DB temporal.
- No se editan las 24 tareas SD ni se reabre H24.
- No hay commit ni push sin petición del dueño.

## 3. Diseño de la Fase 1

### 3.1 `coevolve/compiler.py`

- `compile_studies(apply=False)`: lee `wiki_pages.kind='study'` y crea un
  `memory_items` L2 por estudio, con marca `[study:<slug>]`. Idempotente: si
  la marca existe, no duplica; si el cuerpo cambió, actualiza el mismo item.
- `compile_skills(apply=False)`: lee las técnicas y sus procedimientos del
  grafo, ordena la cadena con las aristas `procedural` y crea un skill
  `tech_skill_<slug>` con `trigger: <técnica>` e `intervention: <cadena>`.
  Pasa por `coevolve.wiki.gate_skill` con score de cobertura del grafo.
- `snapshot(rho=0.2, seed=0)`: lee `task_pool.task_stats()`, calcula pesos con
  `selector.weights` y muestra el subconjunto que se evaluaría. **No estima ni
  puntúa**: sin outcomes de un candidato no hay nada que estimar.
- `run(apply=False)`: agrega los tres informes y declara `llm_tokens=0`.

### 3.2 Memoria y uso

- `memory_tree.recall_text(query, top_k)`: recuperación léxica determinista
  sobre `memory_items`, con decaimiento y refuerzo. No requiere embeddings.
- Tool `recall_memory` en `agent/tools.py`: el agente puede consultar la
  memoria sin cargar el modelo de embeddings.
- `ProceduralSkillLayer.load_from_db()` carga también `tech_skill_*`, no solo
  `auto_skill_*`.

### 3.3 Superficie de producto

- `API.compile_knowledge(apply=False)`.
- `API.coevolve_status(rho, seed)`.
- CLI: `bibliotecario compile [--apply]` y `bibliotecario coevolve [--rho]`.

## 4. Gates declarados antes de medir

| id | gate | umbral |
|---|---|---|
| **G1** | compilación idempotente | segunda pasada con `apply=True`: `created=0` en memoria y skills; contadores no cambian |
| **G2** | cobertura de estudios | 10/10 páginas `study` representadas en `memory_items` |
| **G3** | cobertura de técnicas | ≥1 `tech_skill_*` por técnica con procedimientos; `skills ≥1` |
| **G4** | cero LLM | `generate` parcheado para lanzar excepción: `compile` y `snapshot` terminan OK |
| **G5** | memoria usable | `recall_text` devuelve el estudio relevante y no devuelve nada para una consulta sin solape |
| **G6** | tool expuesta | `recall_memory` está en `TOOLS` y devuelve los hits de G5 |
| **C1** | control | suite completa en verde; sin cambios en evidencia, locks, umbrales ni SD |

## 5. Fuera de alcance de esta fase

- Medir transferencia corpus → arnés: requiere B-1/B-2 y una corrida con plan,
  techo y gates nuevos.
- Promover automáticamente skills desde lecciones vacías o ruidosas.
- Sustituir el retrieval de papers por la memoria; son canales distintos.
- Embeddings de memoria: se posponen para no cargar modelos ni red en este
  corte. `recall_text` cubre la recuperación determinista.

## 6. Cierre de Fase 1 — 2026-10-25

| id | medido | veredicto |
|---|---|---|
| **G1** | segunda pasada `--apply`: `studies.created=0`, `existing=10`, `updated=0`; `skills.created=0`, `updated=0`; `memory_items=10`, `skills=14` | ✅ |
| **G2** | 10/10 páginas `study` → `memory_items`; 0 duplicados | ✅ |
| **G3** | 14/14 técnicas con procedimientos → `tech_skill_*`; `skipped=[]` | ✅ |
| **G4** | `generate` parcheado para fallar; `compile`/`snapshot` OK; CLI real con `llm_tokens=0` | ✅ |
| **G5** | `recall_text("muestreo varianza")` recupera el estudio; consulta sin solape devuelve `[]`; `recall` vectorial ignora los ítems sin embedding | ✅ |
| **G6** | `recall_memory` en `TOOLS`; devuelve los hits de G5 | ✅ |
| **C1** | suite completa **566 passed** (292,55 s); ruff limpio; secretos 0 en 1.725 ficheros | ✅ |

Estado real tras `compile --apply`: `memory_items 0→10`, `skills 0→14`,
`wiki_pages 35→49`; pool intacto en **99 tareas / 667 outcomes**. Copia previa
en `/tmp/opencode/bibliotecario.db.bak-h26-20261025-233132`.

Coste LLM: **0 tokens**. No se lanzó B-1/B-2 ni ninguna corrida de agente en
esta fase. La Fase 2 se ejecutó aparte en `evals/HITO27_PLAN.md` (B-1 v2,
4 tareas × 2 brazos, 42.710 tokens); B-2 no se usó. No hay commit ni push.
