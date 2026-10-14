# Especificación del Benchmark

> **Documento congelado.** Se declara **antes** de medir. Si algo aquí cambia, se
> declara como *benchmark nuevo con línea base nueva* — nunca en silencio, nunca
> mezclando series.
>
> Fundamento: `Documentos/Stop Comparing LLM Agents Without Disclosing the Harness.pdf`
> y `Documentos/EVO-BENCH CAN LANGUAGE MODELS IMPROVE AGENT HARNESS.pdf`.
> **Estado: RATIFICACIÓN PARCIAL — 2026-10-14.**
> Ratificado: **bloque B-1** (§5.2.0, §5.2.1 fase B-1, fórmula, `BUILD=0`,
> prohibición, regla B-2, congelados B-1). **Sin ratificar: todo lo demás**,
> incluida la **fase B-2**. Ver §11.

---

## 0. Qué es este documento y qué no

**Es** la regla fija con la que se dice si un arnés funciona.

**No es** un resultado. No hay ningún número medido bajo esta especificación todavía.

**Y aclara un punto que estaba ambigüo:** los números del Hito 0-2 **no son
resultados de benchmark**. Son **diagnóstico de QA**: no había `D^eval`, ni
Harness Card, ni criterio `Sens(x)`, ni presupuesto, ni bases. Siguen siendo
útiles — pero **no se comparan entre sí como si fueran un experimento.**

---

## 1. Propósito

Responder a **una sola pregunta**, de la forma más dura posible:

> **¿El arnés diseñado por el agente, con un corpus que crece, funciona mejor
> que el arnés de partida — y es mejor por el conocimiento que leyó, no por
> casualidad?**

Para que esa respuesta sea atribuible, hace falta **inmutabilidad del benchmark**
y **varianza por arnés medible**. Las dos cosas se declaran aquí.

---

## 2. Estructura en dos capas

El sistema evalúa dos cosas distintas que **no se confunden**:

| capa | qué mide | estado |
|---|---|---|
| **A — Fidelidad del diseño** | ¿el arnés se apoya en la fuente y no inventa? | ✅ **existe**, umbrales ya declarados en Hito 0-2 |
| **B — Rendimiento del arnés** | ¿el arnés cumple su cometido? | ❌ **no existe** — hay que construirla |

**Relación:** A es **puerta de paso**, B es **resultado**. Un arnés que no pasa
A no llega a ser juzgado en B. Pero pasar A **no es éxito** — es el mínimo para
que el resultado de B sea interpretable.

*Evo-Bench* mide solo B (tareas resueltas). *Stop Comparing* exige declarar el
arnés para que B sea atribuible. Nosotros necesitamos las dos: **A porque el
conocimiento viene de papers, B porque de lo contrario no sabemos si sirve.**

---

## 2.1 La distinción estructural: ETCSOVG es invariante, el arnés no

> *«un agente que diseñe páginas web no debería tener el mismo arnés idéntico que
> un agente que diseñe juegos de plataformas, a pesar de que el principio rector
> ETCSOVG sea el mismo»*

| | qué es | ¿cambia por dominio? |
|---|---|---|
| **ETCSOVG** | el **vocabulario de declaración** — las 7 capas que todo arnés tiene | **NO** |
| **Contenido de cada capa** | lo que **hay dentro** | **SÍ** — web ≠ juegos |
| **Disciplina del benchmark** | congelados, `D^eval`, `Sens`, presupuesto | **NO** |
| **Suite / scorer / `Overall(d)`** | **qué significa «cumplir»** en ese dominio | **SÍ** |

**Consecuencias operativas:**

1. `Overall` es **por dominio**: `Overall(d, H)`. **Nunca se comparan notas entre
   dominios** — un 47 en web no es un 47 en juegos.
2. Arneses de dominios distintos **solo se comparan a nivel ETCSOVG**: qué capas
   están débiles, qué cambió, por qué se espera que afecte a estabilidad / deriva
   / lag de control.
3. Si se quiere una cifra global de «¿mejora el agente?», el **peso entre dominios
   se declara antes de medir** (Evo-Bench usa 2:2:1).

**Y esto es el mecanismo de transferencia:** los papers enseñan principios
**generales** (domain-agnostic, ETCSOVG); el dominio es donde se prueba que los
entendió. Aplicar una idea de *Harness-of-Harness* —que nunca habló de
videojuegos— a un arnés de juegos **es transferencia**, y solo es medible si el
dominio `d` y su `D^eval_d` están congelados y ocultos.

---

## 3. Congelados

Esto **no se toca** durante ninguna ejecución. Cualquier cambio requiere
declaración formal de benchmark nuevo.

### 3.1 Identidad del experimento
- **Dominios** — ver §4.0. Lista cerrada; añadir un dominio = benchmark nuevo.
- **Modelo de política** — uno solo, fijo en todas las celdas.
- **Configuración de endpoint** — idéntica en todos los arneses. **Ningún ajuste
  de API específico de arnés** (*«intentionally a harness study rather than a
  decoding study»*).
- **Juez** — `gemini-3.1-flash-lite`, `temperature=0`, JSON forzado.
  **Ya caracterizado** (§8.12/§8.13): 0% flips, 0 fallos, discrimina.
  *No se vuelve a calibrar. No se cambia a mitad de serie.*
- **Prompt del juez** y su plantilla — fijos.
- **Suites** `D^val` y `D^eval`, sus tamaños y sus repartos.
- **Semilla** del split y de cualquier muestreo — declarada.
- **Guion de evaluación** / pipeline de scorers.
- **Orden de tareas** y **entorno de ejecución**.
- **Parámetros de API** (salida máxima, *timeout*, configuración por defecto).
- **Reglas de parada** y **presupuesto**.
- **Lógica de agregación** y definiciones de métrica.
- **Harness Card de cada arnés** — congelada al declarar el brazo.

### 3.2 Lo único que varía
**El arnés.** Es el factor controlado. Nada más.

### 3.3 Qué queda fuera del alcance
Comparar **modelos**. El modelo está fijo. Cualquier afirmación tipo
«modelo X es mejor» queda **fuera de lo que este benchmark puede decir**.

---

## 4. Suites: `D^val` y `D^eval`

### 4.0 Dominios declarados

**Lista cerrada.** Añadir un dominio = benchmark nuevo con línea base nueva.

| dominio | arnés | suite existente | scorer |
|---|---|---|---|
| **`web_development`** | **ReaWeb** (`c:\EW`) | `reaweb-harness/benchmark/tasks.yaml` — **14 tareas** | evaluator 10 ejes, *blocking gate* → techo **40** |
| **`game_development`** | **ReaGame** (`c:\EG`) | `EG/benchmark/game_tasks.yaml` — **8 tareas** (4 arquetipos × 2) | evaluator 12 ejes, *gates P0* → techo **40** |

**Por qué estos dos y no los 14 de CogniTeam:** son los **únicos** con un arnés
real construido y con suite de tareas fija. CogniTeam define 14 dominios / 61
arquetipos, pero solo 5 están «soportados» y **solo 2 tienen arnés**. Los demás
entran cuando tengan arnés — declaración de extensión, no de cambio.

**Base del cometido por dominio:** cada arquetipo declara su misión en
`archetype.yaml` — `objetivo_principal`, `features_obligatorias`, KPIs.
*En CogniTeam no existe el término «cometido»*: el equivalente es el contrato
`structure` + `verification` del arquetipo. **Ojo: solo 24/61 arquetipos definen
`structure` y 17/61 `verification` — los demás pasan la compuerta vacía
(`return {"passed": True, ..., "score": 1.0}`).** Eso es un agujero que el
benchmark no puede heredar.

### 4.1 Regla de partición

| suite | rol | ¿el agente la ve? | ¿devuelve evidencia? |
|---|---|---|---|
| **`D^val`** | validación visible — se usa para iterar | **sí** | sí |
| **`D^eval`** | evaluación final | **no** | **cero** — solo tras congelar el arnés |

> *«During evolution, the evolver can request validation evaluations only on
> `D^val`, while `D^eval` is reserved for final evaluation after the harness is
> frozen.»* — Evo-Bench §3

**Regla dura:** `D^eval` **nunca** se usa para elegir prompts, arneses o
umbrales. Si se usa, deja de ser `D^eval` — se destruye y se crea otra con
declaración de benchmark nuevo.

### 4.2 Criterio de sensibilidad `Sens(x)` — **requisito de entrada**

Una pregunta/task **solo entra** en el benchmark si **responde a cambios de arnés**.

```
Sens(x) = corr_pearson( {m_h(x)}_{h ∈ H_aux} , {Q_h^(−x)}_{h ∈ H_aux} )
```
donde `m_h(x)` = score de `x` bajo arnés `h`, y `Q_h^(−x)` = calidad *leave-one-out*
del arnés `h` sobre el resto.

**Regla: `Sens(x) ≤ 0` → descartada.** Justificación de Evo-Bench §4.2:
*«high variance only captures the magnitude of performance differences and does
not indicate whether these differences reflect the relative quality of harnesses.»*

- Reparto: estratificado por dificultad, **distribuciones idénticas** entre
  `D^val` y `D^eval`.
- `H_aux` = conjunto fijo de arneses representativos usados para calcular la
  sensibilidad. **Se congela** al construirlo.
- **Criterio `Sens > 0` — declarado ahora, antes de medir.**

### 4.3 Requisito técnico previo
Calcular `Sens(x)` **exige score por pregunta**, no agregado.
Hoy `result_q1_r4_all.json` guarda `r4_ok` booleano por brazo → **insuficiente.**
→ *Acción previa: re-juzgar a nivel de pregunta.*

---

## 5. Métricas

### 5.1 Capa A — Fidelidad del diseño

Umbrales **ya declarados en Hito 0-2. Se mantienen intactos — no se re-bajan.**

| métrica | umbral | estado |
|---|---|---|
| `R4` atribución | **≥ 8/15** | ✅ medido (E, 9/15) — §8.13 |
| `R5` cita a fuente | **≥ 10/15** | ✅ medido (G, 13/15) — §8.12 |
| `B5` cita en **cada** módulo | **100%** | ✅ medido — §8.9 (95,8% → lista de revisión) |
| `R1` / `R2` / `R3` | umbrales Hito 0-2 | preservados |
| Parseo del juez | **0 fallos** | ✅ §8.12/8.13 |

> **Nota de régimen:** `B5` a **100%** con clasificación mecánica + revisión
> humana obligatoria (dec. 17). Si `B5` llegara a re-bajarse, sería una violación
> de §7 del `PROPOSITO.md`.

### 5.2 Capa B — Rendimiento del arnés

#### 5.2.0 REENCUADRE DECLARADO — el evaluador actual mide código, no juego

Leídos `GameCraft-Bench` y `GameDevBench` (los dos papers de benchmark de juegos
de `c:\EG`), **el evaluador estático de 12 ejes de ReaGame no cumple ninguno de
los dos estándares**:

> *«source code, project structure, assets, and screenshots may be useful for
> debugging, but they **do not substitute for observed behavior under player
> input**.»* — GameCraft §3.3

> *«methods… are, however, **either proxies to correctness or non-deterministic**.
> GameDevBench instead uses Godot's testing framework which allows us to
> **directly test game behavior**.»* — GameDevBench §3.2

**Se declara, sin tocar ningún umbral:**

| umbral existente | qué era | qué pasa a ser | se toca |
|---|---|---|---|
| **techo 40** (*gates* P0) | scorer de rendimiento | **Capa A-bis — calidad del código** | **NO** |
| **pesos** (`gameplay 2.0`, `visual 2.0`, resto 1.0/1.5) | pesos de rendimiento | **pesos de A-bis** | **NO** |
| **scores 100** de ReaGame | «el juego funciona» | **«el código pasa el proxy estático»** | **NO** — solo se renombra lo que miden |

**Y se añade**, por tanto, una scorer **genuina de Capa B** que sí ejecute el
juego (§5.2.1). **Las dos se reportan por separado. No se agregan.**

> *Mismo régimen que con R4/R5 (dec. 12/17): umbral intacto, papel declarado,
> valor a la vista. Lo que no se hace es re-bajar ni mezclar.*

#### 5.2.1 La dos scorer de Capa B — por dominio

| dominio | scorer actual | scorer de Capa B a construir | fuente |
|---|---|---|---|
| **`game_development`** | estático 12 ejes → **A-bis** | **ejecución**: replay de trazas **o** tests en Godot | GameCraft / GameDevBench |
| **`web_development`** | estático 10 ejes → **A-bis** | **ejecución**: functional testing en Chrome *(ya parcial: `functional_tester.py`)* | por definir |

##### `game_development` — scorer en DOS FASES *(enmienda 1, tras preflight)*

| | **GameCraft-Bench** | **GameDevBench** |
|---|---|---|
| tareas | **140** / 15 familias | **333** / 4 categorías de skill |
| éxito se decide por | **replay de trazas del agente** + juez multimodal sobre **rúbrica oculta** | **tests unitarios ejecutados en Godot** |
| scorer | GPT-5.5 multimodal, 0–1 por ítem | **binario** pass@1, sin crédito parcial |
| gate de build | **BUILD = 0 → nota final = 0** | *starting point* debe fallar · *ground truth* debe pasar |
| categorías y pesos | **M 0.15 · D 0.35 · V 0.15 · A 0.35** | ninguno |
| validación de tarea | **oracle** Godot + rúbrica ≤24 ítems | tests ↔ instrucción **bidireccionales** |
| presupuesto | 7200 s agente / 1800 s verificador | — |
| mejor agente | **41.46 %** | **53.8 %** |

**Decisión original: GameCraft** — ReaGame *ya* genera juegos completos, no edita
tareas aisladas. **Pero el preflight (2026-10-14) demostró que el camino completo
de GameCraft no es ejecutable hoy**, y que la mitad determinista de GameDevBench
**sí lo es, y es gratis**. Se declara por tanto **dos fases**.

###### Preflight (2026-10-14) — medido, no supuesto

| comprobación | resultado |
|---|---|
| Godot | ✅ `4.7.1.stable` en `EG/.tools/godot` — headless, exit=0 |
| Smoke test del juego | ✅ carga sin errores |
| **Tests de comportamiento en motor** | ✅ **5/5 PASS** · `VALIDATION_PASSED` |
| Xvfb / ffmpeg | ✅ instalados |
| **xdotool** | ❌ **no instalado** |
| **ReaGame emite trazas `Π`** | ❌ **no** |

**Resultado del test de comportamiento** (copia temporal, ReaGame **no modificado**):

```
C1  el proyecto arranca y hay nodo jugador          PASS
C2  el jugador es CharacterBody2D                   PASS   ← tipo real, no texto
C3  tiene move_and_slide                            PASS
C4  ui_left/ui_right/ui_accept registradas          PASS
C5  se MUEVE bajo input  →  dx=85.00 px en 40 f.   PASS   ← COMPORTAMIENTO
```

> **C5 es la diferencia de constructo.** El evaluador estático haría
> `grep "move_and_slide"` y aprobaría un juego con la función escrita pero
> **nunca conectada**. Este test **ejecuta el juego y mide el desplazamiento**.

###### Las dos fases

| fase | qué mide | scorer | coste | estado |
|---|---|---|---|---|
| **B-1** | **Core Mechanics (M)** | **tests de comportamiento en Godot** — determinista, binario | **0** | ✅ **viable hoy — preflight pasado** |
| **B-2** | **D · V · A** | replay de trazas + juez multimodal (GameCraft) | alto | ❌ requiere `xdotool` + trazas `Π` |

```
Score = BUILD × (0.15·M_B1 + 0.35·D_B2 + 0.15·V_B2 + 0.35·A_B2)
        └───── B-1, determinista ─────┘  └──── B-2, fase 2 ────┘
```

**Ventaja científica:** se gana un **suelo determinista** antes de introducir
cualquier juez. Si B-1 y B-2 se construyeran a la vez, **no se podría separar la
varianza del juez de la varianza del arnés**.

**Regla:** **B-2 no se ratifica hasta que B-1 esté funcionando end-to-end.**

###### Especificación B-1 *(ratificable ahora)*

- **Binario por test** — `VALIDATION_PASSED` / `VALIDATION_FAILED` (GameDevBench).
- **Se ejecuta en el motor**, headless. **Nunca** `grep` sobre el código.
- **M = tests que pasan / tests escritos.**
- **BUILD = 0** si el proyecto no carga → **nota final = 0** *(cero, no techo)*.
- Cada test **mapea a una feature pedida en la tarea** — *«unit tests must only
  test for features explicitly requested in the instructions»* (GameDevBench §2.2).
- Tests **flexibles a múltiples soluciones** — no pueden forzar una implementación.
- **Congelado:** motor (Godot 4.7.1), el conjunto de tests, el comando de ejecución.

###### Especificación B-2 *(NO ratificar todavía)*

Extraída de GameCraft §3.2, para cuando se construya:

- **Trazas `Π` del agente** — 1–10 demos JSON, eventos de ratón/teclado,
  ≤20 s, 30 fps, viewport 1280×720.
- **Replay determinista** — `xdotool` + `Xvfb` + `ffmpeg`, muestreo 2 fps.
- **Sin exploración por el verificador** — *«making scores depend on the
  verifier's exploration policy.»* **Prohibido.**
- **Rúbrica oculta `ρ`** — el agente **no ve** el checklist. *(En ReaGame hoy
  el agente **puede leer su propio evaluador** — tiene que cerrarse.)*
- **Ítems ≤24**, anclados `0 / 0.5 / 1`, **tope 0.5** a lo *label-only /
  decorativo / widgets por defecto / formas programáticas*.
- **`max`** para requisitos puntuales · **`mean`** para propiedades persistentes.
- **Congelado:** viewport, fps, ventana, juez, plantilla del juez, pesos, fórmula.

###### Restricción común a ambas fases

- **Sin exploración por el verificador** en ninguna de las dos.
- **Pesos** `M 0.15 · D 0.35 · V 0.15 · A 0.35` — heredados de GameCraft.

> **¡Atención a la inversión!** GameCraft prioriza **Depth y Art (0.35 cada uno)**
> sobre Mechanics y Visuals (0.15): *«a complete game should extend beyond minimal
> mechanics and functional prototypes»*. El evaluador actual de ReaGame hace
> **exactamente lo contrario** (`gameplay 2.0` el más pesado). **Esa inversión
> se declara como hallazgo** — no se corrige por ahora; se deja a la vista.

##### Métricas generales de Capa B

| métrica | definición | dirección | fuente |
|---|---|---|---|
| **`Overall(d, H)`** | score de `H_T` congelado en `D^eval_d` | ↑ | Evo-Bench |
| **`AnytimeVal(d)`** | media del mejor-so-far sobre el presupuesto; si cortas antes, **se arranca el resto** | ↑ | Evo-Bench |
| **`RR(k)`** | prob. de volver a estado que avanza la tarea en ≤ `k` pasos. **Curva en `k ∈ {1,3,5,10}`**, no un número | ↑ | Stop Comparing |
| **Context Retention** | fracción de archivos/tests/restricciones relevantes presentes en el contexto por paso | ↑ | Stop Comparing |
| **Control Lag `τ`** | pasos entre anomalía detectada y señal correctora que llega a la política | ↓ | Stop Comparing |
| **Recursos** | coste USD · tokens · **tiempo secuencial** | ↓ | Stop Comparing / GameDevBench |

> *«RR(k) as a curve over k ∈ {1,3,5,10}… preferable to a single number because
> the choice of k trades promptness against eventual recovery.»* — Stop Comparing §5

**Prohibido agregar A-bis y B en una sola nota.** Se reportan las dos.

### 5.3 Estadísticas de descomposición — si hay rejilla `M × H`

Con modelo fijo, `MV = 0` por construcción. Si en algún momento se varía el
modelo, **se reportan los cinco**, sin excepción:

1. `HV` por modelo
2. `MV` por arnés
3. ratio `HV/MV`
4. **recuento de inversiones de ranking** entre pares de modelos × pares de arneses
5. `η²_p` — **siempre junto con** `ω²` o intervalo bootstrap **y** con el recuento
   de inversiones. *«a large η²_p is neither necessary nor sufficient for ranking flips»*

### 5.4 Instrumentación obligatoria: **TraceForge**

Las tres métricas de trayectoria que *Stop Comparing* exige — **`RR(k)`**,
**Context Retention** y **Control Lag `τ`** — **no se pueden medir sin trazar**.
Son intrínsecamente temporales: necesitan saber qué vio el modelo en cada paso,
qué anomalía se detectó y cuándo llegó la señal correctora.

**`TraceForge` (`c:\TraceForge`) es el instrumento.** No es un añadido: es
**requisito de medición** de §5.2. Sin él, `RR(k)`, Context Retention y `τ`
quedan **no medibles** y el benchmark está incompleto.

| lo que *Stop Comparing* exige | lo que TraceForge da |
|---|---|
| traza persistente con jerarquía de llamadas | `@trace()` / `span()`, `trace_id` que fluye por toda la ejecución |
| coste por paso | coste automático por modelo (200+) |
| latencia por nodo | duración por span + *streaming* (TTFT, *throughput*) |
| auditoría de fallos post-ejecución | SQLite + CLI + informe HTML/Gantt + dashboard |
| — | export **OpenTelemetry**, enmascaro **PII**, soporte *async* |

**También cubre la capa `O` de ETCSOVG**, que es la más débil en *ambos* arneses:
ReaWeb fue criticado exactamente por eso — *«echo de menos OpenTelemetry /
Langfuse / Arize Phoenix… el BudgetTracker es reactivo, no analítico»*.

> **Congelado:** el esquema de traza, los campos capturados y el punto de
> instrumentación. Cambiar la instrumentación a mitad de serie invalida `RR(k)`.

---

## 6. Harness Card — **obligatoria para cada arnés**

Sin ella, **el resultado no se publica.** Siete capas, todos los campos:

| capa | campos mínimos |
|---|---|
| **E — Execution** | sustrato de ejecución, *sandbox*, acceso a FS, acceso a red, *timeout* de tarea, *timeout* de paso, máx. pasos, punto de entrada de evaluación |
| **T — Tool** | lista de herramientas, estilo de esquema, política de selección, formato de error, clases de error reintentables, ¿visibles al modelo o *middleware* oculto |
| **C — Context** | tope de contexto, política de orden, política de compresión/resumen, método de recuperación, memoria persistente, política de caché |
| **S — Scheduling** | bucle del agente, regla de parada, política de reintento, escalada, delegación, *rollback* |
| **O — Observability** | artefactos registrados, formato de trayectoria, *checkpoints*, trazas, logs de validación, ¿los fallos se pueden auditar después? |
| **V — Verification** | parser de salida, validación de esquema, autochequeo, ejecución de tests, detección de anomalías, validación de parche final |
| **G — Governance** | modelo de permisos, listas permitido/denegado, límites de efectos secundarios, manejo de secretos, puntos de aprobación humana |

> *«A submission can provide more detail, but omitting any of these fields makes
> it difficult to separate model effects from harness effects.»* — Stop Comparing, Tabla 3

**Además se declara** qué capa(s) cambió este arnés respecto al anterior y **por
qué se espera que afecte a estabilidad, deriva o lag de control** — una
diferencia de arnés solo cuenta como *significativa* si cumple eso.

---

## 7. Presupuesto

| parámetro | valor propuesto | estado |
|---|---|---|
| iteraciones | *(a declarar)* | **propuesto** |
| pasos | *(a declarar)* | **propuesto** |
| tiempo | *(a declarar)* | **propuesto** |
| *snapshot* | cada evaluación consume **una** iteración; evalúa **instantánea inmutable**; **máx. 1 evaluación activa** | — |
| presupuesto agotado | se **congela el mejor** y se pasa a `D^eval` | — |

> Regla Evo-Bench: *«Analyze while evaluations run and restore the best revision
> before freezing.»* — **no se congela el último, se congela el mejor.**

**Criterio de la hipótesis:** **una hipótesis falsificable por iteración.**
No se hacen ediciones empaquetadas.

---

## 8. Bases de referencia (fuera del ranking)

| base | papel | `web_development` | `game_development` |
|---|---|---|---|
| **Semilla `H0`** | **suelo absoluto** — qué gana el diseño | *Prueba Gemini* (`c:\EW`) — modelo sin arnés: **69/100, 9/13 checks** | generación sin iteración (`curve[0]`) |
| **Humano** | **techo** — qué queda por ganar | portfolio *Nora Velez* hecho a mano | `workspace/current` **curado a mano** (sprites + mapas + cables) |
| **Arnés de referencia** | **techo ingenieril** | *(a declarar)* | *(a declarar)* |

Sin las dos o tres, «mejoró» no significa nada: mejoró *respecto a qué*.

> ⚠ **Advertencia sobre el techo de juegos:** el `workspace/current` de ReaGame
> está **curado a mano** (los propios `lessons.md` lo etiquetan `[manual]`).
> No es un techo de agente — es un techo humano. **Está bien usarlo como tal,
> pero hay que declararlo como humano, no como agente.**

---

## 9. Protocolo de ejecución

1. **Congelar** todo lo de §3 y **registrar la Harness Card** del brazo.
2. **Fijar presupuesto** (§7) y **semilla**.
3. **Iterar** solo contra `D^val`:
   `diagnosticar → 1 hipótesis falsificable → editar → preflight barato →
   evaluar snapshot inmutable → retener o revertir`
4. **Congelar el mejor**, no el último.
5. **Abrir `D^eval` una sola vez**, sin devolver evidencia.
6. **Reportar** `Overall`, `AnytimeVal`, `RR(k)`, Context Retention, `τ`,
   recursos, y la **Harness Card**.
7. **Declarar** si pasó la **puerta A** (fidelidad) **antes** de leer el resultado de B.

### Prohibiciones
- ✗ Comparar sin Harness Card.
- ✗ Re-bajar cualquier umbral de §5.1.
- ✗ Usar `D^eval` para iterar.
- ✗ Ajustar la API de forma específica de arnés.
- ✗ Atribuir la mejora al modelo (el modelo está fijo).
- ✗ Reportar solo un número de `RR` en vez de la curva.
- ✗ Publicar sin recursos (coste, tokens, tiempo secuencial).

---

## 10. Lo que hay que construir antes de poder medir

| # | pieza | bloquea | estado |
|---|---|---|---|
| 1 | **Re-juzgar a nivel de pregunta** → `m_h(x)` | `Sens(x)` | pendiente |
| 2 | **Construir `H_aux`** y calcular `Sens(x)` | selección de preguntas | pendiente |
| 3 | **Crear `D^eval` por dominio**, congelada y oculta | cualquier resultado de Capa B | **no existe** — ver §10.1 |
| 4 | **Harness Cards** de los 8 brazos + ReaWeb + ReaGame | publicar | pendiente |
| 5 | ~~Especificar el dominio de la Capa B~~ | — | ✅ **resuelto** → §4.0 |
| 6 | **Semilla `H0` y base humana** | interpretabilidad | candidatos → §8 |
| 7 | **Presupuesto** (iter/pasos/tiempo) | el loop | pendiente |
| 8 | **Instrumentar con TraceForge** | `RR(k)`, Context Retention, `τ` | pendiente → §5.4 |
| 9 | **Cerrar el agujero de arquetipos sin `structure`/`verification`** | el cometido es vacío en 37/61 | pendiente |
| 10 | **Construir el scorer de Capa B por ejecución** (juegos: replay de trazas) | `Overall(game_development)` | pendiente → §5.2.1 |
| 11 | **Cerrar la visibilidad del evaluador** — el agente no debe poder leer su rúbrica | rúbrica oculta `ρ` | pendiente → §5.2.1 |

### 10.1 Hallazgo crítico: **no existe ningún `D^eval` en todo el ecosistema**

Revisados `Bibliotecario`, `CogniTeam`, `ReaWeb`, `ReaGame` **y los cuatro papers**:

| | ¿hay `D^val`/`D^eval`? | ¿todo visible? |
|---|---|---|
| Bibliotecario | no | QA iterado contra prompts → contaminado |
| CogniTeam | no — `evals/classification.yaml` (123 casos, solo clasificación) | sí |
| ReaWeb | **no** — 14 tareas fijas en `tasks.yaml`, **inyectadas al prompt** | **sí** |
| ReaGame | **no** — 8 tareas en `game_tasks.yaml`, **inyectadas al prompt** | **sí** |
| **Evo-Bench** | ✅ **`D^val` 160 / `D^eval` 448** | — |
| **Stop Comparing** | ❌ no | — |
| **GameCraft-Bench** | ❌ **no** — solo **rúbrica oculta `ρ`** | — |
| **GameDevBench** | ❌ **no** — solo 117 transcripciones *para sonda de contaminación* | — |

**De los cuatro papers, solo Evo-Bench construye el split.** Los dos de juegos
protegen **qué se juzga dentro de una tarea** (rúbrica oculta / tests ocultos),
no **cómo se protege el set de evaluación**. **Evo-Bench sigue siendo la única
autoridad para §4.1.**

**Y en el ecosistema propio:** el agente puede leer su evaluador, sus reglas y
su suite. La única cosa parecida a un *holdout* es el *gate* `train`/`dev` de
ReaGame — **defaults web heredados de ReaWeb, y nunca usado** (`harness_edits`: 0).

**Traducción:** el criterio central de Evo-Bench (*«evaluation-suite tasks are
unavailable»*) **se cumple en cero proyectos**. Crear `D^eval` no es un detalle:
**es lo primero que hace falta.**

### 10.2 Otros hallazgos que condicionan el diseño

- **Umbrales ya declarados y validados en dominio:** ambos arneses usan **techo
  40** por *gates* P0. En ReaGame se validó empíricamente: **80 → 40** cuando el
  gate detectó un juego sin cablear. **Se mantiene intacto** — ver el reencuadre
  de §5.2.0.
- **La comparabilidad por `task_hash` es frágil:** *ReaGame* demostró que
  quitar los acentos cambia el hash (`4dfaa8fe…` vs `501c8e9b…`) y rompe la
  serie. **Normalizar antes de hashear** — congelado nuevo.
- **ReaGame: 7 de 8 tareas de la suite nunca se han ejecutado** y no existe
  `leaderboard.*`. El runner tiene además `best = last` en vez de `max`.
- **Meta-evolución nunca ha disparado:** `harness_edits = 0` en ReaGame;
  en Bibliotecario `skills = 0`, `memory_items = 0`. **El bucle de mejora
  existe y no se ha ejecutado nunca.**
- **Inversión de prioridades detectada:** GameCraft da **0.35** a *Content Depth*
  y *Art & Presentation* y solo **0.15** a *Core Mechanics* — *«a complete game
  should extend beyond minimal mechanics and functional prototypes»*. El
  evaluador actual de ReaGame hace **lo contrario** (`gameplay 2.0` el más
  pesado). **Declarado, no corregido** — queda a la vista en §5.2.1.
- **Los arquetipos por género tienen respaldo parcial:** GameCraft usa 15
  familias/géneros; GameDevBench dice explícitamente *«there is **no existing
  taxonomy** of game development tasks»* y categoriza por **skill + editor**.
  Nuestros 4 arquetipos son géneros: **con respaldo de GameCraft, sin respaldo
  de GameDevBench.**

---

## 11. Ratificación

Esta especificación **no vale nada hasta que se ratifique**, y una vez ratificada
**no se toca** salvo declarando benchmark nuevo.

> ### Ratificación parcial — 2026-10-14
>
> **Objetivo de esta ratificación: desbloquear la construcción del scorer B-1.**
> Se ratifica el **bloque mínimo coherente** para poder medir con B-1. Todo lo
> demás queda **explícitamente sin ratificar** — no se asume nada por silencio.
>
> | se ratifica | por qué es prerequisito de B-1 |
> |---|---|
> | §5.2.0 reencuadre | B-1 **existe porque** el evaluador estático pasó a A-bis |
> | §5.2.1 fase B-1 | es el objeto de la ratificación |
> | §5.2.1 fórmula | define la forma final — `M_B1` se llena hoy, `D/V/A` esperan a B-2 |
> | §5.2.1 `BUILD = 0` | aplica a B-1: proyecto que no carga → nota 0 |
> | §5.2.1 prohibición A-bis + B | evita que el número final diga dos cosas distintas |
> | §5.2.1 regla B-2 | impide ratificar B-2 sin que B-1 funcione end-to-end |
> | §5.2.1 congelados B-1 | el motor y el comando **ya están medidos**; el conjunto de tests se congela **al escribirse** |
>
> **No se ratifica aún** (y por tanto **no se usa como regla**): §2.1 · §3 ·
> §4.0 · §4.1 · §4.2 · §5.1 · **fase B-2** · §5.4 · §6 · §7 · §8 · §10.3.

| item | propuesto | ratificado |
|---|---|---|
| §2.1 ETCSOVG invariante · arnés por dominio | sí | ☐ *sin ratificar* |
| §3 congelados (incl. **lista de dominios**) | sí | ☐ *sin ratificar* |
| §4.0 dominios: `web_development`, `game_development` | sí | ☐ *sin ratificar* |
| §4.1 partición `D^val`/`D^eval` (autoridad: Evo-Bench) | sí | ☐ *sin ratificar* |
| §4.2 criterio `Sens > 0` | sí | ☐ *sin ratificar* |
| §5.1 umbrales A (intactos Hito 0-2) | sí | ☐ *sin ratificar* |
| **§5.2.0 reencuadre**: techo 40 y pesos → **Capa A-bis**, sin tocarlos | sí | ☑ **2026-10-14** |
| **§5.2.1 scorer Capa B — FASE B-1** (`game_development`) = **tests de comportamiento en Godot** · binario · determinista · **preflight 2026-10-14: 5/5 PASS** | sí | ☑ **2026-10-14** |
| **§5.2.1 scorer Capa B — FASE B-2** (`game_development`) = replay + juez multimodal (GameCraft) | **NO** — bloqueada (`xdotool`, trazas `Π`) | ☐ **dejar en blanco** |
| **§5.2.1 fórmula** `Score = BUILD × (0.15·M_B1 + 0.35·D_B2 + 0.15·V_B2 + 0.35·A_B2)` | sí | ☑ **2026-10-14** |
| **§5.2.1 `BUILD = 0` → nota final = 0** (cero, no techo) | sí | ☑ **2026-10-14** |
| **§5.2.1 prohibición**: no agregar A-bis y B en una nota | sí | ☑ **2026-10-14** |
| **§5.2.1 regla**: B-2 no se ratifica hasta que B-1 funcione end-to-end | sí | ☑ **2026-10-14** |
| **§5.2.1 congelados B-1**: Godot 4.7.1, conjunto de tests, comando de ejecución | sí | ☑ **2026-10-14** |
| §5.4 instrumentación TraceForge obligatoria | sí | ☐ *sin ratificar* |
| §6 Harness Card obligatoria | sí | ☐ *sin ratificar* |
| §8 base semilla `H0` | *(candidatos en §8)* | ☐ *pendiente de valor* |
| §8 base humana | *(candidatos en §8)* | ☐ *pendiente de valor* |
| **§7 presupuesto** | *(pendiente — **GameCraft sugiere 7200 s / 1800 s**)* | ☐ *pendiente de valor* |
| §10.3 `D^eval` por dominio | *(bloqueante nº1)* | ☐ *pendiente de valor* |

### Enmiendas posteriores a la última ratificación

**Ninguna todavía.** *(Cualquier cambio futuro tras ratificar se anota
aquí con fecha y motivo — no se reescribe en silencio.)*

#### Enmienda 1 — *previa a la ratificación* · 2026-10-14

| | |
|---|---|
| **objeto** | §5.2.1 scorer de Capa B (`game_development`) |
| **antes** | *«Camino elegido: GameCraft»* — scorer único con replay + juez multimodal |
| **ahora** | **dos fases** — **B-1** tests de comportamiento en Godot *(determinista, coste 0)* · **B-2** replay + juez multimodal *(GameCraft, bloqueado)* |
| **motivo** | **preflight medido, no supuesto**: Godot 4.7.1 corre headless ✅ · **tests de comportamiento 5/5 PASS** ✅ · `xdotool` ausente ❌ · ReaGame **no emite trazas `Π`** ❌ |
| **qué NO cambia** | los **pesos** `M 0.15 · D 0.35 · V 0.15 · A 0.35` · el **`BUILD = 0 → nota 0`** · la **prohibición de explorar** en el verificador |
| **por qué es correcto** | si B-1 y B-2 se construyeran a la vez **no se podría separar la varianza del juez de la varianza del arnés**. Primero el suelo determinista, después la capa de juicio. |
| **artefacto** | `EG/.tools/godot` 4.7.1 · test `test_behaviour.gd` — **copia temporal, ReaGame no modificado** |
| **ratificación** | **pendiente** — ver §11 |

---

**Umbrales declarados antes de medir. Umbrales nunca re-bajados.**
**Resultado negativo se declara. Errata se declara.**

