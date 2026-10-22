# HITO 13 — Cierre de H1 · Enmienda 2 «fuente completa» + intento 9 (brazo `H20`)

Declaración escrita ANTES de implementar y ANTES de medir (2026-10-17).
Ratificación obligatoria del dueño antes de la corrida oficial (§1 toca el
fichero del instrumento y §1.D fija la recalibración E13). Patrón por
intento: plan SOLO → implementación + tests + suite verde + ruff →
ratificación → corrida oficial única → §5 + hallazgo 26/10 + clave-scan +
commit+push.

## §0 Evidencia que declara este intento

- **Hito 12 / enmienda 1**: ventana rica (chunk0+citados+top-10 híbrido)
  → **RECHAZADA 0/4 en E12**; forense: las 4 quejas nuevas son **falsas**
  contra la fuente completa (PEARL «converges faster» 2×, TCE `0.125`/`0.025`
  exactos + Table D/E, Wiki `gating`16×/`rbest`10×/`qwen`98×, PG
  `mutation`11×). Recuperación NO sirve para verificar R4/R5.
- **Hallazgo 10 en su forma final**: los veredictos R4/R5 son **función de
  la ventana** y **ninguna ventana corta probada es estable** — tiny
  (0,86%-10,4%): 4/5 estables pero ReASearch inverificable y cola
  bottomless; recuperada (~7-13%): 0/4 con falsos positivos.
- **La única ventana no probada que resuelve ambos extremos es la fuente
  COMPLETA** (63.012-138.642 chars normalizados por técnica): con ella los
  4 obligatorios tienen sus términos verificables (forense §5 de H12) y
  ReASearch queda juzgado contra los 139K donde `pre-release` vive 0 veces
  (quejas verdaderas) y `re-emission` 1× (falsas detectables) → cola
  **finita y real**.

## §1 Enmienda 2 (toca `evals/eval_q1_r4r5.py` — declarado)

- **A — Cap de fuente en `q1`**: `source[:9000]` → `source[:FUENTE_MAX]`
  con `FUENTE_MAX = 160_000` (constante nueva en el propio fichero).
  **`PROMPT` byte-idéntico; `blueprint[:9000]` intacto** (bp máximo actual
  7399); modelo, temp 0 y env intactos. Nota de comparabilidad: cualquier
  re-ejecución histórica de `eval_q1_r4r5.py` quedaría bajo el cap nuevo
  (no se re-ejecuta; filas `H1`…`H18` y `E12` quedan históricas; solo
  `E13` y `H20` corren bajo enmienda 2).
- **B — `fuente_completa(tech)`** (nueva en `bibliotecario/agent/tools.py`):
  todos los chunks del documento propio con su cabecera `[chunk i]`, sin
  recorte (el cap vive en `q1`). El runner vuelve a cachear la fuente
  **por técnica** (la fuente completa no depende del blueprint; la ventana
  por-bp de la enmienda 1 queda en desuso para el juicio).
- **C — Presupuesto de tokens declarado**: fuentes 85K/127K/139K/63K/99K
  chars ≈ 19-40K tokens por llamada; E13 ≈ 160K tokens de entrada y la
  corrida ≤700K (riesgo 429/cuota declarado en §2).
- **D — Recalibración OBLIGATORIA `E13` (fase 0, antes que filas H20)**:
  los mismos 4 estados aprobados H18 (PEARL r0 · PG r0 · TCE r0 · Wiki r0)
  + diagnóstico ReASearch r0, juzgados con fuente completa. Juicios
  `arm="E13"` (idempotente). **Si alguno de los 4 deja de aprobar, la
  enmienda 2 se RECHAZA y el runner aborta antes de H20.**

## §2 Umbrales, coste y riesgos (a ratificar)

- Umbrales idénticos a HITO7-§11 §2: **H5' 5/5 · G1 5/5 · G2 5/5 · C1'**
  (suite ≥334 + ≥50% base + ningún `ok=False`); **global = los cuatro**.
  Instrumento: `eval_q1_r4r5.py` con el único cambio del cap §1.A; M4,
  V1/V2, causas declaradas, idempotencia intacta; filas `H1`…`H18` y
  juicios `E12` intocables.
- Coste en llamadas: **≤25 juicios** (E13: 5 + corrida ≤20) **+ ≤32
  localizadores**; coste en tokens declarado en §1.C.
- **Riesgos pre-declarados**:
  1. **E13 falla** (alguno de los 4 cae con fuente completa) → enmienda 2
     rechazada, abort sin filas H20, decisión del dueño (forense de las
     quejas para ver si son verdaderas).
  2. **Cuota/latencia** con entradas de 19-40K tokens: 429 manejados por
     reintentos (§8.12); techo diario posible → re-ejecución idempotente.
  3. **ReASearch con fuente completa**: cola finita esperada pero no
     garantizada en ≤10 rondas → NO CUMPLE con evidencia (riesgo (b)
     clásico, ahora medido sobre 139K).
  4. **Foco del modelo con entradas largas** (juicios peores) → medido por
     E13 en los 4; si E13 aprueba, el instrumento queda validado.
  5. **Truncación**: ninguna fuente supera 160K (máx. 138.667) → sin
     truncación; el bp ya entra entero (máx. 7399).

## §3 Runner

- `evals/run_fase1_h20.py` (copia de h19): `ARM = "H20"`, `E_ARM = "E13"`,
  OUT `result_fase1_h20.json`, `MAX_ROUNDS = 10`, `MAX_LOC = 32`, textos
  Hito 13 / enmienda 2 / intento 9 / HITO13 §2-§3. Cadena de base (H18 a
  la cabeza), M4, M1+M5 span, causas e idempotencia iguales a H18-H19;
  cambios: `_calibracion` con filas H18 bajo fuente completa (E13) y
  juicio con `fuente_completa(tech)` cacheada por técnica.
- Filas: `evals/results/result_fase1_h20.json` + juicios `arm="H20"` (y `E13`).
  El brazo declarado `H19` (Hito 12) quedó sin filas por el abort de E12 y
  **no se reutiliza**.

## §4 Disciplina

1. Este plan SOLO commiteado antes que el código.
2. Implementación + tests (`fuente_completa`: doc_id, orden de chunks,
   cabeceras, sin recorte; cap FUENTE_MAX; E13 abort) + suite ≥335 +
   ruff + abort sin env.
3. Ratificación del dueño (§1 enmienda + §2).
4. Corrida oficial única (E13 → H20).
5. NO CUMPLE / rechazo se cierran igual; el siguiente paso exigiría
   declaración nueva.

## §5 Cierre — 2026-10-17 · ENMIENDA 2 RECHAZADA POR LA PUERTA 4/4 (intento 9 no corrió)

- **Resultado E13 (fuente completa)**: **PEARL OK · TCE OK · WikiSkill OK**
  (los 3 restaurados — confirman el forense de E12: sus quejas de la
  ventana rica eran falsas) · **PG R4+R5 FALLA** · ReASearch (diag) R4+R5
  FALLA → **3/4 → §1.D: ENMIENDA 2 RECHAZADA, abort antes de H20** —
  0 filas `H20`, 0 localizadores, coste **5 juicios**. Riesgo (1).
- **Forense de la única caída (PG, fuente completa de 131.899 chars)**:
  1. `lessons persistence` → **`lesson` 0× y `persist` 0×** → queja
     **VERDADERA**: la aprobación de PG en H17/H18 (ventana 0,9%) era un
     **artefacto** — PG nunca aprobó a un juez que pudiera ver su fuente.
  2. `failure-vs-success refiner` → **`refiner` 23×, `success` 44×**
     («offline LLM refiner inspects the partitioned traces» /
     «successes versus failures») → queja **FALSA**.
  3. `graph mutation` → **`mutation` 11×** («Feedback-Driven Mutation»,
     «mutation engine … deleted the mismatched transition edges») → queja
     **FALSA** (equivalencia semántica con otro nombre).
  4. R5 extracción de trayectorias → `trajector` 90× sin algoritmo de
     extracción explícito → **parcialmente verdadera**.
  → **Incluso con la fuente COMPLETA el juez erra por nombre-exacto**
  (hallazgo 10: la ventana no era el único problema; el criterio R4
  confunde «no con ese nombre» con «no existe»).
- **ReASearch con fuente completa: cola corta y verdadera** — E13 lista
  **1 R4 + 1 R5** (contra 2-3 por ronda durante 11 rondas en ventana
  tiny): `refiner` 0× y `pre-release` 0× en 139K → ambas **verdaderas**;
  los moles anteriores (stagnation advisory, search-tree, etc.) existen en
  la fuente y el juez ya no los acusa. **La cola es finita y de 1-2
  reparaciones.**
- **Estado del arte al cierre**: bajo fuente completa, **3/5 tienen
  aprobación verdadera** (PEARL/TCE/Wiki) · **PG** = 1-2 quejas verdaderas
  + 2 falsas encadenables · **ReASearch** = 1-2 quejas verdaderas. La
  puerta 4/4 bloqueó por PG, cuya aprobación previa era ella misma un
  artefacto. Opciones al dueño: **A** declarar intento 9 con puerta
  re-declarada (≥3/4 + forense) y meter PG+ReASearch al bucle de
  reparación — primera vez con colas finitas a la vista · **B** cerrar H1
  con toda la evidencia · **C** enmienda 3 (tolerancia semántica en el
  prompt — rompe PROMPT intacto).
