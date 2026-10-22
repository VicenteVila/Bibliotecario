# HITO 6 — Declaración: H1 intento 3 (brazo `H13`), «reparación que no degenere»

2026-10-17 · escrito ANTES de implementar y ANTES de medir.
Patrón idéntico a HITO3/HITO4/HITO5: este archivo se commitea solo, luego la
implementación + tests, luego la ratificación del dueño de §2, luego la
corrida oficial. Los umbrales se fijan aquí: no se re-bajan después de medir.

## §0 Por qué — diagnóstico del intento 2 (HITO5, cerrado NO CUMPLE)

- **H5 se logró: 5/5 R4+R5** (H1 nació en 1/5). El bucle juez → reparación
  con evidencia completa funciona para la rúbrica; 17 llamadas de coste real.
- **Las guardas tumbaron el cierre**: G1 4/5 (ReASearch 2→0 resueltas),
  G2 2/5 (PEARL y ReASearch pierden `## Bibliografía`; WikiSkill renombra `##`,
  estricto: renombrar = falla).
- **Causa de fondo**: la reparación LLM solo se validaba por «no vacío, no
  «(»». PG quedó en 488 chars (base 3988) y ReASearch en 440 (borrador de
  razonamiento del propio modelo, base 5196) y **el juez los aprobó**
  R4=OK R5=OK. El juez detecta fabricación, no integridad — esto refuerza el
  hallazgo 10 y queda fuera de este hilo: **el instrumento va congelado**.
- Modo B empeoró: al final 0/5 arneses con punteros resueltos (fuera de
  alcance aquí, estatus quo declarado otra vez).

## §1 Mecanismo (los tres arreglos, declarados)

**A) Reparación mecánica determinista previa, 0 tokens** (`mech_repair`):

1. `normalize_pointers` (§7.1): solo corchetes mal formados, nunca prosa.
2. `check_attributions` + `demote_unsupported`: puntero a chunk inexistente
   se quita; término ausente se marca «(propuesta del blueprint)». La prosa
   queda palabra por palabra — §5.8.3 gobierna: P3 regeneró y destruyó en 3/3,
   aquí jamás se regenera por camino determinista.
3. `check_orphan_claims`: cada huérfana recibe la marca R6 al final de su
   propia línea (edición de línea, no de frase).

Toca el texto SOLO por edición de cadena; las estadísticas se registran en la
fila. Si el mecánico ya arregló todo, la reparación LLM igualmente se pide
(como en HITO5) pero parte de ese texto y debe preservarlo.

**B) Validación de salida de cada reparación LLM (nueva, obligatoria):**

- **V1 longitud**: salida no vacía, no «(», y **≥ 50% de la longitud de la
  base** (mismo texto base de HITO5). Caza el caso 488/440.
- **V2 estructura**: `encabezados(base) ⊆ encabezados(salida)` — misma
  definición literal que G2 (`^##\s+`), renombrar = falla.
- **V3 resolución**: `citas_resueltas(salida) ≥ citas_resueltas(base)` —
  G1 aplicado dentro del bucle.

Protocolo de rechazo: **1 reinterto** con el listado concreto de fallos en el
prompt; **2.º rechazo = arnés fallo** (causa registrada; el texto rechazado
no se juzga, no toca disco ni escribe BLUEPRINT.md). Vacío o «(» sigue siendo
error de infraestructura (aborta y se re-ejecuta), criterio intacto de HITO5.
V1 es un **endurecimiento de C1**, declarado como tal: no relaja nada.

**C) Guardas en el bucle**: V2 y V3 son G1 y G2 aplicadas a cada borrador
aceptado; el resumen final repite las mismas G1/G2 de HITO5 contra la misma
base — directamente comparables con 4/5 y 2/5 del intento 2.

## §2 Umbrales (a ratificar antes de la corrida)

| criterio | umbral | base de comparación |
|---|---|---|
| H5' r4_ok y r5_ok por arnés | 5/5 | último juicio `H13` |
| G1 resueltas finales >= base | 5/5 | filas H1R/H1 (igual que HITO5) |
| G2 encabezados base incluidos | 5/5 | ídem |
| C1' | suite verde + cada final >= 50% de su base + no vacíos + no «(» | |
| **Global** | **H5' y G1 y G2 y C1'** | |

- Juez congelado: `gemini-3.1-flash-lite` @ Google vía endpoint OpenAI, temp
  0, prompt `eval_q1_r4r5` intacto, env obligatoria (misma que el dueño
  confirmó en HITO5).
- HITO3/HITO4/HITO5 y el historial quedan intactos: esta corrida solo AÑADE
  filas `arm="H13"`. Nada se re-mide, nada se re-baja.
- Base de G1/G2/V1: `_base()` idéntica al de HITO5 (fila `H1R` si existe, si
  no `H1`) — el mismo estado pre-intento-2, no los finales dañados de H12.

## §3 Runner

`evals/run_fase1_h13.py` → `evals/results/result_fase1_h13.json` (filas `H13`) y
juicios `arm="H13", run=ronda` en `evals/results/result_q1_r4r5.json` (H1, H1R, H12
sin tocar).

- **Ronda 0**: juicio fresco de la base H1R/H1 con el mismo instrumento —
  5 juicios nuevos, no se reutiliza ninguna fila de H12.
- Reparación (si suspende): mecánico A + LLM validado B (≤ 2 intentos de
  generate por ronda).
- Máximo **3 rondas** de reparación; tres fallos seguidos = arnés fallo
  (no hay ronda 4).
- Coste declarado: **≤ 20 juicios + ≤ 30 generate() = ≤ 50 llamadas**.
- Idempotente (retoma por el último juicio/fila válida); BLUEPRINT.md solo
  se escribe con borradores aceptados por V1-V3.
- Apertura obligatoria con la env del juez (aborta sin ella, como HITO5).

## §4 Disciplina

1. Commit de ESTE archivo solo, antes de escribir código.
2. Implementación + tests (suite completa verde) + ruff.
3. Ratificación explícita del dueño de §2 y del env, vía question.
4. Corrida oficial única; resultados escritos en §5 de este archivo + hallazgo
   26 actualizado en CONOCIMIENTO, en el commit de cierre.
5. Si el veredicto es NO CUMPLE se cierra igual; un intento 4 exigiría
   declaración nueva — aquí no se re-baja nada.

## §5 Resultados (escrito al cerrar la corrida oficial, 2026-10-17)

**Veredicto: NO CUMPLE** (H5' y G1 y G2 y C1'). Coste real: **9 juicios + 9
`generate()`** (5 rechazos de validación) de los ≤ 50 declarados. Suite 301
verde.

| criterio | umbral | medido | |
|---|---|---|---|
| H5' r4_ok y r5_ok | 5/5 | **3/5** (PEARL r2 · PG r1 · TCE r0) | NO |
| G1 resueltas finales >= base | 5/5 | **5/5** (intentó 2: 4/5) | sí |
| G2 encabezados base incluidos | 5/5 | **5/5** (intentó 2: 2/5) | sí |
| C1' suite + >=50% base + sin rechazos | todo | suite sí; 2 rechazos | NO |

Por arnés:

- **PEARL** aprueba en ronda 2 con 7399 chars y los 6 encabezados de la base
  (incluida `## Bibliografía`): G2 cumplida de verdad, no solo en el conteo.
  Trayectoria R4/R5: OK/FALLA → FALLA/OK → OK/OK (el juez parpadea entre
  rondas; al modelo le bastan2).
- **Procedural Graphs**: el primer intento de reparación fue un stub de 485
  chars — **el caso exacto del Hito 5 — y V1 lo RECHAZÓ**; el reintento salió
  con 2243 chars, aceptado, y aprueba ronda 1. Disco **restaurado de 488 a
  2360 chars** con documento real.
- **Task-CoEvolve** intacto: aprueba en ronda 0 sin tocarse.
- **ReASearch** y **WikiSkill**: **fail-fast declarado** — dos rechazos de
  validación cada uno (`causa=validacion_rechazada`), sin juicio sobre el
  texto rechazado y sin escritura a `BLUEPRINT.md`. ReASearch perdió el
  encabezado `«Bibliografía  »` (con los2 espacios finales de la base) en
  ambos intentos; su segundo borrador además metió espacios finales en el
  título donde la base no los tiene — V2 es igualdad literal declarada.
  WikiSkill truncó a 576 y 502 chars y perdió `## Bibliografía`.

Diagnóstico para un posible intento 4 (nada decidido; exige declaración nueva):

- **El bloqueo de degradación funciona**: 0 stubs aceptados, G1/G2 5/5 y PG
  restaurado — lo que en el intento 2 se compró con el documento aquí se paga
  con un reintento barato.
- El cuello de botella **se movió**: la reparación LLM no produce en 2
  intentos un documento completo para ReASearch/WikiSkill (trunca y pierde
  encabezados). Candidatos declarables: presupuesto de intentos mayor,
  reparación por secciones en vez de regeneración completa, V2 con espacios
  finales normalizados (hoy castiga la forma, no el fondo).
- **V1-V3 no ven lo semántico**: WikiSkill r1 pasa la validación y lo
  suspende el juez (R4 vuelve a fabricar). Pega directo al hallazgo 10,
  que sigue fuera de este hilo.
- **Disco**: ReASearch queda en el stub de H12 (517 chars) porque ninguna
  reparación suya llegó a ser aceptada — restaurarlo es una acción declarada
  aparte, no se hace fuera de corrida.

Erratas: la de redacción — §1.B dice «el texto rechazado… no toca disco» y el
runner lo guarda como evidencia en `result_fase1_h13.json`
(`texto_rechazado`); no toca `BLUEPRINT.md` ni los juicios, es más
información, no un resultado tocado. Aviso de consola del SDK Gemini (AFC)
durante el juicio de PG ronda 0, igual que en el Hito 5: no afectó a la fila.
Historial intacto: solo se añadieron filas; conteo de juicios por arm
C/D/E/R5/F/G/H 15 cada uno, H1 5, H1R 4, H12 11, **H13 9**.
