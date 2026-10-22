# HITO 19 — PLAN (declaración v2): piloto de `Sens(x)` con arnés mínimo en `software_development`

> **DECLARADO 2026-10-22 (v2) — RATIFICADO por el dueño 2026-10-22: §1 y §2
> ☑ (el dueño pidió dificultad alta: «necesito buenos agentes»).**
> En el momento de la ratificación: **código 0, corridas 0**. La v1 (`da46830`) declaraba un
> `H_aux` de *knobs* de generación de juegos; se retira **sin código ni
> corridas** tras la corrección del dueño: un **arnés** es la capa de 6/7
> subsistemas que envuelve al LLM para hacerlo agente (doc 6 y doc 12 del
> corpus), no la configuración de una llamada. No hubo medición en v1, no
> hay resultados que preservar. §5 (cierre) se escribe al terminar.

## §0 — Estado y por qué este hito, y por qué este diseño

**Bloqueante.** `Sens(x)` (§10.1-§10.2.1 del spec) es lo que separa un split
`D^val`/`D^eval` riguroso de uno con apariencia de riguroso, y exige `H_aux` =
K arneses de calidad distinta que **no existe** (bloqueante nº 22). Con B-1 y
B-2 ya válidos (H15-H18), este es el siguiente jalón del benchmark.

**Qué es un arnés (la corrección que rehace este plan).** Doc 6 (survey, ec. 2):
`H = ⟨Iobs, C, L, Iact, S, V⟩` — interfaz de observación · gestor de contexto ·
bucle de control · interfaz de acción · almacén de estado · verificación y
gobernanza. Doc 12 (anatomía de 11 sistemas): subsistemas `D1` bucle · `D2`
integración LLM · `D3` herramientas/acción · `D4` memoria/contexto · `D5`
seguridad/permisos · `D6` orquestación · `D7` extensibilidad. Un arnés **no** es
un framework, **no** es un evaluation harness, **no** es un orquestador.

**Por qué `software_development` (dominio inexplorado — decisión del dueño).**
- **No hay arnés allí** → construimos un mínimo y controlamos los tres pisos
  del coste: modelo (Nemotron barato), subsistemas (los toggles son nuestros),
  score (tests = determinista, 0 tokens).
- **Verificador casi gratis**: `m_h(x)` = tests ocultos que pasan — mismo
  espíritu que B-1 (pruebas de comportamiento), sin juez.
- Es dominio de **generación** → representativo del objetivo Capa B.
- Reglas de dominio ya escritas para autorar tareas realistas:
  `/mnt/c/Cogniteam/cogniteam_rules/2_software_development/`.
- Evita los dos riesgos **estructurales** de ReaWeb (cuota ajena pausada;
  A/B de subsistemas nulo, p=0.25) y el de juegos (scorer listo pero **sin
  arnés**): la v1 de este plan cayó justo ahí.

**Por qué modelo fijo Nemotron.** En `Sens(x)` el modelo es **variable de
control**: los K arneses difieren en subsistemas, no en modelo (si no, mediríos
calidad de modelo, no de arnés). `NVIDIA_API_KEY` + endpoint + failover ya
cableados (`core/llm.py:220,243`), y `LLM_PROVIDERS` fija proveedor para que la
eval no se mezcle (`llm.py:233-235`). Candidato: `nemotron-3-super-120b-a12b`
(probado: *«sostiene los prompts largos»*, `config.py:42`).

**Petición explícita del dueño: dificultad alta — «necesito buenos agentes».**
Codificada en dos sitios: (a) reglas de construcción de tareas (§1.3) y (b)
gate **U7 de dificultad** (§2), medible y con umbral. Encaja con `Sens(x)`: solo
las tareas difíciles separan arneses; las fáciles empardan y dejan `Sens`
indefinido.

**Alcance honesto.** Es un **piloto**: prueba que `Sens(x)` es calculable y que
≥ la mitad de las tareas discrimina calidad de arnés. **NO dibuja el split** de
ningún benchmark. Puede cerrar **NO CUMPLE** (resultado negativo válido; los
umbrales no se tocan tras medir).

## §1 — Diseño propuesto — ☑ RATIFICADO 2026-10-22

### 1.1 Dominio y arnés mínimo
- Dominio: **`software_development`**. Paquete nuevo `evals/sd_pilot/`
  (rutas exactas se fijan en §1.B al implementar).
- Arnés mínimo (no existe aún): bucle *observe-reason-act* con herramientas
  `read_file`, `write_file`, `run_tests` (pytest headless), presupuesto
  **max_turns = 16**. Sin orquestación (`D6` = ausencia deliberada, doc 12).
- Los subsistemas se implementan **reutilizando** `bibliotecario/harness/`
  (`SkillProgramRegistry` + PFs `Retry`/`ValidateBeforeAct`,
  `TrajectoryRegulationLayer`) — **sin modificar** esos módulos.

### 1.2 `H_aux` — K = 5 variantes (matriz congelada en §1.B)

| var. | D1 bucle | D3 tools | D4 memoria | D5 validación | D7 skills |
|---|---|---|---|---|---|
| **A1** | 1 sola llamada (one-shot) | — | — | — | — |
| **A2** | bucle ≤16 turnos | sí | — | — | — |
| **A3** | bucle | sí | — | PFs validación+retry | — |
| **A4** | bucle | sí | — | PFs | pack de skills congelado |
| **A5** | bucle + regulación trayectoria | sí | errores intra-run | PFs | pack congelado |

A1 es el extremo inferior deliberado (garantiza `spread`); A5 el superior. El
orden `A1 < … < A5` es **intención de diseño, no supuesto**: `Q_h` sale de los
datos. Modelo **fijo** en las cinco.

### 1.3 Tareas — N = 12, **difíciles** (requisito del dueño)
- Cada tarea: workspace con código existente (3-8 ficheros) + requisito
  (feature/bugfix) + **tests públicos** (el agente puede correrlos) +
  **tests ocultos** del verificador.
- **Reglas de dureza** (toda tarea exige ≥ 2): integración multi-fichero ·
  caso límite algorítmico en tests ocultos · lectura de la arquitectura
  existente · recuperación de error a partir de la salida de una herramienta ·
  contrato de API estricto. **Anti-trivialidad**: ninguna tarea se resuelve de
  una sola llamada sin leer ni ejecutar nada.
- Selección de las 12: regla determinista fijada en §1.B **antes** de la
  corrida oficial.
- **Independencia de celdas** (clave de la fórmula): cada celda = workspace
  copiado fresco + estado de arnés fresco + mismo pack de skills congelado →
  **cero aprendizaje cruzado entre tareas**, o `Q_h^(−x)` dejaría de ser
  leave-one-out.

### 1.4 `m_h(x)` y `Sens(x)`
- `m_h(x)` = % de tests ocultos que pasan (pytest headless; determinista;
  0 tokens de juez).
- `Q_h^(−x)` = media de `m_h(·)` de `h` sobre las otras 11 tareas.
  `Sens(x)` = correlación de Pearson de las 5 parejas `(m_h(x), Q_h^(−x))`.
  Varianza nula → **no definible** (se reporta como tal, nunca como 0).

### 1.5 Modelo — fijo, con escalada solo por regla pre-declarada
- Default: **`nvidia/nemotron-3-super-120b-a12b`** (`LLM_PROVIDERS=nvidia`).
- Escalada en G0: si en las tareas de humo **A5 saca 0 global** (suelo) →
  `nvidia/nemotron-3-ultra-550b-a55b`; si aún 0 → **G0 falla**, decisión del
  dueño. El ultra **no** se usa por defecto (coste).

### 1.6 TraceForge — traza del flujo por subsistemas (obligatorio, §5.4)
- Instalación en el venv del proyecto + dependencia en `pyproject.toml`
  (`pip install -e /mnt/c/TraceForge`; repo hermano en solo lectura) — queda
  cubierta por la ratificación de §1.
- **Esquema de traza (se congela al ratificar, §5.4)**: span raíz `sens_pilot`
  con metadata `{variant, task, model, run_id, subsystems_flags}`; hijos
  `turn.N` (input = contexto renderizado que vio el modelo, output = crudo),
  `llm` (tokens/coste), `tool.<nombre>` (args, resultado).
- Para qué: ver **por qué** una variante puntúa distinta de otra a nivel de
  subsistema — la evidencia que hace creíble `Sens(x)`.

### 1.7 G0 — humo con reglas de decisión declaradas ANTES de correr
- Protocolo: 2 tareas difíciles × extremos A1/A5 × modelo elegido → confirma
  coste/celda, ventana piso-techo y traza operativa.
- Reglas pre-declaradas (se aplican sin retoque tras ver datos):
  `A5 > A1` → seguir · `A5 = 0` → escalar modelo (§1.5) · `A1 = A5 = 100` →
  la tarea es fácil: se endurece **en construcción** (iteración de BUILD
  permitida y documentada, previa a la corrida oficial) · coste proyectado
  excede 3M tokens → `N = 8`; aún excede → **no arranca**, decisión del dueño.
- Resultados de G0 se documentan (log + §5). Nada se esconde.

### 1.8 Presupuesto
- Corrida oficial: K×N = 60 runs × ≤16 turnos, **techo 3M tokens**; reducción
  a `N = 8` solo vía la regla G0 de §1.7 (nunca tras medir).

## §2 — Umbrales (RATIFICADOS 2026-10-22)

| gate | umbral | por qué | estado |
|---|---|---|---|
| **G0** humo | ventana `A5 > A1` en las 2 tareas · coste en techo · traza operativa · reglas §1.7 aplicadas y documentadas | sin ventana no hay `Sens`; sin coste no hay corrida | ☑ |
| **U1** `H_aux` | K = 5 variantes congeladas (matriz §1.2 + modelo fijo + `max_turns=16`) | sin `H_aux` no hay `Sens` | ☑ |
| **U2** matriz | 60 celdas, **0 huecos**, `m_h(x)` float determinista | `Sens` exige score por tarea | ☑ |
| **U3** separación | `spread Q_h ≥ 15` puntos | si los arneses no difieren, Pearson es ruido | ☑ |
| **U4** `Sens` finito | finito en ≥ 6/12 tareas (no-definibles se marcan, no cuentan como 0) | Pearson exige varianza | ☑ |
| **U5** discrimina | ≥ 6/12 tareas con `Sens(x) > 0` | si ninguna discrimina → **NO CUMPLE con evidencia** | ☑ |
| **U6** disciplina | umbrales y tamaño **antes** de medir · ruff + pytest · corrida oficial única · sin retoques tras medir · intentos fallidos documentados con causa y coste | `AGENTS.md` | ☑ |
| **U7** **dificultad** (req. del dueño) | media global de celdas **≤ 60** · media de A5 **≤ 80** (sin techo) · **≥ 8/12** tareas con `A5 < 100` (ni el mejor las tiene fáciles) | «necesito buenos agentes»: tareas que exigen agente bueno, medidas | ☑ |

### §1.B — Congelación de implementación (fijada al ratificar/ implementar)

**Rutas** (paquete nuevo, todo bajo `evals/sd_pilot/`):
`harness.py` (bucle mínimo + herramientas) · `variants.py` (A1-A5) ·
`verifier.py` (pytest público/oculto) · `sens.py` (matriz, `Q_h^(−x)`, Pearson,
gates) · `tasks.py` (specs e ids) · `skills_pack/` (skills congelados) ·
`sd_tasks/<id>/` (12 tareas) · `run_pilot.py` (modos `--g0` y `--oficial`) ·
`traces.sqlite` (TraceForge). Evidencia: `evals/results/result_sens_sd_pilot.json`
+ `evals/logs/sens_sd_pilot_run.log` (G0: `evals/logs/sens_sd_g0.log`).
Tests: `tests/test_sens_sd_pilot.py`.

**Variantes (parámetros exactos)** — modelo `nvidia/nemotron-3-super-120b-a12b`,
`LLM_PROVIDERS=nvidia`, `temperature` = 0.2 (default de backend, sin override):
- **A1** one-shot: 1 llamada, workspace completo en el prompt, salida en
  bloques `###FILE: path ###` (convención de `measure_b1.py`), `max_tokens=8192`.
  Sin herramientas, sin iteración.
- **A2** bucle ≤16 turnos, tools `read_file`/`write_file`/`run_tests` (pytest
  públicos), `max_tokens=4096`, historial crudo.
- **A3** = A2 + PFs reutilizados (`SkillProgramRegistry` con
  `ValidateBeforeActPF`/`RetryPF` sobre estado `{last_action.status,
  error_count, attempt_count}`); sus mensajes entran al historial.
- **A4** = A3 + `skills_pack/` (4 skills congelados, idénticos en todas las
  celdas A4/A5: leer-antes-de-escribir · iterar-con-tests-públicos ·
  contratos-estrictos · casos-límite).
- **A5** = A4 + `TrajectoryRegulationLayer` (estancamiento/reintentos/
  presupuesto → mensajes correctivos) + digest estructurado de los últimos 5
  errores siempre en contexto.

**Las 12 tareas** (ids congelados; selección = estas 12, regla fija):
`checkout-rounding` · `repo-cache-layer` · `dsl-parser` · `interval-scheduler` ·
`seeded-bugs-billing` · `cli-subcommand` · `workflow-statemachine` ·
`batch-coalescer` · `schema-validator` · `plugin-registry` · `csv-diff-engine` ·
`config-migration`. Cada una: `TASK.md` + `workspace/` (3-8 ficheros +
`tests_public/`) + `tests_hidden/` + `reference/` (solo QA de BUILD).
Ejes de dureza (≥2 por tarea, exigido por lint): multi-fichero · límites
ocultos · arquitectura · recuperación · contrato estricto.
QA de BUILD por tarea (obligatorio, documentado): `reference` aplicada →
**100% ocultos**; workspace vacío → **≥1 fallo público** y **<100% ocultos**.
`run_tests` solo ve públicos; los ocultos viven fuera del workspace (el
verificador los copia a un dir limpio — supuesto no-adversarial declarado).

**G0**: tareas `checkout-rounding` + `dsl-parser` × {A1, A5}. Reglas §1.7.

**Esquema de traza (congelado, §5.4)**: collector `sqlite` en
`evals/sd_pilot/traces.sqlite`; span raíz `agent="sens_pilot"` con
metadata `{variant, task, model, run_id, max_turns, subsystems}`; hijos
`agent="turn"` (metadata `{turn}`; input = contexto renderizado, output =
respuesta cruda), `agent="llm"` (tokens/coste), `agent="tool"` (metadata
`{tool_name}`; input = args, output = resultado truncado).
`set_metadata_context(variant, task, run_id)` por celda.

**CUMPLE** = G0 + U1-U7 todos OK → `Sens(x)` calculable y ≥50% de tareas
discriminan, con tareas duras. **NO CUMPLE** = cualquier gate cae → evidencia +
decisión del dueño; umbrales y `Sens` no se tocan.

## §3 — Congelados y no congelados
- **Congelados hasta enmienda declarada**: fórmula `Sens(x)` (Evo-Bench §4.2) ·
  esquema de traza (§5.4: se congela al ratificar) · composición del `H_aux`
  (K=5, matriz §1.2) · N=12 (bajar a 8 solo vía regla G0) · tests ocultos una
  vez cerrada su construcción (§1.B) · modelo fijo (salvo escalada §1.5) ·
  umbral de U7.
- **Congelados heredados (intocados)**: `bibliotecario/harness/*` (solo
  lectura/uso) · corpus (`CORPUS_LOCK.json`) · B-1/B-2 de juegos · evidencias
  previas.
- **No congelado**: diseño interno de tareas y arnés hasta §1.B; iteración de
  BUILD (tareas/arness) documentada hasta la corrida oficial; rutas exactas.

## §4 — Disciplina (sin medir hasta ratificar)
1. Este plan v2 se commitea **como declaración**: código 0, corridas 0.
2. **Ratificación del dueño** de §1 y §2 (☐→☑) — con ella se autorizan: crear
   `evals/sd_pilot/`, instalar TraceForge en el venv y añadir la dependencia.
3. Solo entonces: §1.B fija tareas/variantes/rutas/esquema → implementación +
   tests puros (matriz `m_h`, `Q_h^(−x)`, Pearson, casos borde, fake harness
   sin LLM) + ruff + pytest + fila §11 y esquema de traza en el spec →
   **G0 documentado** → ajustes solo por reglas §1.7 → **corrida oficial
   única** → §5 con veredicto por gate.
4. Commits en español ASCII sin acentos; clave-scan en cada commit.
5. Si un gate falla → **NO CUMPLE con evidencia y decisión del dueño**; nada
   se re-baja tras medir; todo intento fallido se documenta con causa y coste.

§5 (cierre) se escribe al cerrar; mientras tanto no existe. Referencias de
estado previo: `evals/results/result_fase2_b2_h18.json` (H18 CUMPLE) y la
corrección de concepto de arnés (docs 6 y 12 del corpus).
