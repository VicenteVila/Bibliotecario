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
python -m pytest tests/ -q   # 42 tests
ruff check bibliotecario tests
```

## Notas operativas

- Modelo: `gemini-3.6-flash` (`gemini-2.5-flash` fue retirado por Google).
- Keys en cadena con failover: `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, … — ante 429/503
  con backoff y salto de key; 401/403 salto directo. Cuota free ≈ 5 req/min.
- Sin cuota LLM el sistema degrada con gracia: ingesta digital, búsquedas híbridas
  (ranking estructural local), `status` y `evolve` siguen operativos.
- `data/`, `.env`, `*.db`, PDFs/DOCX fuente: fuera de git por diseño.
