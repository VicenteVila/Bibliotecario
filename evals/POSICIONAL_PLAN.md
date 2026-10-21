# MEDIDA 1 — citas posicionales `[N]` (brazo P) — plan pre-registrado

*(Declaración ANTES de medir — plan SOLO commiteado.)*

## §0 — Estado y problema medido

- **Problema** (analisis de la critica de los tres PDFs, 2026-10-21): la fuente
  se presentaba al modelo como `[chunk 41]` **sin `doc_id`**, y R1 exige
  `[doc:<id>:<chunk>]` → el modelo **adivinaba el `doc_id` en cada puntero**.
  `normalize_pointers` (`knowledge/study.py`) preserva esos números
  inventados y `check_attributions` los cobra como `puntero_roto`.
- **Implementado y verde antes de medir** (2026-10-21):
  `agent/tools.py` — `_fuente_numerada`, `_POS_CITE`,
  `map_positional_citations`, `_WRITING_RULES_NUM`,
  `build_blueprint(..., positional=False, temperature=None)`;
  `agent/loop.py` — `run_blueprint(..., positional=False)`;
  `api.blueprint_positional` (brazo P);
  `tests/test_positional_citations.py` (8 tests) — **suite 382/382, ruff limpio**.
- **Brazos previos** en `evals/result_blueprint_ab.json`: mismas 5 técnicas
  (PEARL, Procedural Graphs, ReASearch, Task-CoEvolve, WikiSkill) × 3 runs ×
  brazos B/C/D/E. Valores de referencia hoy medidos (promedio/run):

  | brazo | citas | resueltas | ratio B8 | anclas | B11 copiadas | truncados |
  |---|---|---|---|---|---|---|
  | B | 2.47 | 0.20 | 0.081 | 0.00 | 0.53 | 0 |
  | C | 5.33 | 2.73 | 0.513 | 0.00 | 0.00 | 0 |
  | E (ruta del arnés) | 8.67 | 7.40 | 0.854 | 0.00 | 0.00 | 0 |

## §1 — Diseño del brazo P

- **P = C + un solo cambio: el formato de citado** (P2-pos). Mismo loop
  reúnidor de evidencia, mismo presupuesto (`BLUEPRINT_MAX_TOKENS`), misma
  temperatura por defecto que B..E, misma BD. La fuente se presenta como
  `[1]`, `[2]`…, R0 delimita los punteros permitidos a `[N]`, y
  `map_positional_citations` reescribe `[N]` → `[doc:doc_id:chunk]` **por
  código, sin tocar la prosa** (doctrina P3/P4: solo ediciones
  deterministas entre corchetes).
- **Comparación primaria: P vs C** (aisla el formato). **Secundaria: P vs E**
  (contra la ruta del arnés hoy).
- **Fallo nuevo posible y dónde se cobra**: índice fuera de rango → escribe
  `[doc:0:0]`; el `check_attributions` existente lo caza como `puntero_roto`
  (o cae en `citas_resueltas=0` de B8). No se añade máquina nueva aguas abajo.
- **Métricas**: `score()` del runner (B8, R7, B9', B11, truncados) + stats del
  mapper `{mapeados, fuera_de_rango}` por run. R4/R5 con el juez existente
  (`evalq1_r4r5`) sobre el blueprint cruto: corrida aparte, criterio
  secundario.

## §2 — Criterio (ratificar ANTES de correr)

La Medida 1 **PASA** solo si, sobre las 5 técnicas previas × 3 runs (15 runs
de P):

| # | criterio | umbral |
|---|---|---|
| 1 | `fuera_de_rango` (el mapper no inventa índices) | **0.00/run** |
| 2 | B8: `citas_resueltas / citas` | **≥ 0.854** (la de E, sin empeorar el arnés) |
| 3 | Volumen de citas: `citas/run` | **≥ 5.33** (la de C: el formato no puede abaratar la cita) |
| 4 | Sin regresión colateral | B11 copiadas = 0.00 · truncados = 0 · anclas ≥ 0.000 · R7 sección ≥ C |
| 5 | (secundario) R4/R5 del juez | no empeora vs E (mismo prompt congelado) |

Cualquier fallo → **NO PASA con evidencia**; sin redefinir umbrales tras
medir. Si falla solo el 5, decisión del dueño con la evidencia a la vista.

## §3 — Congelados

- `map_positional_citations` y `_WRITING_RULES_NUM` tal como se commitearon;
  `positional=False` por defecto **byte-idéntico** al legacy (cero regresión
  para B..E y para el arnés H1).
- Misma temperatura/presupuesto que B..E · mismo `goal` (`"validar mi agente
  antes de cada release"`) · misma BD · **sin reescritura de prosa** — el
  mapper solo reescribe tokens `[N]`.
- No congelado (post-medida, si PASA): temperatura del write
  (`build_blueprint(temperature=…)`), presentación de la fuente.

## §4 — Disciplina de corrida

- Este plan se commitea **ANTES** de la primera run de P.
- Oficial: `python evals/run_blueprint_ab.py --previas` → solo P, solo las 5
  técnicas con datos en B..E (comparabilidad 1:1; correr las 14 del grafo
  mezclaría poblaciones). Coste estimado: 15 runs × (loop + write) ≈ 80-90
  llamadas.
- `--smoke` (hoy apunta a P): 1 run/técnica para probar el cable; **sus rows
  valen como run 0 oficial** (mismas condiciones, `seen` los cuenta después)
  — declarado aquí para que no se le dé doble uso.
- Riesgos pre-declarados: (a) el modelo ignora R0 y escribe `[doc:…]`
  inventado → lo cobra el criterio 2; (b) índices fantasma (`[5]` con 4
  chunks) → criterio 1; (c) varianza de modelo → 3 runs; (d) el A/B previo
  ya muestra que `cumplimiento_b9` está en 0.000 en todos los brazos — criterio
  4 lo lee como «no empeora», no como «alcanza 1.00».

## §5 — Cierre

(pendiente de la corrida oficial)
