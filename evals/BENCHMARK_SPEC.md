# Especificación del Benchmark

> **Documento congelado.** Se declara **antes** de medir. Si algo aquí cambia, se
> declara como *benchmark nuevo con línea base nueva* — nunca en silencio, nunca
> mezclando series.
>
> Fundamento: `Documentos/Stop Comparing LLM Agents Without Disclosing the Harness.pdf`
> y `Documentos/EVO-BENCH CAN LANGUAGE MODELS IMPROVE AGENT HARNESS.pdf`.
> **Estado: RATIFICACIÓN PARCIAL — 2026-10-14 · + scorer B-1 v2 — 2026-10-15.**
> Ratificado: **bloque B-1** (§5.2.0, §5.2.1 fase B-1, fórmula, `BUILD=0`,
> prohibición, regla B-2, congelados B-1) **y §8.1 base humana
> `game_development`** (intervalo medido `72.73`–`100.00`); y **scorer B-1 v2**
> (enm. 2 + huecos A/B/C de §5.2.2.b) el **2026-10-15** por decisión del
> dueño — **instrumento B-1 vigente para mediciones nuevas**; v1 queda
> congelado como histórico. **Sin ratificar: todo lo demás**, incluida la
> **fase B-2**. Ver §11.

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

### 4.4 Expansión de la suite — familias, no invención *(2026-10-14)*

**Situación:** la suite de `game_development` tiene **8 tareas** en **4 arquetipos**
(`platformas`, `puzzle`, `arcade`, `rpg-lite`). §10.2 declaró que eso **no soporta
un split `D^val`/`D^eval` con potencia estadística**.

**Eje de expansión: las 15 familias de GameCraft-Bench.** No se inventa una
taxonomía propia — GameCraft las eligió *«to cover distinct game-construction
demands rather than surface genres alone»* y las validó con **140 tareas** y un
**oracle de Godot**.

| familia | GameCraft | ¿cubierto hoy? |
|---|---|---|
| Platformer | 19 | ✅ `platformer-juego`, `platformer-niveles` |
| Puzzle | 8 | ✅ `puzzle-memory`, `puzzle-sliding` |
| Shooter | 7 | ✅ `arcade-shooter`, `arcade-olas` |
| Roguelike | 14 | ~ `rpg-quest`, `rpg-boss` *(género afín, no idéntico)* |
| **Open World** | 15 | ❌ |
| **Strategy** | 17 | ❌ |
| **Tycoon** | 16 | ❌ |
| **Visual novel** | 11 | ❌ |
| **Simulation** | 6 | ❌ |
| **Card game** | 5 | ❌ |
| **Horror** | 5 | ❌ |
| **Rhythm** | 5 | ❌ |
| **Idle** | 4 | ❌ |
| **Racing** | 4 | ❌ |
| **Sports** | 4 | ❌ |

**Reglas de la expansión** (declaradas antes de escribir):

1. **Familias del benchmark ≠ arquetipos de CogniTeam.** Las familias vienen de
   GameCraft (validadas externamente); los arquetipos son la fuente de
   conocimiento del dominio. **No se mezclan.**
2. **Las 8 tareas existentes se conservan intactas** — están congeladas.
3. **Mínimo 3 tareas por familia**, objetivo **4** → **≥56 tareas totales**.
4. **Cada tarea describe experiencia de jugador observable**, no implementación
   — instrucción de GameCraft: *«specifying the intended experience without
   prescribing implementation details»*.
5. **Ninguna tarea contiene checklist de rúbrica** — la rúbrica va aparte
   (§5.2.1 B-2) y **el agente no la ve**.
6. **Dentro de una familia, las tareas se diferencian por mecánica y alcance**,
   no por re-texto. Dos tareas de la misma familia con las mismas mecánicas
   son **redundantes y se descartan**.
7. **`turns: 16` y `target_h: 3`** se mantienen salvo declaración en contrario.
8. **Toda tarea nueva entra como `D^val` hasta que la suite alcance el tamaño
   objetivo**; el reparto `D^val`/`D^eval` se fija **después**, de una vez,
   con la suite completa — nunca tarea a tarea.

> **Umbral de §10.2 reafirmado:** la suite debe llegar a **≥56 tareas** antes
> de diseñar el split. Con 15 familias × 4 = **60**, el objetivo queda cubierto.

#### Resultado medido — 2026-10-14

Las 52 tareas nuevas se escribieron con la división de trabajo en 4 lotes y se
consolidaron en **`evals/game_tasks_expanded.yaml`** (viven en Bibliotecario,
**no** en ReaGame, porque ReaGame no se modifica). Validación automática sobre
el fichero consolidado: 52/52 ids únicos, formato `id`/`family`/`task`/`turns`/
`target_h` correcto, **0 fugas de nombres de nodos o APIs de Godot** en la prosa,
**0 checklists de rúbrica**, y las 52 exigen explícitamente HUD visible +
victoria + derrota/final + reinicio.

| familia | existentes (ReaGame) | nuevas | total |
|---|---|---|---|
| Platformer | 2 | 2 | **4** |
| Puzzle | 2 | 1 | **3** |
| Shooter | 2 | 1 | **3** |
| Roguelike *(=`rpg-quest`,`rpg-boss`)* | 2 | 4 | **6** |
| Open World | 0 | 4 | **4** |
| Strategy | 0 | 4 | **4** |
| Tycoon | 0 | 4 | **4** |
| Visual novel | 0 | 4 | **4** |
| Card game | 0 | 4 | **4** |
| Horror | 0 | 4 | **4** |
| Simulation | 0 | 4 | **4** |
| Rhythm | 0 | 4 | **4** |
| Idle | 0 | 4 | **4** |
| Racing | 0 | 4 | **4** |
| Sports | 0 | 4 | **4** |
| **TOTAL** | **8** | **52** | **60** |

**Umbral ≥56: CUMPLIDO (60).** **Mínimo 3/familia: cumplido en las 15.**

> **Déficit declarado, no maquillado:** el objetivo era 4/familia. **Puzzle=3 y
> Shooter=3** se quedan en el mínimo; no se rellenaron con tareas redundantes
> porque la regla 6 prohinde re-texto. Si más adelante se añade una 4ª tarea
> genuina a cada una, el total sube a 62 — pero **el umbral ≥56 ya está cumplido
> hoy** y el split puede diseñarse con la suite actual.

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

###### 5.2.2 Auditoría de cobertura de B-1 sobre las 15 familias *(2026-10-14 — resultado negativo declarado)*

La suite pasó de 8 a 60 tareas (§4.4), pero **B-1 se escribió para las 8
originales**, que eran todas de plataformas/puzzle/arcade — géneros con un
avatar que se mueve por el espacio. Preguntado si el vocabulario de 13 `kind`s
de `check_suite.gd` puede expresar las condiciones de victoria/derrota/HUD de
las familias nuevas, la respuesta es **no en 31 de las 60 tareas**, y se
declara el resultado negativo en lugar de maquillarlo.

**Los 13 `kind`s, clasificados por lo que realmente verifican:**

| grupo | `kind`s | qué verifican de verdad |
|---|---|---|
| **comportamiento** (5) | `moves` · `jump` · `settles`/`lands` · `falls` · `camera_follows` | que el avatar **responde cinéticamente** al input: desplazamiento, salto, gravedad+colisión, cámara |
| **estructural** (8) | `build` · `node_exists` · `node_is` · `has_method` · `collision` · `canvas` · `label_match` · `scene_count` | que algo **existe** — un nodo con ese nombre, una clase, un método, una capa, un texto estático |

**Hallazgo 1 — victoria, derrota y reinicio jamás se activan, en ninguna de las
60 tareas.** Incluso en las 8 originales ratificadas, la victoria se comprueba
como `node_exists` sobre un nodo **llamado** `Win`/`Victoria`/`Goal`, y el
reinicio como `node_exists` sobre uno llamado `Restart`/`Reiniciar`. Es
**presencia estructural, no comportamiento**: un juego con un nodo vacío llamado
`Win` aprueba el check de victoria sin tener pantalla de victoria. **Ningún
`kind` llega a un estado final ni lo verifica.**

**Hallazgo 2 — el discriminador es si la tarea tiene avatar cinético.** Los 5
`kind`s de comportamiento sólo aplican si el jugador es un cuerpo que se mueve
por el espacio. Donde no lo hay, **toda la verificación colapsa a
`label_match` (texto estático de HUD) + `node_exists`** — que es
el evaluador estático con otro nombre:

| familias con avatar — B-1 aplica *(29 tareas)* | familias sin avatar — B-1 no aplica *(31 tareas)* |
|---|---|
| Platformer 4 · Shooter 3 · Open World 4 · Racing 4 · Sports 4 · Horror 4 · Roguelike 6 | Puzzle 3 · Card game 4 · Visual novel 4 · Idle 4 · Simulation 4 · Rhythm 4 · Strategy 4 · Tycoon 4 |

> **Evidencia de las suites ya ratificadas:** las dos de **puzzle** (originales)
> contienen **cero** `kind`s de comportamiento — son sólo `build` +
> `node_exists` + `label_match` + `canvas`. No es un fallo de las suites
> nuevas; **era el límite ya presente y no declarado.**

**Hallazgo 3 — cuatro capacidades que ningún `kind` puede expresar:**

1. **Transición de estado por acción** — *«jugar una carta reduce el maná»*,
   *«cambiar de turno avanza el contador»*, *«elegir opción abre rama»*.
   `has_method` comprueba que el método **se llama** así, no que **haga** algo.
2. **Acumulación pasiva sin input** — el corazón de **Idle/Simulation**: la
   moneda sube sola. Los 5 `kind`s de comportamiento **todos** exigen
   `Input.action_press`. Ninguno mide un contador creciendo **sin** intervención.
3. **Corrección temporal** — el corazón de **Rhythm**: acertar la nota **en el
   instante** correcto. No existe `kind` que mida sincronía. *(→ cerrado el
   2026-10-15 con `timing_window` — ver §5.2.2.b.)*
4. **Lectura de valor vivo del HUD** — `label_match` comprueba que un `Label`
   **contiene** la palabra `puntos`. No comprueba que el número **cambie** al
   recoger una moneda. Un HUD con `puntos: 0` congelado aprueba.

**Hallazgo 4 — techo de 900 frames ≈ 15 s a 60 fps.** Ninguna condición de
victoria de las 60 tareas es alcanzable en 15 s de input guionizado: piso 10 de
un roguelike, 15 cromos de un mundo abierto, reputación de leyenda en un tycoon.
Aunque se añadiera un `kind` que conduzca a un final, **el techo lo impide**.

> **Consecuencia para la fórmula ratificada:**
> `Score = BUILD × (0.15·M_B1 + …)`. El componente `M_B1` hoy mide
> **solo mecánica cinética**, y para 31 de 60 tareas mide **solo existencia
> estructural**. **No se re-baja ningún umbral**, pero se declara que `M_B1`
> **no es todavía una medida de core mechanics** para la mitad de la suite —
> es un **suelo** que verifica «arranca y hay algo ahí».

> **Qué haría falta para cerrar la brecha** — 5 `kind`s nuevos:
> `hud_value_changes` (valor vivo con delta), `state_after_action`
> (acción → delta de propiedad), `wait_accumulates` (crecimiento sin input),
> `reaches_state` (llegar a final y detectarlo), `restart_resets` (reinicio
> resetea estado). **Pero el motor está congelado en §11**: añadir `kind`s
> exige declarar **versión nueva del benchmark**, que es decisión del dueño —
> **no se hace aquí unilateralmente.**
>
> **HECHO 2026-10-14 (enmienda 2, §11):** el dueño autorizó **A1**. Los 5 `kind`s
> se implementaron en **`check_suite_v2.gd`** (archivo nuevo; v1 intacto) y se
> validaron: v2 separa un fixture cableado de uno roto por **83.33 puntos**, donde
> v1 los puntúa igual. **La brecha queda cerrada para las 60 tareas** — pero v2
> es un benchmark nuevo y su uso en medición real requiere ratificación propia.

###### 5.2.2.b Contraste con la literatura — los 20 `kind`s de v2 (más el gate `build`) frente a las clases de fallo de los 5 papers *(2026-10-15 — se hace ANTES de ratificar v2)*

**Método:** se extraen las clases **enumerables** de fallo/oráculo de los cinco
papers del corpus de dominio (`data/corpora/game_development.db`) y se contrastan
uno a uno con los `kind`s de `check_suite_v2.gd`. Se declara **antes** de
ratificar v2: si la literatura revela un hueco, cerrarlo en v2 todavía no cuesta
versión nueva; después sí. Fuente: los propios textos, con cita corta.

> **Errata de recuento (declarada):** la §5.2.2 y la enm. 2 dijeron
> «13 `kind`s = 8 estructurales + 5 cinéticos». En el código v1 hay **14 ramas
> de dispatch** (8 estructurales incluyendo `build` + 6 cinéticas — `settles` y
> `lands` son dos `kind`s que comparten rama). Los **totales usados para decidir
> (13 y 18) siguen siendo válidos como histórico**: son los *checks* sin
> contar el gate `build` (7 estructurales + 6 cinéticas = 13; + 5 nuevos = 18).
>
> **Segunda errata de recuento (declarada 2026-10-15):** el resumen que seguía
> a esta tabla decía *«6 cubiertas, 5 parciales, 6 sin cubrir»*, pero la
> propia tabla daba **5 / 4 / 8** — el resumen reclasificó dos clases ❌ sin
> que su desglose de los 6 cuadre (ni *balanceo* ni la sincronía rítmica
> aparecen en él). El mensaje de commit de `7e34393` heredó esas cifras y no
> se reescribe. Recuento correcto **previo a A/B: 5 cubiertas, 4 parciales,
> 8 sin cubrir**.
>
> Con **A, B y C cerrados (2026-10-15)** se usarán **22 ramas de dispatch /
> 21 checks + BUILD** (13 + 5 + A + B + C) y el recuento de la tabla pasa a
> **8 cubiertas / 4 parciales / 5 sin cubrir**.

**Tabla clase de fallo → `kind`(s) de v2:**

| clase de fallo / oráculo (fuente) | `kind`(s) de v2 | estado |
|---|---|---|
| Proyecto no arranca / escena no carga (GameCraft: *unlaunchable*) | `build` | ✅ cubierto |
| Controles sin respuesta (GameCraft: *unresponsive controls*) | `state_after_action` | ✅ si la tarea declara el efecto de la acción |
| Colisiones incorrectas (GameCraft: *incorrect collisions*; 2022: *collision issues*) | `collision` · `settles`/`lands` | ✅ cubierto |
| Objetivo inalcanzable / soft-lock (GameCraft: *unreachable objectives*; ICARUS *soft lock*) | `reaches_state` | ✅ alambre — alcanzable con input guionizado, no que una IA sepa ganar |
| Sin feedback en HUD/UI (GameCraft: *missing UI feedback*) | `hud_value_changes` · `label_match` | ✅ cubierto |
| Transición de estado rota (GameCraft: *broken state transitions*) | `state_after_action` | ⚠️ **parcial** — un paso declarado; no secuencias encadenadas |
| Transición ilegal al jugar (SAGE: *illegal state transition*) | `state_after_action` · `restart_resets` | ⚠️ **parcial** — verificamos las transiciones **declaradas en la tarea**; SAGE **explora** para hallar no declaradas (descubrimiento ≠ verificación) |
| **Desbordamiento de recurso** (SAGE: *resource overflow*) | `resource_within_bounds` | ✅ **cerrado 2026-10-15 (A)** — muestrea una propiedad numérica cada frame de física y comprueba `min/max` (cota, no delta); evidencia cita valor, cota y frame. Validado: fixture ok 8/8, roto cae con «COTA EXCEDIDA» |
| Lógica de juego inconsistente (SAGE: *inconsistent game logic*) | `label_match` · `state_after_action` | ⚠️ **parcial** — sólo reglas declaradas en la tarea; reglas generales → invariantes tipo GameRule → futuro |
| Crash en caliente / excepción de runtime (2022: *crash and stuck behaviour*) | `no_runtime_errors` | ✅ **cerrado 2026-10-15 (B)** — **runner-side** (el motor no intercepta sus propios errores): separa estos checks del motor y escanea la salida con el patrón declarado `SCRIPT ERROR:|Failed to load script`; el primer error citado como evidencia. Validado: el fixture roto cae con su propia línea de error |
| Rendimiento/fps (Survey CASE-5 *performance testing*; Riot) | — | ❌ **fuera de medida** — `MAX_FRAMES` 6000 es válvula anti-colgadas, **no** métrica de rendimiento → no-alcance declarado o métrica nueva (decisión) |
| Regresión entre versiones (**SAGE**, paper central) | — | ❌ **fuera de B-1** — B-1 mide una versión; comparar versiones = serie temporal (ámbito `D^eval`/`Sens`) → no-alcance de B-1 |
| Multijugador / red (Survey MEDIA-2: *multiplayer/network testing*) | — | ❌ **no aplicable** — las 60 tareas son single-player 2D |
| Playtesting / fun-factor / UX / legibilidad visual (Survey: *«capturing the fun… is not possible»*; GameCraft Limitations: no mide fun) | — | ❌ **ámbito de B-2** (juez multimodal, bloqueado) — ya declarado |
| Balanceo y exploración (2022: *balancing*, *game exploration*) | — | ❌ **no aplicable** — son tareas del tester, no de verificación de lo pedido |
| Timers encadenados en secuencia (GameRule límite 4: *Timer(a) no encadenable*) | `wait_accumulates` sólo acumulación simple | ⚠️ **parcial** → futuro/B-2 |
| Sincronía rítmica (hallazgo 3 de esta misma sección, familia Rhythm) | `timing_window` | ✅ **cerrado 2026-10-15 (C)** — el motor vigila la llegada de la nota a la línea (`cue_at` + `cue_op`), pulsa dentro (tick siguiente al cruce) y fuera (`+outside` frames): el `watch_label` debe subir con el interior y **no** con el exterior. Validado: ok 9/9; el roto cae con «la ventana no distingue el instante». Sin paper detrás: lo declaró nuestra auditoría |

**Resumen honesto de la tabla (recuento con A/B/C cerrados, 2026-10-15):** de
17 clases contrastadas — **8 cubiertas** (las 5 previas + cota de recurso +
crash en caliente + sincronía rítmica), **4 parciales**, **5 sin cubrir** (2
no-alcance: rendimiento y regresión entre versiones; 2 no-aplicables:
multijugador y balanceo; 1 ámbito B-2: playtesting/UX). **Los tres huecos
quedan cerrados y validados** — los dos con paper detrás (SAGE, Politowski) y
el propio de la auditoría (Rhythm). El recuento previo del resumen (6/5/6)
estaba mal — errata declarada arriba.

> **Estado de la decisión del dueño (2026-10-15):** el dueño autorizó
> **«A y B ahora… después C»** → **los tres huecos cerrados el mismo día**:
> **(A) `resource_within_bounds`**, **(B) `no_runtime_errors`** (runner-side)
> y **(C) `timing_window`** (ventana de sincronía Rhythm), con validación
> medida: ok **9/9 = 100** vs roto **1/9 = 11.11** — los 8 checks del roto
> caen cada uno por su propia razón — y v1 intacto: fixtures **11.11/11.11**,
> ReaGame **72.73**, `git diff` vacío. **No queda ningún hueco abierto en esta
> tabla → **RATIFICADO 2026-10-15** (el dueño: «Ratifica v2»)** — v2 es el
> instrumento B-1 vigente para mediciones nuevas. La ratificación se emite
> una sola vez; cualquier cambio posterior es enmienda nueva con fecha.

###### 5.2.2.c Suites de las 52 tareas reales — escritas desde el texto, ANTES de cualquier generación *(2026-10-15)*

**Método.** Las 8 tareas originales ya tienen suites v1 congeladas que el
runner v2 corre tal cual (`v2-compat.yaml` lo prueba: 4/4). Las **52 tareas
nuevas** (`evals/game_tasks_expanded.yaml`) reciben sus suites en
`evals/preflight/suites_v2/<id>.yaml`, **generadas desde el texto de cada
instrucción copiado verbatim** (el generador lee el propio YAML: cero
transcripción manual) y **antes de existir cualquier generación** — así el
instrumento no puede contaminarse con lo que un agente haya construido. Se
congelan **al escribirse**: cualquier cambio posterior es benchmark nuevo o
enmienda con fecha. El lint commiteado (`evals/preflight/lint_suites_v2.py`)
valida kinds, campos por kind, presupuesto de frames y cobertura; resultado:
**52/52 suites, 551 checks, LINT PASSED** (6–17 checks por suite; presupuesto
por suite ≤ ~600 frames de física, muy por debajo del techo `MAX_FRAMES` 6000).

**Principio de inclusión (GameDevBench §2.2):** un check por cada feature que
el texto declara **explícitamente**; nada inventado; nada adivinado de los
internos del juego. Reparto:

* **Universales (52):** `build`, `hud-visible` (canvas), `victoria-existe` y
  `reinicio-existe` (`node_exists` sobre nombres de final declarados en la
  instrucción «tras cualquier final se puede reiniciar») y
  `sin-errores-de-script` (runner-side, al final).
* **`label_match` (179):** un stem **español del propio texto** por cada ítem
  que la instrucción lista en «el HUD muestra …»; una aguja por check.
  Supuesto operacional heredado de v1: el valor del HUD es **legible en
  texto** (retratos/íconos sin número quedan fuera de medida). Donde la aguja
  lleva acento (`día`, `maná`, `símbol`, `balón`, `héroe`, `pánic`, `daño`,
  `ejércit`) se usa la grafía del texto; las cotas admiten lista de variantes
  (`[dia, día]`).
* **`resource_within_bounds` (28):** sólo cuando la tarea declara un **«N de
  M»** con su etiqueta en el HUD (llaves de 3, cromos de 15, población de 20,
  vida de 30, piso 10, oleadas de 8…). Cotas máximas; umbrales de victoria
  («5000 monedas», «al menos 12 de 15 tiros») **no** son cotas.
* **Cinéticas (46):** sólo donde el texto declara la mecánica — `moves` (22),
  `jump` (4), `falls` (4), `settles` (4), `camera_follows` (3) — con los
  nombres del avatar en `names` para que el motor resuelva el target.
  `node_is CharacterBody2D` (13) sólo en avatares 2D con interacción física
  declarada (caídas, pinchos, balón, esquiva); `collision` (3) verifica que
  el nodo nombrado (pinchos, moto, balón) **es** `CollisionObject2D`.
* **`wait_accumulates` (3):** sólo economía **pasiva desde t=0** (parque,
  zoológico, taberna — «los parroquianos llegan solos»); la idle que exige
  comprar la primera máquina no acumula sin input.

**Exclusiones con motivo (el instrumento existe; lo que no se puede escribir
sin adivinar es lo que se excluye):** `timing_window` — las tareas no
declaran coordenadas de cue (`cue_at`/`axis`); `reaches_state` — la victoria
es inalcanzable con input guionizado en presupuesto (hallazgo 4); 
`restart_resets` — exige reinicio **en caliente** con tecla no declarada
(las tareas sólo piden presencia «tras cualquier final» → `node_exists`);
`hud_value_changes` / `state_after_action` — los pares acción→efecto y su
tecla no están declarados en ningún texto.

**Ajustes de aplicación (4, declarados al escribir):** (1) basketball **sin**
cota de `puntos` — el texto no declara valor por tiro; (2) puzzle-cajas
**sin** cota de `nivel` — el texto dice «al menos 15», cota mínima, no
máxima; (3) strategy-defensa **con** `oleada≤15` y tycoon-colonia **con**
`día≤5` — mismo patrón «N de M» ya aceptado en card-lane y ow-sobreviv;
(4) horror-maze **sin** `node_is` — el texto declara «primera persona», con
lo que una lectura 3D es legítima y el tipo de avatar queda no declarado.

**Supuestos declarados:** corpus 2D (§5.2.2.b: las 60 tareas son
single-player 2D); input por defecto de Godot (flechas = `ui_*`,
`ui_accept` = espacio) salvo que el texto declare otra tecla; agujas en
español porque las tareas están en español.

**Recuento por kind (las 52 reales):** `label_match` 179 · `node_exists`
132 · `build` 52 · `canvas` 52 · `no_runtime_errors` 52 ·
`resource_within_bounds` 28 · `moves` 22 · `node_is` 13 · `falls` 4 ·
`jump` 4 · `settles` 4 · `camera_follows` 3 · `collision` 3 ·
`wait_accumulates` 3. Las 52 suites **se congelan con este lint verde**.

###### 5.2.2.d Protocolo de la PRIMERA medición B-1 v2 — declaración previa *(2026-10-15)*

**Decisión del dueño:** «Medición pequeña declarada». Se declara **ANTES de
correrla** cualquier llamada; los resultados se anotan después, nunca al revés.

| | |
|---|---|
| **qué se mide** | capa **generador + suite**: generación one-shot de juego completo y su puntuación B-1 v2. **NO** es medición de arnés de agente completo (sin turnos, sin memoria, sin meta-evolución) — eso queda para HITO3. |
| **muestra** | **8 de las 52 tareas**, una por familia elegida por **cobertura de kinds**, no por dificultad esperada: `card-memory-precision` (Card: HUD + cota + victoria/reinicio) · `platformer-torre-rebote` (Platformer: avatar + salto + caída + asiento + cámara + colisión) · `idle-clicker-fabrica` (Idle: acumulación pasiva + cota) · `rhythm-note-highway` (Rhythm) · `horror-maze-flashlight` (Horror) · `strategy-defensa-torres` (Strategy: economía + cota) · `shooter-shmup-lateral-jefe` (Shooter: única del género) · `visualnovel-mystery-accusation` (Visual novel). Entre las 8 están los 14 `kind`s reales. |
| **generador** | **una sola llamada** por generación: texto verbatim de la tarea + **crib Godot 4** (abajo) + convención de formato `###FILE: path###`; el generador **NO ve la suite** ni las agujas. Modelo **`openai/gpt-oss-120b`** (Groq, tier libre), `max_tokens=6000` (declarado: adaptado al **TPM 8000** del tier — con 12000 los repairs grandes rebotan con HTTP 413). |
| **reparación** | hasta **2 rondas** por generación: si la suite falla, se reenvía el proyecto actual + la primera línea de evidencia (`[FAIL]` / `SCRIPT ERROR`). Respuesta vacía o 413 → espera de **65 s** (ventana TPM) y **un** reintento; si vuelve vacía, la generación se registra como fallida con su error. Presupuesto máximo: **8 × (1+2) = 24 llamadas LLM**. |
| **scoring** | por **generación**: `Score` del runner (`BUILD × M`, fórmula intacta). Por **tarea**: media de sus generaciones (primario) + máximo (secundario). **Global: media de medias.** Además se reportan: tasa de sintaxis limpia en 1er intento, reparaciones usadas y tokens consumidos. |
| **umbrales** | **sin umbral de aprobación**: esta corrida **fija BASELINE**. Los umbrales de aceptación (R5 ≥10/15, R4 ≥8/15, B5 100%, `BUILD=0→0`) **no se tocan** y no se aplican a esta serie. |
| **crib Godot 4** *(conocimiento de harness, no agujas)* | sin backticks; `@onready`/`@export` (nunca los keywords de Godot 3); enums de alineación = constantes globales `HORIZONTAL_ALIGNMENT_*` / `VERTICAL_ALIGNMENT_*`; señales con `nodo.senal.connect(_metodo)`; sin `yield` (usar `await`); `position` (no `rect_position`); `Label.autowrap_mode` (no el bool `autowrap`); sin funciones nombradas anidadas (usar `var f = func():` o inlinear el `await`); cada `Area2D` necesita `CollisionShape2D` para recibir input. |
| **artefacto** | script one-off `/tmp/opencode/gen/measure_b1.py` + resultados `measure_b1_results.jsonl` (números clave se copian a CONOCIMIENTO al cerrar) |

**Ampliación del crib y serie 2 — 2026-10-15 (declarada tras el resultado parcial de la serie 1, que se PRESERVA):**

**Serie 1, resultado parcial visto antes de ampliar** (no se borra ni se
repite en silencio): 2 de las 8 tareas corridas — `card-memory-precision`
**0.0/0.0/0.0** y `platformer-torre-rebote` **0.0/0.0/0.0**, ambas **BUILD=0**.
Causa común medida: el generador escribe los `.tscn` en **sintaxis Godot 3**
(`margin_*`, `size=` en Control, `extents=`, subrecursos inline
`RectangleShape2D { … }`, y en card además `[ext_resource]` al final del
fichero). El crib declarado cubría GDScript, **no** el formato `.tscn`. La
evidencia de reparación de la serie 1 sólo contenía el `SCRIPT ERROR` (no la
línea `fallan: build`) — errata de implementación corregida en el script
*antes* de la serie 2.

**Ampliación (mismo día, resultados parciales a la vista y declarados):**

| | |
|---|---|
| **qué añade el crib v2** | formato `.tscn` Godot 4: `[ext_resource]` **antes** del primer `[node]`; recursos embebidos en bloque `[sub_resource type="X" id="N"]` con propiedades en líneas siguientes (**nunca** inline `X { … }`); `RectangleShape2D.size=` (**no** `extents=`); Control con anchors/offsets (**no** `margin_*` ni `size=` en Button); Camera2D sin `current=`; `project.godot` con `viewport_width/viewport_height` |
| **qué hace la serie 2** | **repite las MISMAS 8 tareas** con el mismo presupuesto y scoring, en fichero de resultados aparte; la serie 1 permanece en `measure_b1_results.jsonl` como dato declarado. |
| **qué NO cambia** | umbrales, fórmula, suites congeladas, motor, modelo ni `max_tokens`. |

**Serie 2b — ajuste de presupuesto declarado tras la primera tarea de la serie 2** *(2026-10-15)*: `card-memory-precision` (serie 2) devolvió **ficheros incompletos** (`main.gd` truncado: `completion_tokens` = 6000 exactos = tope de `max_tokens`) y los reintentos cayeron en **413 por ventana TPM deslizante** (dos llamadas en el mismo minuto superan el límite de 8000 aunque cada una por sí sola quepa). La serie 2 parcial se preserva en `measure_b1_s2_results.jsonl`. La **serie 2b** repite las 8 tareas con dos y solo dos cambios, ya declarados: **`max_tokens` 6000 → 7000** (request por llamada ≈ 800+7000 < 8000) y **cooldown de 70 s tras CADA llamada LLM** (limpia la ventana deslizante). Todo lo demás idéntico. Resultados en `measure_b1_s2b_results.jsonl`.

**Resultados — BASELINE fijado el 2026-10-15** *(los números se registran aquí después de correr; no se toca nada de lo declarado arriba)*:

| serie | crib | llamadas | generaciones | con BUILD>0 | media global |
|---|---|---|---|---|---|
| 1 (parcial, 2/8 tareas) | GDScript | 6 | 6 | **0** | 0.00 |
| 2 (parcial, 1/8 tarea) | GDScript + `.tscn` v1 | 1 | 2 | **0** | 0.00 |
| **2b (8/8 tareas)** | GDScript + `.tscn` v1 | 18 | 20 | **0** | **0.00** |

- **Global serie 2b por tarea (Score, media/máx):** las 8 tareas = `0.00/0.00`
  (`card-memory-precision` [0,0,0] · `platformer-torre-rebote` [0,0] ·
  `idle-clicker-fabrica` [0] · `rhythm-note-highway` [0,0,0] ·
  `horror-maze-flashlight` [0,0] · `strategy-defensa-torres` [0,0,0] ·
  `shooter-shmup-lateral-jefe` [0,0,0] · `visualnovel-mystery-accusation` [0,0,0]).
- **0 de 28 generaciones** de las tres series cargaron la escena (`BUILD=0` en
  todas). **Causa dominante medida: el `.tscn`**, no el GDScript: cabecera
  `[gd_scene …]` ausente, `[ext_resource]` al final, subrecursos inline de
  Godot 3, `extents=`/`margin_*`/`size=`, referencia a `icon.png` inexistente.
  El GDScript del crib sí hizo efecto: 3/8 tareas sin ningún `SCRIPT ERROR` en
  el 1er intento de la serie 2b.
- **Límites del tier libre confirmados en caliente:** truncado a `max_tokens`
  (6000 y 7000) en proyectos grandes; **413 estructural** en reparaciones de
  proyectos grandes (`prompt + max_tokens > 8000`): `horror` y `platformer`
  no pudieron usar sus 2 reparaciones; 12 reparaciones usadas de 16 posibles
  (presupuesto respetado: 18 llamadas de 24 máximas). Tokens serie 2b:
  **121 569**.
- **Errata de implementación declarada** (no afecta a los `Score` registrados):
  el corte temprano por "PASSED" de la serie 2b miraba `fails` del runner en
  vez de `fallan` — `idle-clicker-fabrica` usó 1 de sus 3 llamadas y la lista
  "sintaxis limpia 1er intento" del agregador usa `fails` como proxy (lectura
  correcta: 3/8 sin `SCRIPT ERROR`, 0/8 con `BUILD`).
- **Qué demuestra la medición:** el **instrumento** ya está validado en juego
  real (smoke 2026-10-15: juego reparado = **10/10**); lo que la baseline
  mide es que **este generador en este tier no produce un juego cargable**.
  Siguiente experimento declarado aparte (no se hace aquí): scaffold de
  `.tscn` mínimo en el harness, o modelo con presupuesto suficiente.

**Serie 3 — scaffold de `.tscn` fijo, declarada ANTES de correrla** *(2026-10-15)*:

| | |
|---|---|
| **hipótesis** | el fallo dominante de la baseline (0/28 con `BUILD>0`) es la escritura de `.tscn` por el modelo, no su capacidad de lógica de juego. Si el harness fija la escena, `BUILD` cruza el cero y las mediciones ganan resolución. |
| **qué cambia el harness** | **el harness escribe** `project.godot` y `main.tscn` (Godot 4 válidos: cabecera `[gd_scene load_steps=2 format=3]`, `[ext_resource]` primero, raíz `Node2D` con script). **El modelo sólo genera `main.gd`**, con `###FILE: main.gd###`, y crea **todo el árbol por código en `_ready()`** — patrón exacto del smoke que ya pasó **10/10**. Criba reducida a GDScript (el crib de `.tscn` ya no aplica). Instrucción explícita declarada: las etiquetas del HUD usan **las palabras en español del propio texto de la tarea** (mismo origen que las agujas de la suite; no se muestra la suite). |
| **qué NO cambia** | 8 mismas tareas · modelo `openai/gpt-oss-120b` · `max_tokens=7000` · cooldown 70 s · presupuesto 1 gen + 2 repairs · scoring y suites idénticos. Sólo se extrae `main.gd` de la respuesta; si el modelo devuelve además escenas, se ignoran. |
| **resultado** | `evals/preflight/results/measure_b1_serie3.jsonl` — se anota aquí al cerrar. |

**Resultados de la serie 3 — 2026-10-15** *(hipótesis del scaffold: CONFIRMADA)*:

| tarea | scores (generaciones reales) | media | máx |
|---|---|---|---|
| `card-memory-precision` | [10.0, 80.0, 80.0] | 56.67 | 80.00 |
| `idle-clicker-fabrica` | [75.0] | 75.00 | 75.00 |
| `platformer-torre-rebote` | [52.94] | 52.94 | 52.94 |
| `visualnovel-mystery-accusation` | [25.0] | 25.00 | 25.00 |
| `rhythm-note-highway` | [12.5] | 12.50 | 12.50 |
| `shooter-shmup-lateral-jefe` | [10.0] | 10.00 | 10.00 |
| `strategy-defensa-torres` | [10.0] | 10.00 | 10.00 |
| `horror-maze-flashlight` | [9.09] | 9.09 | 9.09 |
| **GLOBAL (media de medias)** | | **31.40** | |

- **BUILD>0 en 10/10 generaciones reales** (baseline: 0/28). La causa del
  cero era la escritura de `.tscn`, no la lógica del juego: con la escena
  fija por el harness, el modelo produce juegos que arrancan y corren.
- **Bucle de reparación probado donde el tier lo permitió** (card): evidencia
  del motor devuelta al modelo → **10.0 → 80.0** en una ronda. Los otros 7
  tareas no pudieron usar sus reparaciones: **429 `agotada/sobrecargada` del
  tier libre** abortó las llamadas posteriores (sólo 10 llamadas de las 24
  del presupuesto; 7 registros `respuesta_vacia` preservados pero excluidos
  de las medias — no son generaciones).
- **Observación de instrumento, candidata a enmienda futura (suites intactas):**
  `victoria-existe`/`reinicio-existe` fallan en 7/8 juegos porque los
  generadores crean el botón con **texto** `Reiniciar` / etiqueta `¡Victoria!`
  pero **no asignan el nombre de nodo** (`restart_btn.name` nunca se pone) y
  `node_exists` compara **nombres**. El smoke pasó porque su prompt pedía
  nombres explícitos. Decidir en enmienda si `node_exists` acepta también
  textos de Label/Button — **no se toca ahora**.
  **(Hecho el mismo día: enmienda 4 de §11 — `node_exists` acepta texto de
  Label/Button; fixtures intactas; serie 3 no re-escalada, workspaces de
  `/tmp` perdidos en un borrado total declarado en la enmienda.)**
- **Sintaxis GDScript: 1/8 primeros intentos sin `SCRIPT ERROR`** — el crib
  reducido no basta; los `Score` de 9-25 con error de script muestran que un
  `_ready()` parcial arranca la escena pero no el HUD completo.
- Tokens serie 3: **56 197** en 10 llamadas. Presupuesto: respetado (≤24).

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
| **Semilla `H0`** | **suelo absoluto** — qué gana el diseño | *Prueba Gemini* (`c:\EW`) — modelo sin arnés: **69/100, 9/13 checks** | generación sin iteración (`curve[0]`) — *pendiente* |
| **Humano** | **techo** — qué queda por ganar | portfolio *Nora Velez* hecho a mano | **medido 2026-10-14** — ver §8.1 |
| **Arnés de referencia** | **techo ingenieril** | *(a declarar)* | *(a declarar)* |

Sin las dos o tres, «mejoró» no significa nada: mejoró *respecto a qué*.

### 8.1 Base humana de `game_development` — **medida, no estimada**

Medida el **2026-10-14** bajo la spec ratificada (fase **B-1**), suite
`platformer-juego`, contra `workspace/current` de ReaGame — que los propios
`lessons.md` etiquetan `[manual]`. **Es techo humano, no de agente.**

| escena | M | Score | qué representa |
|---|---|---|---|
| `res://levels/mision1.tscn` | **11/11** | **100.00** | nivel completo y funcionando |
| `res://main.tscn` | **8/11** | **72.73** | la escena que el proyecto **declara como punto de entrada** |

> **La base humana no es un número: es un intervalo.**
> `100.00` = lo que cuesta el arnés humano cuando el juego se juega.
> `72.73` = lo que cuesta cuando **el punto de entrada está mal** — mismo
> código, misma arquitectura, distinta escena de arranque.
>
> **Ambos son referencia legítima**, y declarar sólo el 100 ocultaría que un
> humano también se equivoca en la parte que el `grep` no ve.

**Los 27 puntos de diferencia son enteramente del punto de entrada.** Eso es
la evidencia medida de que **Capa A-bis y Capa B son constructos distintos**:
el evaluador estático aprueba ambas escenas por igual; el scorer de ejecución
las separa en 27 puntos.

**Cómo se usa:** toda generación futura se reporta **relativa a este intervalo**.
Un resultado por debajo de `72.73` está por debajo de un humano con el punto de
entrada roto. Uno por encima de `100.00` habría que revisarlo — o es real, o el
scorer falla.

> ⚠ **Reproducibilidad:** estas medidas salieron de `EG/.tools/godot` **4.7.1**
> contra `workspace/current` **en la fecha indicada**. Si el workspace cambia,
> **la base se re-mide y se anota**, no se reutiliza el número viejo.

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
| 3 | ~~**Crear `D^eval` por dominio**~~ → **ampliar la suite de tareas** hasta tamaño que soporte el split, y *después* partir | cualquier resultado **definitivo** de Capa B | **reencuadrado** → §10.2 — *bloqueado por tareas, no por diseño* |
| 4 | **Harness Cards** de los 8 brazos + ReaWeb + ReaGame | publicar | pendiente |
| 5 | ~~Especificar el dominio de la Capa B~~ | — | ✅ **resuelto** → §4.0 |
| 6 | **Semilla `H0` y base humana** | interpretabilidad | ✅ **base humana medida** `game_development` → §8.1 · *`H0` y `web_development` pendientes* |
| 7 | **Presupuesto** (iter/pasos/tiempo) | el loop | pendiente |
| 8 | **Instrumentar con TraceForge** | `RR(k)`, Context Retention, `τ` | pendiente → §5.4 |
| 9 | **Cerrar el agujero de arquetipos sin `structure`/`verification`** | el cometido es vacío en 37/61 | pendiente |
| 10 | ~~**Construir el scorer de Capa B por ejecución**~~ | `Overall(game_development)` | ✅ **Fase B-1 construida y validada** → §5.2.1 · *B-2 bloqueada* |
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

### 10.2 Pero `D^eval` está bloqueada por TAREAS, no por diseño *(2026-10-14)*

El bloqueante anterior se enunció como *«no existe `D^eval`»* — como si faltara
escribir el split. **No es así.** Mirados los tamaños de suite:

| benchmark | tareas | `D^val` / `D^eval` | tareas de eval por split |
|---|---|---|---|
| **Evo-Bench** | 608 | 160 / 448 | **448** |
| **GameCraft-Bench** | 140 | *(no tiene split)* | — |
| **GameDevBench** | 333 | *(no tiene split)* | — |
| **ReaGame** | **8** | — | **~2** si se parte 6/2 |

> **Con 8 tareas, un split `D^val`/`D^eval` deja ~2 tareas de evaluación.**
> Eso **no tiene potencia estadística**: un solo fallo mueve la nota 50 puntos,
> y la varianza entre runs dominaría cualquier señal de mejora real.
>
> **Escribir `D^eval` sobre 8 tareas produciría la *apariencia* de un split
> riguroso con un dato que no lo es.** Eso es peor que no tenerlo, porque
> habilitaría conclusiones inválidas con forma de resultado.

**Por lo tanto, reencuadre del bloqueante nº 3:**

| antes | ahora |
|---|---|
| *«Crear `D^eval` por dominio, congelada y oculta»* | ***Ampliar la suite de tareas de `game_development` hasta un tamaño que soporte un split con potencia, y DESPUÉS partir `D^val`/`D^eval`.*** |

**Umbral declarado antes de diseñar el split:** el tamaño mínimo de la suite
se fija **antes** de elegir el reparto — no al revés. Criterio de referencia:
Evo-Bench usa **~2.8 tareas de eval por cada una de val** (448/160). Con ese
ratio, un split con **≥20 tareas de `D^eval`** exigiría **≥56 tareas totales**.

> **Esto no es una excusa para no medir.** B-1 ya funciona y ya mide contra la
> base humana de §8.1. Lo que **no** se puede es *reportar un resultado de
> Capa B como definitivo* hasta que la suite soporte el split.

#### 10.2.1 El umbral se cumplió, pero el split aún no se puede dibujar — depende de `Sens(x)`, no de una decisión *(2026-10-14)*

§4.4 amplió la suite a **60 tareas** y el umbral ≥56 quedó **cumplido**. Eso
levanta el bloqueante *«faltan tareas»*, pero **no** habilita a dibujar el split
todavía — y la razón hay que leerla en Evo-Bench, no inventarla.

**Cómo construye Evo-Bench su split realmente** (§4.2 y §5 del paper):

1. `Sens(x)` = correlación de Pearson entre la puntuación de la tarea bajo cada
   arnés auxiliar `{m_h(x)}` y la calidad global del arnés `Q_h^(−x)`
   (media *leave-one-task-out* sobre todas las tareas salvo `x`).
2. **Se eliminan las tareas con `Sens(x) ≤ 0`** — no distinguen calidad de arnés.
3. Difficulty = `1 − Perf(x)`; se estratifica por difficulty y se selecciona la
   mayor `Sens` dentro de cada estrato.
4. El reparto val/eval es aleatorio **dentro de cada estrato**, de modo que las
   dos mitades comparten la distribución de difficulty.

**Es un procedimiento calculado, no una decisión de diseño.** Un split fiel a
Evo-Bench exige:

| requisito | ¿lo tenemos en juegos? |
|---|---|
| puntuación **por tarea** (no agregada) | ✅ **Sí** — B-1 emite `res.score = 100·m_pass/m_total`, float por tarea, en JSON (`evals/preflight/suite_runner.py`) |
| **K arneses auxiliares** distintos evaluados sobre el pool | ❌ **No** — no existe ninguno; hay que generarlos y ejecutar las 60 tareas contra cada uno |

> **Corrección del bloqueante nº 2:** *«`Sens(x)` no se puede calcular — no hay
> score por pregunta»* era cierto para el brazo **R4/Q1**, que guardaba `r4_ok`
> booleano agregado. **Para juegos no aplica**: B-1 sí produce puntuación numérica
> por tarea. Lo que falta para `Sens(x)` en juegos son los **K arneses auxiliares**,
> no el score.

> **Por lo tanto el split fiel a Evo-Bench está bloqueado por COSTE**, en la misma
> decisión que el bloqueante nº 17: generar arneses auxiliares y correr 60 tareas
> por arnés a `target_h: 3` consume las claves del dueño del proyecto.

**Lo que sí se puede dibujar hoy** es un reparto estratificado por familia
(determinista, sin `Sens`). Pero **no es el split de Evo-Bench** y se declara
como **placeholder**: no puede eliminar tareas con `Sens ≤ 0`, que es justo lo
que da potencia al split real. Si se dibuja, debe **reemplazarse** — no
*refinarse* — cuando `Sens(x)` sea calculable, porque el conjunto de tareas
elegibles cambia.

> **Regla derivada:** nunca reportar un número de `D^eval` como «split
> Evo-Bench» salvo que `Sens(x)` se haya calculado y las tareas con `Sens ≤ 0`
> se hayan excluido de hecho. Un split aleatorio etiquetado como Evo-Bench
> sería **falsa atribución de método**.


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
> §4.0 · §4.1 · §4.2 · §5.1 · §5.4 · §6 · §7 ·
> §8 parcialmente *(**base humana `game_development` SÍ medida y ratificada**;
> `H0` y `web_development` siguen sin valor)* · §10.3.

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
| **§5.2.1 scorer Capa B — FASE B-2** (`game_development`) = replay + juez multimodal (GameCraft) | sí | ☑ **2026-10-21** — *bloqueo resuelto en Hito 15 (`xdotool`, trazas `Π`); ratificación del dueño junto con §2-§3 de `HITO16_PLAN.md`, **antes de la corrida oficial** · **corrida oficial 2026-10-22 → NO CUMPLE** (U1/U3/U5/U6 ✅; **U2 ❌** juez caucho sobre negro puro 0.7762; **U4 ❌** default−idle = 0.0) — umbrales intactos, evidencia y verificación del instrumento en `evals/HITO16_PLAN.md` §5* |
| **§5.2.1 fórmula** `Score = BUILD × (0.15·M_B1 + 0.35·D_B2 + 0.15·V_B2 + 0.35·A_B2)` | sí | ☑ **2026-10-14** |
| **§5.2.1 `BUILD = 0` → nota final = 0** (cero, no techo) | sí | ☑ **2026-10-14** |
| **§5.2.1 prohibición**: no agregar A-bis y B en una nota | sí | ☑ **2026-10-14** |
| **§5.2.1 regla**: B-2 no se ratifica hasta que B-1 funcione end-to-end | sí | ☑ **2026-10-14** |
| **§5.2.1 congelados B-1**: Godot 4.7.1, conjunto de tests, comando de ejecución | sí | ☑ **2026-10-14** — *v1 intacto; v2 añadido como benchmark nuevo (enm. 2)* |
| **§11 enm. 2 — scorer B-1 v2** (`check_suite_v2.gd` · `suite_runner_v2.py` · 21 `kind`s + gate · huecos A/B/C cerrados · validación **9/9 vs 1/9**) | sí | ☑ **2026-10-15** — *decisión del dueño: «Ratifica v2»* |
| §5.4 instrumentación TraceForge obligatoria | sí | ☐ *sin ratificar* |
| §6 Harness Card obligatoria | sí | ☐ *sin ratificar* |
| §8 base semilla `H0` | *(candidatos en §8)* | ☐ *pendiente de valor* |
| §8 base humana **`game_development`** = intervalo **`72.73`–`100.00`** medido 2026-10-14 | sí — **medido** | ☑ **2026-10-14** |
| §8 base humana **`web_development`** | *(portfolio Nora Velez — sin medir)* | ☐ *pendiente de medida* |
| **§7 presupuesto** | *(pendiente — **GameCraft sugiere 7200 s / 1800 s**)* | ☐ *pendiente de valor* |
| §10.3 `D^eval` por dominio | *(bloqueante nº1)* | ☐ *pendiente de valor* |

### Enmiendas posteriores a la última ratificación

**Última ratificación: 2026-10-15 — scorer B-1 v2 (enm. 2 + ampliación
A/B/C). Tras ella: enmienda 3 (2026-10-15, bugfix de timing de los checks
estáticos tras el primer smoke) y enmienda 4 (2026-10-15, `node_exists`
admite texto de UI) — ambas sin cambio de kinds ni umbrales.** Las enmiendas
1 y 2 figuran abajo como registro previo a esa ratificación.
*(Cualquier cambio futuro tras ratificar se anota aquí con fecha y motivo —
no se reescribe en silencio.)*

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

#### Enmienda 2 — *B-1 v2: se cierra la brecha de §5.2.2 con 5 `kind`s nuevos* · 2026-10-14

| | |
|---|---|
| **objeto** | motor B-1 (`check_suite.gd`) — **versión nueva del benchmark**, no enmienda del congelado |
| **antes (v1)** | 13 `kind`s: 8 estructurales + 5 cinéticos. **31 de 60 tareas** quedaban sin cobertura de comportamiento (§5.2.2). Victoria/derrota/reinicio sólo se comprobaban como `node_exists` sobre un nodo *llamado* Win/Restart. *(Errata declarada 2026-10-15: el reparto correcto es **7 estructurales + 6 cinéticos + `build` como gate** — `settles` y `lands` son dos `kind`s; los **totales 13/18 y las decisiones tomadas no cambian**. Ver §5.2.2.b.)* |
| **ahora (v2)** | **21 `kind`s** = los 13 de v1 **+ 5 nuevos** (`hud_value_changes` · `state_after_action` · `wait_accumulates` · `reaches_state` · `restart_resets`) **+ 3 cerrados tras el contraste de §5.2.2.b** (`resource_within_bounds`, `no_runtime_errors`, `timing_window` — ver ampliación abajo). v2 observa **cambios en el tiempo**, no sólo existencia. |
| **qué NO cambia** | **v1 queda intacto y runnable** (`check_suite.gd` + `suite_runner.py` sin tocar — `git diff` vacío). El motor de v2 es un **archivo nuevo** `check_suite_v2.gd`. Godot sigue siendo **4.7.1**. La fórmula, `BUILD=0` y los pesos son idénticos. |
| **motivo** | §5.2.2 declaró, tras auditar las 15 familias, que B-1 **no cubría 31 de 60 tareas**: los 5 `kind`s cinéticos sólo aplican a avatares que se mueven por el espacio, y en Card/Idle/Rhythm/VN/Strategy/Tycoon/Simulation/Puzzle la verificación colapsaba al evaluador estático. Se pidió explícitamente al dueño y autorizó **A1**. |
| **validación medida** *(no supuesta)* | dos fixtures sintéticos idénticos en estructura, uno cableado (`v2_ok`) y uno sin cablear (`v2_broken`): **v1 los puntúa IGUAL (11.11 vs 11.11)** — no distingue. **v2 los separa 83.33 puntos** (ok **100.00** vs roto **16.67**), y los 5 `kind`s nuevos **fallan en el roto cada uno por su razón** (HUD congelado · propiedad sin cambiar · sin acumulación pasiva · sin indicador de final visible · sin reset). |
| **compatibilidad** | v2 ejecuta los `kind`s de v1 sin cambios — suite `v2-compat` = **4/4 PASS** (moves, settles, camera_follows). |
| **arreglo de fondo** | al construir v2 aparecieron dos fallos reales del diseño v1, corregidos y declarados: (1) `frames` contaba iteraciones de `_process`, que en headless **desincronizan** de los ticks de física — el juego sólo avanza en física, así que v2 ata el progreso del check a `Engine.get_physics_frames()`; (2) el target se resolvía en `_initialize`, antes de que `_ready()` creara los nodos por script — v2 lo resuelve en `frames==1`, robusto tanto a nodos en `.tscn` como creados por script. |
| **límite declarado** | `MAX_FRAMES` sube de 900 a **6000** como **válvula de seguridad contra colgadas** (no es presupuesto científico; el presupuesto real va en el `frames:` de cada check). |
| **artefactos** | `evals/preflight/check_suite_v2.gd` · `suite_runner_v2.py` · `suites_v2/v2-fixture.yaml` · `suites_v2/v2-compat.yaml` · `fixtures/v2_ok/` · `fixtures/v2_broken/` |
| **ratificación** | ☑ **RATIFICADO 2026-10-15** — decisión del dueño («Ratifica v2») tras el contraste §5.2.2.b **sin huecos abiertos** y la validación completa (ok **9/9** vs roto **1/9**, compat **4/4**, v1 intacto **11.11/11.11** y ReaGame **72.73** con `git diff` vacío). **v2 es el instrumento B-1 vigente para mediciones nuevas; v1 queda congelado como histórico** — nunca se mezclan (regla de arriba). Cualquier cambio posterior → enmienda nueva con fecha. |

> **Regla derivada de la enmienda 2:** `M_B1` **v1** mide cinemática + existencia
> (suelo). `M_B1` **v2** añade observación de cambios (HUD vivo, acumulación
> pasiva, final alcanzable, reinicio efectivo). **Nunca se mezclan números v1 y
> v2 en una misma serie** — son instrumentos distintos, como declaró la enmienda 1
> para B-1/B-2. Un resultado v1 y un resultado v2 no son comparables.

#### Ampliación pre-ratificación — A, B y C cerrados en v2 · 2026-10-15

| | |
|---|---|
| **objeto** | §5.2.2.b — los dos huecos con paper detrás, **antes** de ratificar v2 |
| **qué se añade** | **(A)** `resource_within_bounds` — cota `min/max` muestreada **por frame de física** en el motor (SAGE *resource overflow*). **(B)** `no_runtime_errors` — **runner-side**: el motor GDScript no puede interceptar sus propios errores en caliente, así que `suite_runner_v2.py` separa estos checks del motor, escanea la salida combinada con el patrón **declarado** `SCRIPT ERROR:|Failed to load script` y sintetiza el resultado citando la primera línea como evidencia; si hay coincidencia la validación entera queda `FAILED`. **(C)** `timing_window` — corrección temporal (familia Rhythm): arma en la nota, detecta el cruce de `cue_at`, pulsa **dentro** (tick siguiente) y **fuera** (`+outside`); exige que `watch_label` suba con el interior y **no** con el exterior |
| **validación medida** | fixtures ok/roto con la suite final de 9 checks: **ok 9/9 = 100.0** · **roto 1/9 = 11.11** — los 8 checks caen cada uno por su razón (HUD congelado · propiedad sin cambiar · sin acumulación · sin final visible · sin reset · «COTA EXCEDIDA: 497.0 fuera de [-inf, 10]» · «pulsé FUERA de la ventana (+20 frames) y 'puntos' SUBIÓ: 10.0 → 20.0 — la ventana no distingue el instante» · «primer error de script: SCRIPT ERROR: Invalid call…»). `v2-compat` **4/4** · **v1 intacto** en fixtures **1/9 = 11.11** en ambos (sigue sin distinguir) · **v1 en ReaGame 72.73** con `git diff` vacío |
| **qué NO cambia** | v1 congelado (ficheros v1 con `git diff` vacío), Godot 4.7.1, la fórmula, `BUILD=0`, los pesos, `MAX_FRAMES` 6000 y los umbrales. Sólo crece el recuento: **22 ramas / 21 checks + BUILD** |
| **ratificación** | ☑ **RATIFICADO 2026-10-15** — el dueño emitió «Ratifica v2» tras cerrar C: sin huecos abiertos en §5.2.2.b; v2 vigente para medición nueva (una sola vez; cambios posteriores → enmienda) |

#### Observación de instrumento — v1 no es reproducible bajo carga · 2026-10-15

**Hecho medido, sin tocar nada congelado:** hoy se corrió `platformer-juego`
(v1) sobre ReaGame **19 veces**: **14 dieron 8/11 = 72.73** (el baseline
ratificado) y **5 dieron 9/11 = 81.82**. En un experimento controlado, con 8
bucles de CPU pesando la máquina dio **9/11 las 2/2**, y en reposo **8/11 las
12/12** siguientes. El check que voltea es **`jugador-salta`** (los otros 10
son estables; `meta-existe` y `monedas-existen` fallan siempre: es el
`main.tscn` roto del bloqueante 18).

**Causa raíz (ya declarada en la enm. 2):** v1 ata `frames` a iteraciones de
`_process`, que en headless corren sin techo y se desincronizan de los ticks
de física — la ventana de 30 frames del check de salto no siempre abarca el
arco del salto. Es exactamente el defecto que el arreglo de fondo de v2 (ata
el progreso a `Engine.get_physics_frames()`) corrigió.

**Qué NO cambia:** v1 no se modifica (`git diff` vacío), no se re-baja ningún
umbral, y **ambos valores caen dentro del intervalo ratificado §8.1
[72.73, 100.00]**. Se declara para que nadie trate un 8/11 y un 9/11 de v1
como comparables entre sí ni entre sesiones: **un solo número de v1 no es
reproducible sin controlar la carga de la máquina; el baseline sigue siendo
72.73 (medido en reposo)**.

> **Regla derivada de la observación:** toda medición v1 se declara con el
> estado de carga de la máquina; las comparaciones serias de v1 usan la misma
> condición. V2 ya no depende de esto para su progreso (ligado a física), y su
> fixture de validación hoy corre estable.

#### Enmienda 3 — *bugfix tras el primer smoke B-1 end-to-end: los estáticos corrían antes de `_ready()`* · 2026-10-15

| | |
|---|---|
| **objeto** | motor B-1 v2 (`check_suite_v2.gd`) — **bugfix de timing; sin cambio de kinds, sin cambio de umbrales, sin tocar suites congeladas** |
| **antes** | los `kind`s estáticos (`node_exists`, `canvas`, `label_match`, …) se ejecutaban en `_initialize()`, el mismo frame del `instantiate()`. Con fixtures **estructurales** (nodos declarados en `.tscn`) eso basta; con juegos **generados por código** —que crean su árbol en `_ready()`— los estáticos veían una escena vacía y emitían **falsos FAIL** (sin CanvasLayer · ningún Label · Victoria/Restart no encontrados). La fase de comportamiento ya estaba blindada (`frames==1`, arreglo de fondo de la enm. 2); los estáticos no. |
| **ahora** | los estáticos se ejecutan en el **primer frame de física** — misma convención `frames==1` ya ratificada para `_resolve_target`—, con `_ready()` corrido. |
| **motivo (medido, no supuesto)** | **smoke B-1 end-to-end 2026-10-15**: primera generación real (`card-memory-precision` · `openai/gpt-oss-120b`) cuyo `_ready()` crea HUD (`CanvasLayer` + Labels `Tiempo:`/`Parejas: 0/8`/`Intentos:`/`Combo:`) y pantallas `Victoria`/`GameOver`/`Restart`. Con el motor previo ese juego —ya sin errores de script— marcaba **1/10** (sólo build + cota + sin_errores, los tres que no dependen del árbol creado en `_ready`); tras el fix, **el mismo juego = 10/10 PASSED**. Regresión de fixtures: `v2-fixture` **9/9** · `v2-compat` **4/4** (ambas PASSED). |
| **qué NO cambia** | kinds, umbrales, fórmula, `BUILD=0`, pesos, `MAX_FRAMES`, suites congeladas y v1 intacto. La enmienda **no re-baja ningún umbral**: corrige un falso negativo del instrumento que habría castigado juegos correctos. |
| **artefacto** | `evals/preflight/check_suite_v2.gd` — `statics_pending` + `_run_statics()` invocados desde `_process` en el primer tick de física |

#### Enmienda 4 — *`node_exists` admite también el texto de UI (Label/Button)* · 2026-10-15

| | |
|---|---|
| **objeto** | `check_suite_v2.gd` — rama `node_exists` (fallback por texto). **Sin cambio de kinds, sin cambio de umbrales, sin tocar suites congeladas.** |
| **antes** | `node_exists` sólo comparaba **nombres de nodo** (igualdad/contención, case-insensitive). Los generadores crean las pantallas finales con **texto** y sin asignar `name` (p. ej. `restart_btn.text = "Reiniciar"`) — en la serie 3, `victoria-existe`/`reinicio-existe` fallaron en **7 de 8** juegos que sí presentaban esos elementos (hallazgo 25). Ninguna tarea del corpus pide nombres concretos de nodo. |
| **ahora** | si **ningún nombre** coincide, se busca además el **texto** de `Label` y `Button` en todo el árbol (case-insensitive; **sin** requisito de visibilidad: la pantalla de victoria suele estar `visible=false` hasta ganar). La evidencia declara por dónde pasó: `texto: '¡Victoria!'`. Sólo `node_exists`: `node_is`, `collision`, `has_method` y los destinos de los checks de movimiento siguen **sólo por nombre**, y `player` sólo se asigna por nombre. |
| **motivo (medido)** | grep directo sobre generados de la serie 3: texto `Reiniciar`/`¡Victoria!` presente, nombre de nodo sin asignar → falso fail sistemático que castigaba juegos que cumplían la tarea pedida. |
| **validación medida** | fixtures de ratificación **intactas**: `v2-fixture` ok **9/9** · roto **1/9** · `v2-compat` **4/4** (idénticos a §11 enm. 2). Micro-juego sintético con **sólo texto** y ningún nombre relevante: `victoria` **PASS** (`texto: '¡Victoria!'`) · `reinicio` **PASS** (`texto: 'Reiniciar'`) · `avatar` ausente sigue **FAIL** — el fallback no inventa nodos inexistentes. |
| **qué NO cambia** | recuento de kinds (**21 + BUILD**), umbrales, fórmula, `BUILD=0`, suites (los YAML no se tocan), v1 intacto. **Los scores de la serie 3 no se re-escalaron**: los workspaces se perdieron con un borrado total de `/tmp` (declarado aquí); las cifras de §5.2.2.d siguen siendo las medidas con la enmienda 3. |
| **artefacto** | `evals/preflight/check_suite_v2.gd` — rama `node_exists` + `_find_ui_text()` |

---

**Umbrales declarados antes de medir. Umbrales nunca re-bajados.**
**Resultado negativo se declara. Errata se declara.**

