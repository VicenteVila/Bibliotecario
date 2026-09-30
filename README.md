# Bibliotecario

Agente de búsqueda tipo **ReASearch** sobre papers ingeridos: responde preguntas con citas
`[doc:chunk]` y produce **blueprints de implementación** (+ plantillas de agente instanciables)
para aplicar las técnicas de esos papers en agentes nuevos.

Greenfield en Python 3.12 + SQLite + Gemini cloud + embeddings locales (SentenceTransformers).
Interfaz: **librería + CLI** (sin bot/API/dashboard).

## Papers fundacionales

| Paper | Módulo(s) | Aporte |
|---|---|---|
| *The Optimizer Is the Agent: Reasoning-Driven Search across Prompts, Programs, and ML Workflows* (Li et al., UT Austin + Snowflake, arXiv:2608.06714) — **documento padre** | `agent/` | Scaffold ReASearch: loop tool-using, system prompt en 2 capas, estado re-emitido por turno, `compact()`, `lessons.md`, avisos de estancamiento 3+/7+ |
| *PEARL: Path-Entity Aligned Relational Learning with Contextual Subgraphs for Inductive KGC* | `knowledge/pearl.py`, `memory/` | Subgrafo contextual por consulta, retrieval de caminos guiado por LLM (LPRA), filtro dual-view, agregación camino-entidad |
| *Procedural Graphs: Self-Evolving Execution Structures for LLM Agents* | `knowledge/procedural.py`, `knowledge/refiner.py` | Tripletas `(procedure, relation, procedure)` autoevolutivas; refiner que contrasta trayectorias fallidas vs exitosas |
| *WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution* | `coevolve/wiki.py` | Wiki persistente multicapa (raw/accumulated/skill), gating + rollback, muestreo estratificado, skills transferibles |
| *Task-CoEvolve: Efficient Harness Optimization via Adaptive Validation Task Selection* | `coevolve/selector.py`, `coevolve/estimator.py` | Selección por varianza ponderada (ec. 2), estimación full-set Hájek/anclada-diferencia (ecs. 3-4), selección Ŝ-max |

Base portada: **Asubarnipal** (commit `50a37b5`), con 10 bugs corregidos (detallados en el historial):
tabla `embeddings` huérfana eliminada, ponderación híbrida unificada (0.5/0.3/0.2),
upserts con `ON CONFLICT` que preservan FKs y metadata, sin FAISS duplicado,
harness habilitado por defecto con runs persistidos, precondiciones PF tolerantes
(clave plana y anidada), FallbackPF a Gemini, PFs cableados al loop.

## Quickstart

```bash
/usr/bin/python3 -m venv ~/.venvs/bibliotecario
~/.venvs/bibliotecario/bin/python -m pip install -e ".[dev]"
printf 'GEMINI_API_KEY=...\n' > .env && chmod 600 .env   # nunca se commitea
bibliotecario repl
```

Comandos: `status` · `ingest <pdf|url|youtube|img|txt|docx> [--ocr]` ·
`ingest-dir <carpeta> [--ocr]` (lote: omite no-soportados y duplicados por hash) ·
`ask "<pregunta>" [--turns N]` · `blueprint <técnica> <objetivo>` ·
`implement <técnica> <objetivo>` · `evolve` (co-evolución en background).

```python
import bibliotecario.api as API
API.init()
API.ingest("paper.pdf")
API.ask("¿Qué es la selección por varianza ponderada?")
API.implement("Task-CoEvolve", "validar mi agente")
```

## Tests

```bash
python -m pytest tests/ -q   # 72 tests
ruff check bibliotecario tests
```

## Evaluación

```bash
python evals/eval_retrieval.py                    # métricas mecánicas de retrieval
python evals/eval_end2end.py --turns 5            # loop completo + judge
```

El golden set (`evals/golden_qa.jsonl`) son 15 preguntas de dificultad creciente.
Retrieval a nivel de documento: recall@1 `0.933`, recall@3/5 `1.0`, MRR `0.956`.
End-to-end: `judge_mean 4.38`, `provenance 0.90`, 93 % de respuestas con cita,
0 truncadas, 0 fallbacks de proveedor.

El `judge_mean` es **estocástico** (mismo modelo, temperatura > 0): tres runs
idénticos dieron 3.33–3.71 antes del barrido profundo, con σ ≈ 0.19. Para judging
de cambios pequeños hay que comparar varios runs, no uno. Las métricas
deterministas (`recall`, `provenance`, `truncadas`) sí son señal fiable.

## Notas operativas

- Cadena de proveedores con failover, en orden: **Groq** (`GROQ_API_KEY`, `llama-3.3-70b-versatile`)
  → **NVIDIA NIM** (`NVIDIA_API_KEY`, `nvidia/nemotron-3-super-120b-a12b`, fallback
  `openai/gpt-oss-20b`) →
  **Gemini** (`GEMINI_API_KEY[_N]`, `gemini-3.6-flash`; `gemini-2.5-flash` fue retirado por Google).
  Modelos configurables con `GROQ_MODEL` / `NVIDIA_MODEL`.
- El cierre del loop añade un **barrido profundo** determinista (`deep_sweep`): mejores
  chunks por relevancia, por léxico de la pregunta y por cobertura uniforme del paper.
  Sin coste de LLM ni varianza. Es lo que permite responder preguntas de detalle
  concreto (una cifra, una regla de desempate) que viven en un apéndice y no aparecen
  en el top-8 por relevancia.
- Solo se usan los proveedores con key presente en `.env`; 401/403 salta de proveedor,
  429/500/503 reintenta con backoff y luego salta. Pacing de 10 s por proveedor.
- OCR por visión sigue en Gemini (Groq/NVIDIA no exponen visión aquí).
- Sin cuota el sistema degrada con gracia: ingesta digital, búsquedas híbridas
  (ranking estructural local), `status` y `evolve` siguen operativos.
- `data/`, `.env`, `*.db`, PDFs/DOCX fuente: fuera de git por diseño.
