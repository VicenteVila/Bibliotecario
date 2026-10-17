# Hito 4 — meta-evolución: que el sistema aprenda de sus fallos

**Estado: CERRADO 2026-10-16 — umbrales declarados ANTES de medir y
ratificados por el dueño antes de la corrida; resultado: H5 ✅ · H6 ✅ ·
H7 ✅ · H8 ✅ · C1 ✅ → HITO4 CUMPLE (5/5), ver §6.**

**Objetivo:** cerrar el **hallazgo 4** de `CONOCIMIENTO.md` — la meta-evolución
nunca ha disparado (`skills=0`, `memory_items=0`, `harness_edits=0` y
`evolve_from_failures` sin callers en la ruta productiva). Con el Hito 3
cerrado, las piezas ya existen: los PFs reaccionan a fallo real (H3), el
estado que llega a `apply_pfs` es real (Fase 3) y hay instrumento para
observar corridas (H4). Lo que falta es cablear el ciclo completo:

```
run falla → firma del fallo se cuenta → a la 2ª vez evoluciona →
el PF/skill evolucionado se registra y persiste → una run posterior lo usa
```

---

## 1. Qué se va a cambiar (diseño, no medición)

1. **Tabla `harness_edits`** (nueva en el esquema): memoria durable de las
   firmas de fallo — `signature`, `occurrences`, `evolved`, `pf_name`,
   `intervention`, timestamps. Da hogar real al contador `harness_edits` del
   hallazgo (en este repo no existía tabla; era 0 en ReaGame).
2. **El loop lleva firma de error**: cada sitio de error de `loop.run()`
   registra la firma normalizada del mensaje en `run_errors` (dedupe por run);
   `state_pf` gana `last_error` (estado real, el último mensaje de error —
   se suma a lo que la Fase 3 ya puso en el estado).
3. **`RuntimeHarness.meta_evolve(task, errors)`** — enganchado al final de
   `loop.run()` (en `finally`, tras `finish_run`; un fallo aquí no rompe la
   run y se loguea). Por cada firma: `bump` en `harness_edits`; **K=2 runs**
   (una vez es ruido, dos es patrón) → `evolve_from_failures` crea el
   `auto_pf_N` → skill derivada `auto_skill_N` registrada en la capa
   `ProceduralSkillLayer` **y** persistida en la tabla `skills` → evento
   escrito en `memory_items` (L0). Reclamo condicional por firma para que
   `--workers` no duplique evoluciones.
4. **Rehidratación**: `get_pf_registry()` reconstruye los `auto_pf_*` desde
   `harness_edits` al crearse; `RuntimeHarness.__init__` recarga
   `auto_skill_*` desde la tabla `skills`. La evolución sobrevive a un
   proceso nuevo (antes moría en memoria).
5. **Uso en el loop**: antes de `apply_pfs`, si hay `last_error`,
   `retrieve_skills` aporta el hint `[skill auto_skill_N] …` a la historia
   (una vez por skill y run); el outcome se registra al cerrar (la run
   siguió sin errores tras el hint → éxito).
6. **Fuera de alcance declarado**: `run_blueprint` (dimensión D) no se toca;
   `decompose_complex_task` sigue exigiendo `task.complexity` que el loop no
   conoce; `MT.recall()` sigue sin estar en la ruta productiva (se rellena
   `memory_items` con el evento de evolución, que `background.consolidate`
   ya procesa; la lectura queda como hilo abierto).

## 2. Hipótesis y umbrales — DECLARADOS ANTES DE MEDIR

| id | hipótesis | umbral (intacto, nunca re-bajable) |
|---|---|---|
| **H5** | la evolución dispara en la ruta productiva | `auto_evolved ≥ 1` **y** `harness_edits` con `evolved=1 ≥ 1` |
| **H6** | lo evolucionado se usa (mismo proceso) | `auto_pf_*` aparece en `pf_fires` de al menos una run del lote: `≥ 1` |
| **H7** | los contadores muertos del hallazgo se llenan | `skills ≥ 1` **y** `memory_items ≥ 1` |
| **H8** | durabilidad: sobrevive a proceso nuevo | `auto_pf_*` en `pf_fires` de la run **tras reiniciar registro+harness**: `≥ 1` |
| **C1** | controles (no romper lo existente) | run limpia con registro rehidratado: **0** fires de `auto_pf_*`; suite completa en verde |

Ningún umbral es estadístico: son comprobaciones de existencia sobre runs
**deterministas** (guionizadas, sin LLM). Si alguno no se alcanza, se escribe
"NO CUMPLE" ahí mismo y no se re-baja.

## 3. Diseño de medición — `evals/run_hito4_meta.py`

- **0 tokens**: misma técnica que H3 enmienda y los tests del loop — LLM
  guionizado, harness/PFs/estado reales. DB **hermética** (temporal, `init_db`
  propio): no contamina ni hereda `data/bibliotecario.db`.
- Guion de error: tool inexistente → tool válida → cierre. Firma idéntica
  entre runs (el mensaje no depende de la pregunta).
- Lote de 5 runs, cada una observando un eslabón:

| run | condición | qué observa |
|---|---|---|
| R1 | error, registro limpio | firma contada (`occurrences=1`), **sin** evolucionar aún |
| R2 | error, mismo proceso | **evoluciona**: H5 + H7 (skills, memoria) |
| R3 | error, mismo proceso (sin reinicio) | **uso**: `auto_pf_1` en `pf_fires` → H6 |
| R4 | error, **con** registro+harness reiniciados | rehidratación: `auto_pf_1` vuelve a disparar → H8 |
| R5 | **limpia**, con registro rehidrata | **0** `auto_pf_*` → C1 |

- Tras el lote: tests completos en verde (C1) y lectura directa de contadores
  (`harness_edits`, `skills`, `memory_items`, `pfs.stats()`).

**Coste declarado esperado: 0 tokens LLM** (solo runs guionizadas locales).

## 4. Reglas de disciplina (las del proyecto)

- Umbrales anteriores a la medición; no se re-bajan; resultado se publica
  tal cual (Hito 3 cerró con 2 de 4 NO CUMPLE y así queda).
- Cualquier desviación entre diseño y script se declara errata con fecha
  antes de dar el resultado por bueno; el histórico no se reescribe.
- **Interacción declarada**: las corridas de evaluación existentes usan
  `data/bibliotecario.db`; si la evolución persiste ahí, las evals futuras
  heredan los `auto_pf_*` (una eval comparable necesita DB hermética). Es
  comportamiento del producto, no un bug; queda anotado aquí antes de medir.

## 5. Cómo se sabrá que cierra

Tabla *criterio / umbral / medido* en §6 tras la corrida, erratas propias
numeradas y coste real — la misma estructura que HITO0-HITO3. Cierre del hito
como sección propia con los veredictos H5-H8+C1 y qué hilos quedan abiertos.

---

## 6. Resultado — 2026-10-16 — **HITO4: CUMPLE (5/5)**

Corrida oficial `evals/run_hito4_meta.py` → `evals/result_hito4_meta.json`
(DB hermética, 5 runs guionizadas, **0 tokens**), tras la ratificación del
dueño de §2. Umbrales intactos: ninguno se tocó.

| criterio | umbral (ratificado) | medido | veredicto |
|---|---|---|---|
| **H5** la evolución dispara | `auto_evolved ≥1` y `harness_edits evolved ≥1` | 1 y 1 | **CUMPLE** |
| **H6** lo evolucionado se usa (mismo proceso) | `auto_pf_*` en `pf_fires` de R3 ≥1 | `auto_pf_1` presente | **CUMPLE** |
| **H7** contadores muertos del hallazgo | `skills ≥1` y `memory_items ≥1` | 1 y 1 | **CUMPLE** |
| **H8** durabilidad tras reinicio | `auto_pf_*` en `pf_fires` de R4 ≥1 | `auto_pf_1` rehidratado | **CUMPLE** |
| **C1** controles | run limpia R5 con 0 `auto_pf_*`; suite en verde | 0 fires; **281 passed** | **CUMPLE** |

Observaciones de la corrida (tal cual salieron, sin filtrar):

- **R1** (1ª firma): 0 evoluciones — K=2 respeta «una vez es ruido». Los PFs
  built-in (`retry`+`fallback`) ya disparan como en H3: es el comportamiento
  previo, no cuenta para los umbrales.
- **R2** (2ª firma): evento `{pf: auto_pf_1, skill: auto_skill_1, x2}` — una
  sola evolución por firma; la tercera y cuarta aparición (R3, R4) no la
  repiten (`occurrences` llega a 4 en la fila, `evolved` sigue en 1).
- **R3**: `auto_pf_1` en los fires **y** la skill `auto_skill_1` recibe su
  hint en la historia y registra outcome de recuperación (1/1, `success_rate=1.0`).
- **R4**: registro y harness reiniciados — `auto_pf_1` reconstruido desde
  `harness_edits` (contador restaurado, sin reutilizar nombres) y la capa de
  skills recargada desde la tabla: vuelve a disparar.
- **R5**: limpia con el registro rehidratado — 0 fires de `auto_pf_*` (y 0 en
  total): lo evolucionado no dispara sin fallo.

**Erratas:** ninguna de medición. Nota de implementación pre-medición (los
tests la cazaron antes de la corrida oficial): el primer `bump` insertaba la
firma con `occurrences=0` — corregido a 1 en el mismo día y antes de medir;
también se confirmó que el mensaje real de este guion sale de la rama *toolish*
(`parse_tool_call` rechaza tools desconocidas antes de llegar a validación),
así que la firma del experimento se deriva del mensaje exacto y no de una
constante a mano.

**Coste real:** 0 tokens LLM; 5 runs locales; 281 tests en verde (los 3
nuevos cubren la cadena R1-R5 como regresión).

**Qué queda fuera / hilos abiertos tras este cierre:** `MT.recall()` sigue sin
estar en la ruta productiva (el evento de evolución se escribe en
`memory_items` y lo procesa `background.consolidate`, pero la lectura no está
cableada); `run_blueprint` (dimensión D) no lleva meta-evolución propia; las
evals que corran sobre `data/bibliotecario.db` heredarán los `auto_pf_*`
persistidos (la práctica declarada es DB hermética para evals comparables);
`decompose_complex_task` sigue exigiendo `task.complexity` que el loop no
conoce (regla intacta de no inventar complejidad). Del listado del cierre del
Hito 3 siguen abiertos: verificación de atribución (H1/hallazgo 26), potencia
del A/B (H4/hallazgo 27) y juez ciego (hallazgo 10).

