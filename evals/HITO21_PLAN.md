# HITO21 — Límite del canal b: diagnóstico y corrección del parseo JSON

> **Estado: BORRADOR, NO RATIFICADO.** No ejecutar ninguna corrida hasta que el
> dueño ratifique §3 (gates) y §4 (techo). Este plan nace de un análisis
> **offline de la evidencia del HITO20 §1** (0 tokens), no de una medición
> nueva.

## §0 — Estado y alcance

HITO20 §1 quedó **CERRADO 2026-10-24**: la matriz 17×12 con canal b + brazo
forzado midió 63/63 celdas, 2.686.674 tokens, media 82,47 (H19 70,43) y
saturación **SATURA**. El límite declarado en §5 son **4 celdas `max_turns`
con 0 escrituras**. Este hito **no** ejecuta B (tareas endurecidas) ni C1:
solo diagnostica y, si procede, corrige ese límite.

## §1 — Evidencia (0 tokens)

Fuente: `evals/results/result_sens_sd_corridab.json` +
`evals/sd_pilot/traces_corrb.sqlite` + informes de la corrida.

| celda | parada | writes | tools | acciones inválidas | patrón |
|---|---|---|---|---|---|
| `A2_checkout-rounding` | `max_turns` | 0 | 30 (16 read + 14 run_tests) | 1 | bucle conductual: lee y prueba, no escribe |
| `A3_checkout-rounding` | `max_turns` | 0 | 34 (21 read + 13 run_tests) | 0 | bucle conductual: lee y prueba, no escribe |
| `A4_dsl-parser` | `max_turns` | 0 | 11 (10 read + 1 run_tests) | 15 | JSON inválido repetido: `"content": """…` (comillas triples) |
| `A5_plugin-registry` | `max_turns` | 0 | 7 read | 13 | JSON inválido repetido con contenido grande |

Datos duros:

- A4 emite el mismo objeto inválido 15 turnos seguidos (85 tokens/turno); el
  `write_file` no llega a ejecutarse: `parse_actions()` devuelve 0.
- A5 repite 13 turnos de ~966 tokens; el contenido supera los 4.000 chars que
  guarda la traza (`_MAX_RAW_IN_HISTORY`), así que el tail no es auditable,
  pero tampoco hay span `tool` de escritura.
- A2/A3 **sí** parsean la mayoría de turnos: no es un fallo de formato, es
  conducta (leen y ejecutan tests sin intentar escribir).

## §2 — Hipótesis

- **H1 (formato, A4/A5)**: el modelo usa delimitadores de Python (`"""`) o
  contenido no escapado dentro de `write_file.content`; el JSON completo es
  inválido y el turno se pierde. El aviso “Responde SOLO con JSON” no basta
  para payloads grandes.
- **H2 (conducta, A2/A3)**: el bucle no tiene un recordatorio de “si no has
  escrito nada, escribe ahora”; el modelo puede leer y probar hasta agotar
  turnos sin crear/editar ficheros.
- **H3 (parser)**: `parse_actions()` escanea `{` en cualquier parte del texto,
  incluidas prosa o bloques de código; puede ejecutar acciones no previstas o
  descartar el turno entero. Es un riesgo transversal, no solo de estas 4
  celdas.

## §3 — Diseño y gates pre-registrados

### §3.1 Fase A — replay offline (0 tokens)

Antes de gastar: extraer los turnos inválidos guardados y probar un parser
tolerante **solo para `write_file.content`** (aceptar `"""…"""` y reparar
saltos/comillas), con estas condiciones:

- **G0-A**: en los turnos válidos de las 63 celdas, el parser nuevo debe ser
  **idempotente** (mismas acciones y mismos args que el actual).
- **G0-B**: en los turnos inválidos almacenados de A4/A2 debe recuperar un
  `write_file` con `path` correcto (el contenido puede ser parcial: se mide
  recuperación de acción, no calidad del fichero).
- Si G0-A o G0-B fallan → **no se corre**; se pasa a la opción de prompt.

### §3.2 Fase B — corrida mínima (solo si Fase A pasa)

Brazo único **b3** (bump de `CANAL_B_VERSION` + enmienda): parser tolerante
y/o recordatorio explícito de formato, decidido en Fase A. Celdas:

- 4 residuales (`A2_checkout-rounding`, `A3_checkout-rounding`,
  `A4_dsl-parser`, `A5_plugin-registry`).
- 4 controles ya resueltas, una por variante, elegidas por semilla
  pre-registrada antes de mirar resultados (p.ej. `A2_plugin-registry`,
  `A3_plugin-registry`, `A4_interval-scheduler`, `A5_batch-coalescer`).

Gates (intactos tras medir):

- **G1**: ≥2 de las 4 residuales con `writes > 0` y `stopped_by != max_turns`.
- **G2**: media de las 4 residuales sube ≥10 puntos vs su evidencia b2.
- **G3**: ningún control baja >5 puntos vs su evidencia b2 (regresión global).
- **G4**: 0 celdas `truncated_by_ceiling`.
- **G5**: coste ≤ techo de §4.
- **G6**: evidencia completa (`result_*.json`, informes, log, trazas, estado)
  y `canal_b_version` registrado por celda.

**Veredicto**: si G1-G6 pasan → `CUMPLE` (b3 reemplaza a b2 para medición
nueva); si falla G1/G2 → `NO CUMPLE` con causa; si falla G3 → revisar parser.

## §4 — Disciplina y presupuesto

- **Techo propuesto: 1.800.000 tokens** (8 celdas; proyección: 4 residuales
  ~919k según b2 + 4 controles ~600k = ~1,52M; margen 18 %). El dueño debe
  ratificarlo **antes** de lanzar; no se amplía a mitad de corrida.
- Modelo fijo `nvidia/nemotron-3-ultra-550b-a55b`; clave `NVIDIA_API_KEY_PILOTO`.
- `b3` solo se compara intra-versión; la comparación con b2 es diagnóstica,
  no causal. b1 queda congelado como evidencia histórica.
- Los intentos fallidos se documentan con causa y coste. La evidencia no se
  edita. Commits en ASCII.

## §5 — Cierre

Pendiente. Se rellenará con resultados, gates y veredicto; los umbrales de §3
no se tocan tras medir.
