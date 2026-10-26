# HITO27 — H26-B Fase 2: transferencia de skills compiladas a B-1 v2

Estado: **CERRADO 2026-10-26 — CUMPLE (instrumento); señal descriptiva, no
significación**. Decisión del dueño 2026-10-25: 4 tareas B-1, techo 100.000
tokens. Es la primera señal de transferencia corpus → arnés; **no** es un test
de significación ni una corrida de arnés completo.

## 1. Objetivo

Medir si el conocimiento ya compilado (`tech_skill_*`) cambia la calidad de un
juego generado, usando el instrumento **B-1 v2** ratificado. El contraste es
`skills` vs `control`, misma tarea, mismo modelo, mismo prompt base y mismo
scorer. El resultado se reporta como **dato descriptivo**: con n=4 no se
declara una diferencia significativa.

## 2. Diseño declarado antes de medir

### 2.1 Tareas (4, elegidas por género, no por nota)

| id | género |
|---|---|
| `card-memory-precision` | Card |
| `platformer-torre-rebote` | Platformer |
| `idle-clicker-fabrica` | Idle |
| `visualnovel-mystery-accusation` | Visual novel |

Son 4 de las 8 tareas de la baseline B-1 v2 de 2026-10-15. Se eligen por
cobertura de género; no se mira su score para elegirlas.

### 2.2 Brazos

- **control**: `PROMPT_SERIE3` + texto de la tarea, sin conocimiento.
- **skills**: el mismo prompt + un bloque fijo con **las 14 skills
  `tech_skill_*`** ordenadas por nombre, en formato compacto: nombre + hasta
  320 caracteres de cada skill. Las skills son principios generales de diseño
  de arneses; no contienen ids de tareas, suites, agujas ni resultados B-1.
  El recorte se declara antes de medir para que prompt + `max_tokens` quepa
  con margen en el TPM 8000; no se recorta después de ver resultados.

El bloque de skills se genera determinísticamente desde `data/bibliotecario.db`
y se registra en el JSON de la corrida. No se usa `search_papers` ni retrieval
por tarea: el tratamiento es el corpus compilado, no una búsqueda distinta por
celda.

### 2.3 Generación y scoring

- Modelo: `openai/gpt-oss-120b` (el de la baseline B-1 v2), vía Groq.
- `max_tokens=6000`; prompt + salida debe caber en el TPM 8000 del tier.
- **1 generación por celda, 0 reparaciones**: 4 tareas × 2 brazos = **8
  llamadas** como máximo.
- `temperature` por defecto del cliente (0.2), igual en ambos brazos.
- Scorer: `evals/preflight/suite_runner_v2.py` sobre el workspace generado
  (`project.godot` + `main.tscn` fijos; el modelo escribe `main.gd`).
- Sin reintentos extra del runner: una respuesta vacía se registra como celda
  fallida, no se reintenta para “arreglarla”.

### 2.4 B-2

**No se ejecuta B-2 H18 en este hito.** B-2 está atado a `platformer-juego` y
a su ρ oculta; no puntúa juegos generados arbitrarios sin una rúbrica nueva.
Usarlo aquí sería cambiar el instrumento, no medir transferencia. B-1 v2 es el
instrumento aplicable a las 4 tareas.

## 3. Presupuesto y tiempo

| concepto | valor |
|---|---:|
| llamadas máximas | 8 |
| tokens estimados | 50.000–80.000 |
| **techo declarado** | **100.000** |
| tiempo estimado de corrida | 35–50 min |
| implementación 0-token | 45–90 min |

La estimación sale de la serie 3 B-1 v2 (10 llamadas, 56.197 tokens, 3.077 s
de `llm_s`) y del cooldown declarado de 70 s. Si el coste medido supera
100.000, se detiene y se declara **NO CUMPLE por techo**; no se amplía a mitad
de corrida.

## 4. Gates

| id | gate | umbral |
|---|---|---|
| **T1** | presupuesto | 8/8 llamadas como máximo; coste ≤100.000 tokens |
| **T2** | generación | 8/8 celdas con `main.gd` parseado |
| **T3** | instrumento | 8/8 suites ejecutadas; `BUILD>0` en ≥6/8 |
| **T4** | no fuga | control sin skills; skills sin ids de tarea/suite/agujas |
| **T5** | encaje TPM | prompt + `max_tokens=6000` < 8.000 tokens en las 8 celdas |
| **T6** | reporte | media por brazo, delta por tarea y `BUILD`; sin afirmar significación con n=4 |

Si T1-T6 fallan, el hito es **NO CUMPLE** y no se publica una conclusión de
transferencia. T6 no exige que `skills` gane: un delta ≤0 es un resultado.

## 5. Fuera de alcance

- Reparaciones, bucle de agente, multi-turno o `coevolve` vivo.
- Cambiar tareas, suites, umbrales, modelo o fórmula de B-1/B-2.
- Editar evidencia H18/H22-H24 o la baseline de 2026-10-15.
- Afirmar que hay transferencia con n=4; esto es un primer corte.

## 6. Cierre — 2026-10-26

| id | medido | veredicto |
|---|---|---|
| **T1** | 8/8 intentos y 8/8 llamadas con usage; **42.710 tokens** ≤100.000 | ✅ |
| **T2** | 8/8 celdas con `main.gd` parseado | ✅ |
| **T3** | 8/8 suites ejecutadas; **BUILD>0=8/8** (≥6) | ✅ |
| **T4** | control sin skills; skills con briefing; sin ids/suite/agujas en el briefing | ✅ |
| **T5** | peor request estimado **7.774 < 8.000** | ✅ |
| **T6** | control **10,22** · skills **30,22** · delta **+20,00**; card +80,00; otras 3 tareas 0,00; n=4 descriptivo | ✅ |

**Veredicto: CUMPLE (instrumento), no “transferencia general”.** El delta
positivo está concentrado en `card-memory-precision` (control 10,0 vs skills
90,0; `sin-errores-de-script` pasa solo en skills). Las otras tres tareas
empatan (5,88 / 12,5 / 12,5) y todas sus celdas fallan
`sin-errores-de-script`, incluida la de skills. Con n=4 y un solo género
afectado no se afirma que las skills transfieran en general; haría falta una
réplica con más tareas/muestras antes de adoptar nada.

- Coste real: **42.710 tokens** (8 llamadas; 0 reparaciones; 0 llamadas extra).
- Tiempo: suma `llm_s` **75 s** + 8 cooldowns de 70 s = **635 s (~10,6 min)**;
  las suites van aparte. La estimación de 35–50 min era conservadora.
- Puerta: suite **574 passed** (288,22 s); ruff limpio; secretos 0 en 1.725
  ficheros; `lint_suites_v2.py` PASSED; `git diff --check` limpio.
- Evidencia: `evals/results/result_transfer_h26b.json`; stdout:
  `evals/logs/h26b_transfer_run.log`.
- B-2 no se ejecutó. No hay commit ni push.
