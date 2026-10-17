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

`evals/run_fase1_h13.py` → `evals/result_fase1_h13.json` (filas `H13`) y
juicios `arm="H13", run=ronda` en `evals/result_q1_r4r5.json` (H1, H1R, H12
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
