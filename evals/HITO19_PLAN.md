# HITO 19 — PLAN (declaración): piloto de `Sens(x)` con `H_aux` de juegos

> **DECLARADO 2026-10-22 — PENDIENTE DE RATIFICACIÓN (§1 y §2 en ☐).**
> En este momento el hito tiene **código 0 y generaciones 0**: esto es la
> marca de declaración. El dueño debe ratificar §1 y §2 **antes** de
> implementar y antes de cualquier corrida. §5 (cierre) se escribe al
> terminar.

## §0 — Estado y por qué este hito

H16-H18 cerraron el instrumento **B-2** (híbrido válido, `Score_final`
0.9187, §5 de `HITO18_PLAN.md`). **B-1** ya era válido (scorer v2
ratificado 2026-10-15). Con ambas capas de la scorer Capa B listas, el
**bloqueante nº 1-2 de `BENCHMARK_SPEC.md` §10** queda al descubierto:
no se puede dibujar `D^val`/`D^eval` sin `Sens(x)`, y `Sens(x)` exige
`H_aux` (K arneses de calidad distinta) que **no existe** (§10.2.1,
bloqueante nº 22: *«K arneses auxiliares… hay que generarlos y ejecutar
las 60 tareas contra cada uno»*).

**Qué mide `Sens(x)`** (Evo-Bench §4.2, citado en §4.2 del spec):

```
Sens(x) = corr_pearson( { m_h(x) }_{h ∈ H_aux} , { Q_h^(−x) }_{h ∈ H_aux} )
  m_h(x)   = score de la tarea x bajo el arnés h
  Q_h^(−x) = calidad de h, media leave-one-out sobre todas las tareas salvo x
```

Una tarea **discrimina** si su score correlaciona con la calidad global
del arnés (buena arnés → alta en x; mala arnés → baja en x). **`Sens(x)
≤ 0` → la tarea se descarta** del benchmark: no distingue calidad de
arnés. Es el criterio que separa un split riguroso de uno con apariencia
de riguroso.

**Hechos medidos que hacen este piloto viable** (del propio repo, no
opinión):

- El generador `evals/preflight/measure_b1.py` es un one-shot
  **parametrizable** (modelo, crib, scaffold, `max_tokens`), y esos knobs
  **ya tienen calidad medida**: scaffold serie 2→3 = BUILD global
  **0.00 → 31.40** (`BENCHMARK_SPEC.md` §5.2.2.d); repairs 1 ronda =
  card 10→80 (pero bloqueados por 429 del tier libre).
- **B-1 emite score por tarea** (`res.score = 100·m_pass/m_total`, float,
  en JSON) → es exactamente `m_h(x)`. **No hace falta B-2** para el
  piloto: B-2 solo tiene 1 rúbrica (`platformer-juego`) y cuesta ~38k
  tok/tarea; B-1 es **determinista y 0 tokens de juez**.
- Precedente **H4** (Hito 3 fase 4): A/B con `n=6` y juez ruidoso **NO
  separó** (LOW>FULL invertido, IC cruza 0). Lección aplicada aquí: usar
  score **B-1 determinista** (sin ruido de juez) y declarar **umbrales y
  tamaño de muestra antes de medir**.

**Alcance honesto de este hito**: es un **piloto** que prueba que
`Sens(x)` es calculable y que el mecanismo separa tareas. **NO dibuja el
split final** de las 60 tareas; eso es un hito futuro que exige el
`Sens(x)` completo sobre toda la suite. Este piloto también puede
cerrar **NO CUMPLE** si B-1 no discrimina (resultado negativo válido,
declarado sin tocar umbrales).

## §1 — Diseño propuesto — ☐ pendiente de ratificación

**`m_h(x)` = score B-1 por tarea.** Sin juez. Determinista. `H_aux` = K
variantes del **generador** (`measure_b1.py`), no del scorer (el scorer
B-1 es fijo y congelado).

**Construcción de `H_aux` (K = 5 arneses).** Todos **sin rondas de
reparación** (evitan el 429 del tier libre y la separación la da el
scaffold, no los repairs). Cada arnés **se congela** declarando
`(modelo, crib, scaffold, max_tokens)` antes de correr. Propuesta, con
su calidad a priori:

| arnés | configuración | calidad a priori |
|---|---|---|
| **A1** | sin scaffold (serie 2: el modelo escribe `project.godot`+`main.tscn`+`main.gd`), crib v2 | **baja** — medido ≈ BUILD 0.00 |
| **A2** | scaffold (serie 3: harness fija `project.godot`+`main.tscn`, modelo solo `main.gd`), crib v2 | **media-alta** — medido ≈ 31.40 |
| **A3** | scaffold + crib v2 + modelo `openai/gpt-oss-20b` | exploratoria |
| **A4** | scaffold + crib v2 + modelo `qwen/qwen3.8-27b` | exploratoria |
| **A5** | scaffold + crib **v1** (sin reglas `.tscn`), `max_tokens=6000` | exploratoria (crib/techo menores) |

A1 y A2 anclan los extremos con calidad **ya medida**; A3-A5 añaden
puntos intermedios/dispersos (necesarios para que Pearson tenga
resolución). La separación mínima entre arneses es gate U3.

**Piloto: N = 12 tareas.** Selección **por regla determinista antes de
medir**: tareas con suite B-1 v2 verde (`suites_v2/`), cubriendo ≥ 6
familias GameCraft, elegidas por orden de id (o similar) — la lista
exacta se fija en §1.B en el commit de implementación, antes de
generar. Las 12×5 = **60 generaciones** ≈ 420k tokens de generación +
60 corridas de Godot (0 tokens). Cooldown 70 s del tier libre → ~1-2 h
de pared. Viable.

**Cómputo de `Sens(x)`.** Para cada tarea x de las 12:
1. `m_h(x)` = score B-1 de x bajo cada arnés h (5 valores).
2. `Q_h` = media de `m_h(·)` de h sobre las 12 tareas;
   `Q_h^(−x)` = media de h sobre las **otras 11** (leave-one-out).
3. `Sens(x)` = correlación de Pearson de las 5 parejas
   `(m_h(x), Q_h^(−x))`.
4. Tareas con varianza nula en `m_h(x)` o en `Q_h^(−x)` (todas las
   arneses empatan en x) → `Sens` **no definible** (se reporta como
   tal, no como 0 — un empate no es Sens=0, es Sens sin resolver).

**Lo que este diseño NO hace**: no toca el scorer B-1 (v2 congelado) ni
B-2; no usa juez; no dibuja `D^val`/`D^eval`; no corre las 60 tareas;
no modifica `measure_b1.py` salvo parametrizar sus knobs ya existentes.

## §2 — Umbrales (propuestos — RATIFICAR antes de implementar/medir)

| gate | umbral | por qué / calibración | estado |
|---|---|---|---|
| **U1** `H_aux` construido | K = 5 arneses **congelados** (modelo/crib/scaffold/`max_tokens` declarados por arnés) | sin `H_aux` no hay `Sens` | ☐ |
| **U2** matriz completa | cada arnés corre las N = 12 tareas; `m_h(x)` = score B-1 float; **0 celdas faltantes** | `Sens` exige score por tarea | ☐ |
| **U3** separación de arneses | `spread Q_h = max(Q_h) − min(Q_h) ≥ 15` puntos | si los arneses no difieren, Pearson es ruido; A1≈0 vs A2≈31 lo garantiza a priori | ☐ |
| **U4** `Sens` calculable | `Sens(x)` **finito** en ≥ N/2 = 6 tareas (las de varianza nula se marcan «no definible», no se cuentan como 0) | Pearson exige varianza en ambas series | ☐ |
| **U5** el mecanismo discrimina | ≥ 50% de las tareas (≥ 6/12) con `Sens(x) > 0` | si ninguna tarea discrimina, B-1 no sirve para `Sens` → **NO CUMPLE con evidencia**, sin re-bajar | ☐ |
| **U6** coste y disciplina | umbrales y tamaño **antes** de medir · `corpus_lock` · ruff · sin re-bajar `Sens` ni umbrales tras medir · resultados negativos se declaran | `AGENTS.md` / §0 del spec | ☐ |

**Qué es "CUMPLE"**: U1-U6 todos OK → el piloto prueba que `Sens(x)` es
calculable en juegos con B-1 y que **≥ la mitad de las tareas
discriminan calidad de arnés**. Eso habilita (en un hito futuro) el
`Sens(x)` completo sobre las 60 tareas y el dibujo del split.
**Qué es "NO CUMPLE"**: cualquier gate cae → se cierra con evidencia y
decisión del dueño; los umbrales no se tocan tras medir.

## §3 — Congelados y no congelados

- **Congelados heredados**: scorer **B-1 v2** (`suites_v2/`, `res.score`
  por tarea) · scorer **B-2 híbrido** (H18, intacto) · fórmula
  `Sens(x)` de Evo-Bench §4.2 · `measure_b1.py` como generador (sus
  knobs ya existen; no se reescribe su lógica) · modelo por defecto del
  generador `openai/gpt-oss-120b` · evidencia intocable.
- **Congelados hasta enmienda declarada**: la composición exacta del
  `H_aux` (K, configs) y la lista de las N tareas — ambos se fijan en
  §1.B antes de la primera generación; una vez fijados, no se tocan
  tras medir.
- **No congelado**: el número K (se puede subir a 6 si Sens resulta
  inestable con 5 — se declara, no se mide a ciegas), la elección de
  tareas dentro del criterio, y el detalle del cómputo Pearson.

## §4 — Disciplina (sin medir hasta ratificar)

1. Este plan se commitea **como declaración**: código 0, generaciones 0.
2. **Ratificación del dueño** de §1 y §2 (☐→☑), antes de implementar y
   antes de la primera generación.
3. Solo entonces: §1.B fija `H_aux` y las N tareas → implementación +
   tests puros (matriz `m_h`, `Q_h^(−x)`, Pearson, casos borde) + ruff +
   fila §11 de `BENCHMARK_SPEC.md` → **corrida oficial única** (genera
   `H_aux`×tareas, calcula `Sens`) → §5 con veredicto.
4. Commits en español ASCII sin acentos; clave-scan en cada commit.
5. Si un gate falla → **NO CUMPLE con evidencia y decisión del dueño**;
   umbrales y `Sens` no se tocan tras medir; todo intento fallido se
   documenta con causa y coste.

§5 (cierre) se escribe al cerrar; mientras tanto no existe. Evidencia
previa de referencia: `evals/results/result_fase2_b2_h18.json` (H18
CUMPLE) y las líneas base de scaffold/`measure_b1` en
`BENCHMARK_SPEC.md` §5.2.2.d.
