# AGENTS.md — cómo trabajar en este repo

Si estás leyendo esto, eres el agente de turno (humano o LLM). El proyecto
**no depende de la memoria de nadie**: todo lo que necesitas está aquí.
Orden de lectura recomendado:

1. `PROPOSITO.md` — qué mide el proyecto y con qué fórmulas.
2. `CONOCIMIENTO.md` — **mapa maestro**: estado, decisiones, hallazgos, veredictos por hito.
3. `evals/BENCHMARK_SPEC.md` — la regla de medición (§11 = qué está ratificado).
4. `evals/BLUEPRINT_METRIC_DESIGN.md` — umbrales y decisiones numeradas.
5. `evals/README.md` — qué es cada fichero de `evals/`.
6. Planes `evals/HITO*_PLAN.md` — qué se prometió en cada hito y su veredicto (§5 de cada uno).

## Reglas duras

- **Disciplina de medición**: se ratifica ANTES de medir; los umbrales NO se
  tocan tras medir; si un gate falla → **NO CUMPLE con evidencia** y decisión
  del dueño. Nunca hay corridas "de prueba" con resultado favorable escondido:
  los intentos fallidos se documentan con su causa y su coste.
- **Idioma**: documentación y mensajes de commit en español; los mensajes de
  commit van **en ASCII sin acentos**.
- **Commits/push**: solo según el plan del hito (cada plan declara su
  disciplina en su §4) o si lo pide el dueño. Revisa `git status`/`git diff`
  antes; nunca subir `.env` ni claves.
- **Secretos**: `.env` (gitignored) guarda `NVIDIA_API_KEY`, `GEMINI_API_KEY`
  y demás. **Jamás imprimirlas ni commitearlas.** Escaneo antes de cada commit:
  `git diff --cached | grep -cE "nvapi-[A-Za-z0-9]{6}"` debe dar 0 (ojo: el
  patrón literal `nvapi-` aparece en este propio fichero como ejemplo — por
  eso el scan exige carácter alfanumérico tras el guion; y `grep -c` sin
  coincidencias devuelve exit 1 y rompe cadenas `&&`; usa `;` o `|| true`).
- **Claves y presupuesto (política del dueño 2026-10-23)**: `NVIDIA_API_KEY` =
  SIEMPRE bibliotecario (la app); `NVIDIA_API_KEY_PILOTO` = SIEMPRE las corridas
  de evaluación (`run_pilot.py` la aplica sola y avisa si falta). Gemini: SIEMPRE
  `GEMINI_API_KEY` (principal; `_2`/`_3` solo si falta la principal, sin
  rotación). **Antes de cada run nueva**: `evals/sd_pilot/run_pilot.py
  --presupuesto --max-turns T --n-tareas N --techo TECHO` (turnos y coste de
  antemano) y declarar el techo en el plan del hito antes de lanzarla.
- **`EG/`, `EW/`, `TraceForge/` son otros repos/trabajos externos**: en este
  proyecto son **solo lectura**. Todo trabajo con el workspace de Godot se hace
  en copias temporales. Binario: `EG/.tools/godot` (4.7.1.stable). En WSL la
  única pantalla válida es Xvfb en `localhost:99` (`:0`/WSLg da frames negros;
  `/tmp/.X11-unix` es tmpfs ro → Xvfb necesita `-listen tcp -ac`).
- **Base de datos**: `data/bibliotecario.db`. Los tests NO la tocan (usan una
  DB tmp). Para operaciones destructivas: respaldo previo. Para cascadas FK
  hay que usar `storage.get_conn()` (pone `PRAGMA foreign_keys=ON`); una
  conexión `sqlite3` cruda no borra en cascada y deja huérfanos.

## Puerta (gates) — ejecutarla antes de cada commit

```bash
.venv/bin/python -m ruff check bibliotecario tests evals/corpus_lock.py
.venv/bin/python -m pytest tests/ -q          # 513 tests, ~2.5 min
.venv/bin/python evals/preflight/lint_suites_v2.py   # si se toca preflight/
.venv/bin/python evals/corpus_lock.py check          # si se tocó el corpus
```

Python **siempre** con `.venv/bin/python` (no `python` suelto).

## Convenciones de `evals/`

- Ver `evals/README.md`: mapa por clases, decodificador de nombres
  (`result_fase1_h14.json`, `run_*`, logs) y qué es intocable.
- **La evidencia (`result_*.json`) no se borra ni se edita**; es la prueba de
  lo medido. Los `.log` son el stdout de su corrida.
- Los planes `HITO*_PLAN.md` son contrato: su §4 declara la disciplina del
  hito y su §5 el cierre con veredicto. Lo que el plan dice que está
  "congelado" (juez, prompts, pesos, umbrales) no se modifica sin enmienda
  ratificada.

## Trampas conocidas (ya mordidas)

- `grep -c` con 0 coincidencias → exit 1 → rompe `&&`.
- El juez B-2 (`evals/preflight/juez_b2.py`) tiene un **fallo de grounding
  medido**: inventa contenido sobre frames negros (U2). No confíes en un
  Score_B2 sin leer `evals/HITO16_PLAN.md` §5.
- `Score_final` en `evals/results/result_fase2_b2.json` es **dato, no nota**,
  si la corrida es NO CUMPLE.
- Los gates y corridas oficiales viven en `evals/preflight/`; los runners
  necesitan env (`Q1_API_KEY`, `Q1_BASE_URL`) — el patrón exacto de export
  está documentado en `_endpoint()` de `juez_b2.py`.
- Sed de mudanza `s|evals/result_|evals/results/|g` **come el prefijo
  `result_`** (deja `evals/results/fase2_b2.json`). Usa
  `s|evals/result_|evals/results/result_|g` y verifica con un path conocido
  (que `evals/results/result_fase2_b2.json` exista y las rutas citadas en
  doc apunten a él) antes de confiar en el barrido.
- Si algo de la raíz de `evals/` no aparece en `evals/README.md`, añádelo
  ahí al crearlo: el mapa se mantiene con cada cambio.
