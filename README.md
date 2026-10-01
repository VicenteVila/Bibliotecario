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
python evals/eval_end2end.py --golden golden_blind_qa.jsonl --turns 4 \
       --provider nvidia --out result_blind_r1.json   # evaluación ciega
```

### Set ciego (el que cuenta)

`evals/golden_qa.jsonl` son 15 preguntas **vistas**: se depuraron mirando los
fallos del agente, así que sus métricas están sesgadas al alza.

`evals/golden_blind_qa.jsonl` son 40 preguntas escritas leyendo los chunks,
sin ejecutar el agente ni el juez. 8 por paper, 35 respondibles y 5 no
respondibles (una por paper, para medir abstención real). Agente pineado con
`--provider nvidia` y juez en `openai/gpt-oss-20b`, de familia distinta.

**Resultado: `judge_mean 4.310`, IC 95 % ± 0.264** sobre 3 runs × 33-35
respondibles (4.171 / 4.273 / 4.486; r2 tiene 2 caídas de infraestructura que se
excluyen de la media). `cite_precision 0.900`, `abstain_rate 0.867`, ~646k
tokens de agente por run.
Detalle completo en `evals/REPORT_BLIND.md`; datos en `evals/result_blind_r*.json`.

Un 504 del proveedor **no cuenta como nota del agente**: la fila lleva
`infra_error` y queda fuera de `judge_mean`. Sin eso, dos caídas bajaban la media
de r2 de 4.273 a 4.029 sin dejar rastro en ninguna métrica.

El ruido **dentro** de una misma pregunta es `σ = 0.709`, contra `σ = 0.952`
**entre** preguntas. Comparar dos sistemas sobre las mismas 35 preguntas con
3 runs cada uno detecta diferencias de **0.112** al 95 %; con una sola run
serían 0.194. Por eso hay que repetir: 5 preguntas tienen `σ ≥ 1.7` y barcan
la escala entera entre runs (`tce-b5` fue 5, 3 y 0).

Dos cosas que la eval ciega desmintió:

- **La etiqueta de dificultad no predice el rendimiento.** Las "difíciles"
  puntúan 4.667 y las "fáciles" 4.083. Etiquetaba cuántos chunks había que
  combinar, no cuánto le costaba al agente.
- **La abstención no está calibrada.** Se abstiene bien en 13/15 no respondibles,
  pero `tce-b3` y `tce-b4` son abstenciones *falsas* que se repiten en las 3
  runs, con la respuesta presente en el corpus. No distingue "no está" de "no
  lo he retrieved", así que un `abstain_rate` alto no prueba que sepa callarse.
  Míralo junto a `false_abstention_rate`.

### Set antiguo

Retrieval a nivel de documento sobre el set de 15: recall@1 `0.933`,
recall@3/5 `1.0`, MRR `0.956`. End-to-end: `judge_mean 4.38`, `provenance 0.90`.

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
