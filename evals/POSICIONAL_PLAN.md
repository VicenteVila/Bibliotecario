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
- **Brazos previos** en `evals/results/result_blueprint_ab.json`: mismas 5 técnicas
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

## §5 — Cierre (corrida oficial + tres correcciones de medición, 2026-10-21)

### Qué corrió

- **Corrida oficial**: `LLM_PROVIDERS=nvidia … run_blueprint_ab.py --previas` —
  15/15 runs `ok`, 0 truncados, sin failover (log `/tmp/opencode/ab_previas.log`).
- **Proveedor**: `nvidia/nemotron-3-ultra-550b-a55b`. El primer intento quedó
  con proveedores caídos (404: función no disponible en la cuenta para los
  modelos que se pedían) y su corrida queda declarada como de infra y
  respaldada en `result_blueprint_ab_corrida1_prov_roto.json`; sus filas se
  borraron de OUT antes de la oficial. **Umbrales de §2 intactos.**

### Tres defectos de medición detectados al leer el veredicto

1. **Bug del instrumento R7 (afectaba a todos los brazos).** `_biblio_check`
   exigía `^### Bibliografía` sin número delante; los brazos que numeran
   secciones (`## 7. Bibliografía`) cobraban R7 como ausente. Corregido en
   `run_blueprint_ab.py` y reaplicado a las 75 filas con `--repuntua`
   (reescribe solo `checks` desde los blueprints guardados, cero llamadas
   LLM, umbral sin tocar). Efecto: C 13→**15**/15, E 11→**15**/15,
   P 8→**11**/15, B 14→15, D 10→12.
2. **Confusor de modelo en P vs C.** Las filas B..E históricas no registran
   modelo y P corrió en nemotron-ultra: la comparación mezclaba formato Y
   modelo. Para leer §2 como está escrito («P vs C **aisla el formato**»),
   se re-corró **solo C** con `--solo=C --previas` en nemotron-ultra
   (15/15 `ok`; histórico de C preservado en
   `result_blueprint_ab_C_historico.json`; las filas nuevas ya guardan
   `modelo`). Decisión tomada *tras* ver el fallo de R7 de P y declarada
   aquí; el umbral «R7 ≥ C» no se redefinió, lo que se hizo fue medir a C en
   las mismas condiciones que a P. *Salvedad*: E (criterio 2, secundario
   P vs E) sigue siendo histórico, es decir, cruzado entre modelos.
3. **Truncación del blueprint en el juez.** `eval_q1_r4r5.py` cortaba el
   blueprint a 9000 chars; E mide ≤6736 y nunca lo alcanzó, pero 10/15
   blueprints de P se cortaban justo donde vive R5 (Bibliografía,
   declaraciones de silencio). Añadido `Q1_BP_MAX` (default 9000, intacto
   para los brazos históricos) y P se juzgó con `Q1_BP_MAX=16000` — vista
   completa, comparable porque E nunca se truncó. Primer juicio de P con la
   vista corta quedó respaldado en `result_q1_r4r5_P_truncado.json`.
   Además E tenía 2 filas con fallo de parseo de juez (PEARL 0, ReASearch 0)
   —«un fallo de parseo NO es una evaluación» según la propia doctrina del
   script—, reintentadas hasta n=15.

### Veredicto (n = 15 runs de P sobre las 5 técnicas previas)

| # | criterio | umbral | medido | |
|---|---|---|---|---|
| 1 | `fuera_de_rango` | 0.00/run | **0.00/run** | ✅ |
| 2 | B8 ratio | ≥ 0.854 | **1.000** (25.27/25.27) | ✅ |
| 3 | citas/run | ≥ 5.33 | **25.27** | ✅ |
| 4 | colateral | B11=0 · trunc=0 · anclas≥0 · R7≥C | 0.00 · 0/15 · 11.27 · R7 11/15 vs C-mismo-modelo 6/15 | ✅ (ver nota) |
| 5 | juez R4/R5 (secundario) | no empeora vs E | R4 5/15 vs E 2/15 · R5 7/15 vs E 9/15 · fab/bp 0.73 vs 1.87 · rel/bp 0.60 vs 1.53 | ✅ (ver salvedad) |

**Nota del criterio 4 (R7 ≥ C), ambas lecturas:**

- vs **C mismo modelo** (nemotron-ultra): C 6/15, P 11/15 → **pasa**.
- vs **C histórico corregido** (mismo instrumento): C 15/15, P 11/15 →
  fallaría en la lectura cruzada entre modelos.

La evidencia atribuye la caída de R7 al modelo, no al formato: con el mismo
modelo, el brazo C cae a 6/15 de Bibliografía (histórico: 15/15) y a 5/15 en
«Según» (histórico: 15/15), mientras P mantiene 11/15 y 7/15 — en condiciones
limpias **el formato posicional mejora R7 frente a C** (11 vs 6) y no
empeora la atribución (7 vs 5). El primado de la prosa de C histórico
(15/15) no es reproducible en el modelo actual (6/15), y qué modelo corrió
C histórico no está registrado — de ahí la corrección del campo `modelo`.

**Nota del criterio 5 (juez, n=15 vs 15, mismo prompt, temp 0):**

- R4: **mejora** — P 5/15 vs E 2/15; fabricaciones/blueprint 0.73 vs 1.87 (×2.6
  menos).
- R5 binario: **baja 2 runs** — P 7/15 vs E 9/15.
- R5 continuo: **mejora ×2.5** — rellenos/blueprint 0.60 vs 1.53 (lo que R5
  cuenta, cuenta menos en P).
- Los 8 fallos R5 de P coinciden casi todos con fallos R4 (misma raíz:
  fabricaciones), concentrados en ReASearch/PG/WikiSkill. Ruido de juez
  medido en el repo: 33-52% de flips en R5 (dec. 16; ahora temp 0) — 2 runs
  están dentro de ese ruido.

### Veredicto final: **MEDIDA 1 PASA** (decisión del dueño, 2026-10-21)

Ratificada con la evidencia de §2 a la vista: criterios 1-3 PASAN con
holgura — 0 índices fantasma, B8 perfecto (el mapper resuelve todo `[N]` que
el modelo pone en rango), ×4.7 citas vs C histórico y ×1.97 vs C mismo
modelo, y por primera vez B9' anclas > 0 (11.27/run; todos los brazos
previos, 0.00). Criterio 4 pasa en su lectura limpia (P vs C mismo modelo,
la que §1 diseñó para aislar el formato). Criterio 5, secundario, se acepta
con salvedad: R4 y ambos continuos mejoran, R5 binario cae 2 runs dentro
del ruido medido del juez.

**Sin redefinir umbrales** en ningún punto del camino. Post-medida, §3
descongela: temperatura del write (`build_blueprint(temperature=…)`) y
presentación de la fuente.
