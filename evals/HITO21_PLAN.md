# HITO21 — Límite del canal b: diagnóstico y corrección del parseo JSON

> **Estado: RATIFICADO 2026-10-24 por el dueño** (respuesta «sí» en sesión):
> techo **1.800.000 tokens** y gates §3 congelados antes de medir. El diseño de
> b3 se congela en §3.2 **después de la Fase A offline** y antes de lanzar.
> Este plan nace de un análisis **offline de la evidencia del HITO20 §1**
> (0 tokens), no de una medición nueva.

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

**Resultado Fase A (2026-10-24, 0 tokens; evidencia
`evals/results/result_hito21_fase_a.json`): PASA.**
G0-A: 369 turnos replayados, 257 con acciones base, **0 diferencias**.
G0-B: `A4_dsl-parser` **15/15** recuperadas (`mini_dsl/tokens.py`) y
`A2_checkout-rounding` **1/1** (`checkout/redondeo.py`). `A3` y `A5` no son
recuperables desde la traza almacenada (13 turnos cada una con salida cortada
a 4.000 chars; el raw completo no se guardó).

### §3.2 Fase B — corrida mínima (solo si Fase A pasa)

Brazo único **b3** (bump de `CANAL_B_VERSION` + enmienda), **congelado tras
Fase A**: (i) parser tolerante solo si el parser base devuelve 0 acciones
(recupera `"content": """…"""`), y (ii) recordatorio anti-bucle a partir
del turno 6 sin escrituras (exige `write_file` con contenido completo y avisa
de que el contenido debe ser string JSON, sin triples comillas). No cambia
el prompt base ni los tools; solo añade avisos cuando ya hay atasco. Celdas:

- 4 residuales (`A2_checkout-rounding`, `A3_checkout-rounding`,
  `A4_dsl-parser`, `A5_plugin-registry`).
- 4 controles ya resueltas y **congeladas antes de medir** (todas con
  `score=100` y `writes>0` en b2): `A2_plugin-registry`,
  `A3_plugin-registry`, `A4_interval-scheduler`, `A5_batch-coalescer`.

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

- **Techo ratificado: 1.800.000 tokens** (8 celdas; proyección: 4 residuales
  ~919k según b2 + 4 controles ~600k = ~1,52M; margen 18 %). **No se amplía a
  mitad de corrida.**
- Modelo fijo `nvidia/nemotron-3-ultra-550b-a55b`; clave `NVIDIA_API_KEY_PILOTO`.
- `b3` solo se compara intra-versión; la comparación con b2 es diagnóstica,
  no causal. b1 queda congelado como evidencia histórica.
- Los intentos fallidos se documentan con causa y coste. La evidencia no se
  edita. Commits en ASCII.

## §5 — Cierre

**Corrida 2026-10-24 19:34–20:08 (8/8 celdas, 66 llamadas LLM, 33 min).**
Coste **596.343 tokens** (prompt 517.262 + completion 79.081) = **33,1 %**
del techo de 1.800.000. Evidencia: `evals/results/result_hito21.json`,
`evals/results/informes_hito21/*.md`, `evals/sd_pilot/traces_h21.sqlite`,
`evals/sd_pilot/_run_state_h21.json`, `evals/logs/hito21_run.log`.

| celda | tipo | b2 | b3 | Δ | turnos | writes | parada | inválidas | tokens |
|---|---|---|---|---|---|---|---|---|---|
| `A2_checkout-rounding` | residual | 38,1818 | **0,0** | −38,1818 | 8 | 5 | `final` | 0 | 103.720 |
| `A3_checkout-rounding` | residual | 38,1818 | **100,0** | +61,8182 | 8 | 5 | `final` | 0 | 105.566 |
| `A4_dsl-parser` | residual | 13,0435 | **89,1304** | +76,0869 | 7 | 8 | `final` | 0 | 87.608 |
| `A5_plugin-registry` | residual | 64,2857 | **100,0** | +35,7143 | 3 | 1 | `final` | 0 | 9.325 |
| `A2_plugin-registry` | control | 100,0 | **64,2857** | **−35,7143** | 17 | 0 | `max_turns` | 12 | 152.310 |
| `A3_plugin-registry` | control | 100,0 | 100,0 | 0,0 | 15 | 1 | `final` | 8 | 102.481 |
| `A4_interval-scheduler` | control | 100,0 | **56,6667** | **−43,3333** | 4 | 0 | `final` | 0 | 21.724 |
| `A5_batch-coalescer` | control | 100,0 | 97,0588 | −2,9412 | 4 | 1 | `final` | 0 | 13.609 |

Gates (§3.2, sin tocar):

- **G1 PASA**: 4/4 residuales con `writes>0` y parada `final`.
- **G2 PASA**: media residual **72,2826** vs 38,4232 → **Δ +33,8594**.
- **G3 FALLA**: caídas A2_plugin **−35,7143**, A4_interval **−43,3333**,
  A5_batch −2,9412; solo A3_plugin se mantiene. Umbral −5 superado por dos
  controles.
- **G4 PASA**: 0 `truncated_by_ceiling`; **G5 PASA**: 596.343 ≤ 1.800.000;
  **G6 PASA**: las 8 celdas registran `canal_b_version="b3"`.

**Veredicto: NO CUMPLE** (falla G3, causa única y suficiente). b3 **no se
adopta**: `CANAL_B_VERSION` vuelve a **b2** por defecto; `--hito21` fuerza b3
solo para reproducir esta evidencia (`BIBLIOTECARIO_CANAL_B_VERSION=b3`).
La Fase B no reemplaza a b2 ni habilita medición nueva con b3.

### Lectura

- El parser/aviso **desbloquea 3 de 4 residuales** (A3 +61,8; A4 +76,1;
  A5 +35,7), con 4/4 escribiendo y parando en `final`, y un coste muy por
  debajo del techo. A4 pasa de 15 acciones inválidas a 0 y A5 de 13 a 0.
- Pero **A2_checkout cae a 0,0** pese a escribir 5 veces: produce código que
  no pasa los tests ocultos; el objetivo “escribir” no equivale a “resolver”.
- La regresión de controles es heterogénea: A4_interval cae 43,3 puntos en
  **4 turnos y 0 writes** (el aviso anti-bucle empieza en el turno 6) y con
  **0 acciones inválidas**, así que **no puede atribuirse al nudge**; apunta a
  varianza del modelo o a otro efecto de b3. A2_plugin sí llega a 17 turnos
  con 0 writes y 12 inválidas (nudge activo): posible interacción, no aislada.
- **n=1 por celda y b3 empaqueta parser+nudge**: no hay atribución causal.
  Lo que sí queda medido es el veredicto global: el paquete b3 no es seguro
  para producción bajo el gate pre-registrado.
- Incidencia de proceso: `_run_cell` no pasaba `on_turn` a `Cell`, por lo que
  **no se escribió `_heartbeat_h21.json`** (el resto de evidencia sí). Se
  corrigió tras la corrida y se añadió test de regresión; también se corrigió
  `snap_turns or …`, que ignoraba `snap_turns=()`. Ninguno de los dos afecta
  a scores ni a tokens (solo observabilidad/snapshots locales).

### Siguiente (no ratificado)

HITO22 debería **aislar parser y nudge** (brazo parser-solo vs nudge-solo),
repetir controles **n≥2** para separar varianza de efecto, y mantener A2 como
caso de calidad (escribir no basta). Requiere plan y techo nuevos; no se lanza
con el techo de este hito.

