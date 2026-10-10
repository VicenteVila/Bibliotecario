# Hito 1 — responder bien lo que tiene, sin perder el piso

**Aprobado 2026-10-10.** Escrito a partir de lo medido en `HITO0.md`,
`REPORT_BLIND.md` y `PLAN_READING.md`. La columna *estado hoy* es resultado ya
medido; el resto es lo que queda por correr.

## Decisiones adoptadas

Las cuatro que quedaban abiertas al redactarlo, cerradas por el responsable:

| # | decision | eleccion | por que |
|---|---|---|---|
| 1 | Umbral de calidad | **`judge_mean >= 4.50`** | Por encima de la base r1 (4.171) y de la actual (4.229); por debajo de lo ya alcanzado (r5 4.714). La distancia +0.271 es detectable con el protocolo pareado (MDE 0.112), no con una run suelta (0.194). |
| 2 | Temperatura | **`0.0` para todo**, y **una run extra** con la config de r5 a 0.0 | `0.0` es donde la fabricacion es 0% y es la unica palanca medida gratis. El precio (~0.17 de juez) y la fabricacion (51.6% -> 33.9%, p=0.019) van en signo opuesto, asi que no es un confundo: es una palanca. Sin rerunear r5 a 0.0 no hay baseline honesto. |
| 3 | Presupuesto | **~9-10M** con corte a **~4M** si ninguna candidata pasa **4.35** | La puerta evita acabar 10M sin respuesta. |
| 4 | Alcance | **Hito 1 = QA**, con el **diseno de la metrica de blueprints en paralelo y sin coste de tokens** | El diseno no castea tokens y encaja en los 25-40 min de reloj de cada run. Asi el Hito 2 arranca con metrica puesta. |

El flag que hace posible la decision 2 es **`PROMPT_LEGACY`** (`state.py`,
`loop.py`): restaura literalmente el prompt previo a `15261a0` para comparar
**los dos prompts a la misma temperatura**. Verificado contra git: con `=1` los
prompts son byte-identicos a `15261a0^`, y con `=0` a `main`. Sin el flag, r5
(corrio a temp 0.2) no tiene baseline comparable y la deuda no se puede resolver.

## Por que este hito

El Hito 0 dejo el proyecto con **dos mitades separadas, cada una buena en lo suyo
y ninguna buena en las dos**:

| | calidad (juez) | fabricacion en no respondibles |
|---|---|---|
| **r5** (mejor run conocida) | **4.714** | 1 fabricada de 5 |
| **promptstop** (2 runs) | 4.229 | **0%** (0/64 en la suite de 64) |

El cambio que arreglo la fabricacion **costo puntos en la mitad respondible** y
no esta aislado de la temperatura (0.2 -> 0.0). Hito 1 es literalmente juntar en
una sola configuracion lo mejor de las dos columnas.

No es una meta de comodidad: sin esto, el sistema es o bien honrado y mediocre,
o bien bueno y propenso a inventar.

## Criterios

| # | criterio | umbral | medido sobre | estado hoy |
|---|---|---|---|---|
| **1** | **Calidad** | `judge_mean >= 4.50` sobre 3 runs pareadas | `golden_blind_qa` (35 respondibles) | **4.229** (2 runs) — falta +0.271 |
| **2** | **Piso de fabricacion** | `<= 5%` de fabricadas | `golden_abstention` (64) | **0%** ✓ |
| **3** | **Piso de run_score** | `>= 0.75` en las DOS mitades | blind + abstencion | **0.806** y **1.000** ✓ |
| **4** | **Sin confundo** | misma temperatura en toda comparacion A/B | — | **sin aislar** (0.2 vs 0.0) |
| **5** | **Sensibilidad declarada** | MDE `<= 0.15` con el protocolo elegido, fijado ANTES de medir | — | **0.194** con 1 run; **0.112** con 3+pareado |

Criterios 2 y 3 son **guardias de regresion**, no objetivos: ya estan cumplidos
y cualquier configuracion nueva tiene que volver a pasarlos. El objetivo real es
el 1, y el 4 y 5 son lo que hace que el 1 signifique algo.

### Por que 4.50

- Por encima de la base `r1` (4.171) y de la actual `promptstop` (4.229).
- Por debajo de `r5` (4.714) y `r6` (4.600), asi que **es alcanzable**: ya se
  llego antes, solo que sin el piso de fabricacion.
- La distancia a cubrir (+0.271) es detectable con el protocolo pareado del
  criterio 5 (MDE 0.112), no con una run suelta (MDE 0.194).

Lo que lo hace dificil no es el numero: es que **ninguna run que tenga 4.5+
ha pasado nunca la suite de 64**.

## Protocolo de medicion

Declararlo antes de la primera run. Cambiarlo despues invalida la comparacion.

1. **Temperatura fijada en todo** (criterio 4). Candidata: `--temperature 0.0`,
   que es la unica palanca medida que funciona y es gratis. Si se elige 0.2, se
   cambia para todos los sistemas comparados, no solo para el nuevo.
2. **3 runs por sistema, pareadas por pregunta** sobre `golden_blind_qa`.
   Con sd intra-item 0,709 eso da **MDE = 0.112** al 95% sobre las mismas 35
   preguntas. Con una run suelta serian 0,194 y la mitad de las mejoras reales
   no se verian.
3. **La suite de 64 se corre en la configuracion FINAL**, no en cada
   candidata: son 2,1M por pasada y criterio 2 solo puede empeorar en el
   resultado definitivo, no en los ensayos.
4. Juez `openai/gpt-oss-20b`, familia distinta a la del agente, como ya viene
   haciendo todo el corpus.

### Coste

| paso | que | tokens | puerta |
|---|---|---|---|
| 0 | **baseline**: config de r5 (`PROMPT_LEGACY=1`) a temp 0.0, 1 run | 1,2M | — |
| 1 | candidata a candidata (blind, 2-3 runs) | 2,4-3,6M | si ninguna pasa **4.35**, se corta |
| 2 | medicion final: 3 runs pareados | 3,6M | — |
| 3 | suite de 64 sobre la config final | 2,1M | — |
| | **total estimado** | **~9-10M** | **minimo posible ~6.9M** |

La puerta del paso 0 decide si el paso 1 hace falta. Tres salidas posibles,
todas medidas contra los 4.229 de `promptstop` ya existentes:

| si el baseline sale… | significa | accion |
|---|---|---|
| **~4.2-4.3** | la deuda 0.486 era temperatura | `promptstop` ya esta al nivel; **se salta el paso 1** |
| **~4.5-4.7** | la deuda es del prompt | **hacen falta candidatas** |
| **< 4.2** | ni temperatura ni prompt lo explican | se reescribe el diagnostico en vez de gastar |

Si tras 2 candidatas ninguna sube el juez por encima de 4,35, se para y se
reescribe el diagnostico en vez de seguir gastando.

## Puertas de salida (que se descarta si no se mueve)

Siguiendo el mismo criterio que gasto el Hito 0: nada entra a produccion sin su
medicion, y lo que no mueve la metrica se suelta.

- **El residuo ya esta diagnosticado y no es del cierre.** `PLAN_READING.md`
  cierra con que el 74% de los fallos *si cierran el chunk gold*: es un problema
  de discriminacion con la evidencia en el contexto, y que "los parches del
  agente no lo atacan". Las tres vias del plan (ancla numerica, puerta
  multiparte, verificacion de cita) **ya se midieron y se descartaron**.
- Asi que el orden es: primero **aislar temperatura** (es gratis respecto al
  diagnostico: puede explicar parte de los 0,486), despues **atacar por el lado
  de la recuperacion o de la pregunta**, que es lo que el propio plan marca
  como no agotado.

## Lo que este hito NO cubre

El README promete dos cosas y este hito solo cierra una.

1. **Blueprints e `implement`** — la mitad del valor del producto. `blueprint`
   y `implement` existen en `api.py` y **no tienen ni metrica definida**: nadie
   ha escrito que seria un blueprint bueno. Ese es el primer trabajo del
   **Hito 2**, y es de diseno, no de medicion. Hasta que exista esa metrica no
   se puede decir que falta "poco" o "mucho": es un frente sin mapa.
2. **Auto-mejora** (`evolve`, lecciones, `Procedural Graphs`, `refiner`, wiki
   con gating). Implementada, **sin medir** — y el unico componente que si se
   midio, la seleccion y estimacion de Task-CoEvolve, **salio negativo**
   (`REPORT_COEVOLVE.md`): no le gana a no hacer nada en el regimen actual.
3. **Trazabilidad de la run** (domino 4, "deliberate diagnosis, verification"):
   un agente cuyo primer turno diverge no puede pararse a si mismo a partir de
   la evidencia. Sigue sin existir.

## Como se sabra que esta cerrado

La misma estructura que el Hito 0: una tabla *criterio / umbral / medido*, con
los tres primeros rellenados con el valor de la run final, la seccion de erratas
si algo resulta estar mal medido, y el coste real en tokens. Si algun umbral
queda sin alcanzar, se dice aqui y no se maquilla con una media.
