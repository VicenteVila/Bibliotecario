# HITO25 — auditoría del instrumento SD y decisión (0 tokens)

Estado: **CERRADO 2026-10-25 — AUDITORÍA COMPLETA; NO HAY CONSTRUCTO LIMPIO**.
**Decisión del dueño 2026-10-25: H26-B ratificada** (§9): B-1/B-2 como
benchmark válido + producto; H26-A queda descartada salvo nueva decisión.
Este hito no mide arneses ni lanza LLM: audita H22-H24 y recomienda si la
línea SD debe repararse o cerrarse.

## 1. Objetivo

Explicar por qué H22, H23 y H24 cerraron **NO CUMPLE** y separar tres cosas
que los cierres mezclan:

1. capacidad del arnés;
2. límites del canal de salida (tokens/completion);
3. defectos del instrumento (caps, gates, QA y presupuesto).

Salida: una recomendación con evidencia, sin reabrir H22-H24, sin editar su
evidencia y sin construir SD-5.

## 2. Alcance y disciplina

- **0 tokens LLM**. Solo lectura de planes, `result_*.json`, logs y trazas
  SQLite; análisis con `.venv/bin/python`.
- No se editan fixtures, locks, umbrales ni evidencia de H22/H23/H24.
- No se re-puntúa H24: su veredicto **NO CUMPLE** queda intacto. Los defectos
  de gate se documentan para H26, no para cambiar el pasado.
- No se construyen tareas nuevas ni se reanuda ningún probe.
- No se toca `Respuesta.txt` ni `D "Solucion idempotencia.txt"`.
- No hay commit en este hito salvo petición del dueño.

## 3. Evidencia auditada

| hito | diseño | celdas | coste | gates | cierre |
|---|---|---:|---:|---|---|
| H22 SD-2 | 12 dev + 12 test; calibración dev | 9/24 | 213.859 | C1 parcial, **C2 ❌**, C3 parcial, C4 ✅ | NO CUMPLE; oficial no lanzado |
| H23 SD-3 | probe breadth/runtime/contract | 6/6 | 194.453 | P1 ✅, **P2 ❌**, **P3 ❌**, P4 ✅, P5 ✅ | NO CUMPLE |
| H24 SD-4 | probe cola larga tail-2/4/24 | 5/6 | 290.185 | **R1-R6 ❌** | NO CUMPLE |

Contexto: H18 (2026-10-22) fue el último **CUMPLE**. Desde H19, la línea de
benchmark acumula **≈9,8M tokens** y seis cierres NO CUMPLE; SD-2/SD-3/SD-4
suman **698.497 tokens** y ningún constructo limpio.

### 3.1 H22 — saturación del one-shot

- A1 midió **100 en 5/5** celdas (inventory F1/F2/F3 y reservations F1/F2).
- C2 exigía `A1 < 100` en ≥8/12; con 5 ceros ya era **imposible** (máximo
  7/12). El runner paró a las 9/24 celdas.
- A5: 76,4706 / 100 / 100 / 50. C3 parcial: media 81,6176, A1−A5 18,3824.
- QA de BUILD 24/24 y lock correctos: el problema no fue la construcción,
  sino que las tareas no tenían headroom para A1.

### 3.2 H23 — dos extremos sin punto medio

- P2 ❌: media A1 **66,67**, solo **1/3** con A1 < 100.
- P3 ❌: media A5 **96,67**, solo **1/3** con A5 < 100.
- `breadth`: A1 **0** con completion **8.192** (corte one-shot); A5 **90**
  con **0 escrituras**, 33 tools y parada por cap **80.079 > 80.000**.
- El 90 de A5 `breadth` es el **estado inicial**: el QA de esa tarea da
  `empty_score=90`. La suite oculta solo discrimina 10 puntos; A5 no mejoró
  nada. Ese 90 no es evidencia de capacidad del arnés.
- `runtime` y `contract`: A1 **100** y A5 **100**; QA vacío 67,5. Otra vez
  saturación, no headroom.

### 3.3 H24 — el techo de salida domina el resultado

- A1 `tail-2/4/24` = **27,2727 / 0 / 0**; A5 `tail-2/4` = **0 / 0**;
  `tail-24` no ejecutada. QA vacío **0** y referencia **100** en las 3: la
  prueba oculta sí es sensible; el fallo no es de tests.
- A5 leyó los ficheros completos (7.569 chars, cola en 7.548) pero intentó
  reescribirlos con `write_file` completo. La salida se cortó exactamente a
  **4.096 completion tokens** (5.220 chars), produjo JSON inválido 5/2 veces
  y **0 escrituras**. Repitió la misma escritura truncada 5 veces en `tail-2`
  y 2 en `tail-4`.
- A1 `tail-24` gastó **90.964** (82.772 prompt + 8.192 completion) y no
  produjo bloques parseables. `tail-4` también agotó 8.192 completion.
- Coste: **290.185** (238.176 prompt + 52.009 completion), **40.185 por
  encima** del techo 250.000. A5 `tail-2` **91.027 > 70.000**; A5 `tail-4`
  **72.152 > 70.000**; A1 `tail-24` **90.964 > 70.000** y el cap no se aplicó.

## 4. Hallazgos de instrumento

### I1 — El cap no se aplica antes de la llamada

`harness.py:382-387` calcula `_cap_excedido()` con el uso acumulado, pero se
consulta **después** del turno (`harness.py:523`). Una llamada puede pasarse
del cap y solo se corta al terminar. H24 `A5 tail-2` lo demuestra: 91.027
frente a 70.000. H23 `A5 breadth` ya lo había medido: 80.079 frente a 80.000.

### I2 — El camino one-shot no aplica cap ni techo

`_run_one_shot()` (`harness.py:420-436`) llama al LLM y devuelve el resultado
sin comprobar `_cap_excedido()` ni `_techo_alcanzado()`. Por eso A1 `tail-24`
gastó 90.964 con cap 70.000. El cap de celda y el techo global solo existen
de facto para el bucle A5.

### I3 — El techo global permite overshoot deliberado y no reserva por celda

`_techo_alcanzado()` (`harness.py:389-400`) corta mid-cell solo si la celda
ya gastó ≥80% de su proyección; `_run_many()` (`run_sd3.py:304`) solo mira
`spent >= techo` antes de la siguiente celda, no `spent + proyección`. La
proyección inicial de H24 era 226.437 ≤ 250.000, pero el coste real fue
290.185. La proyección no es conservadora: H23 proyectó 140.448 y gastó
194.453 (+38,4%); H24 proyectó 226.437 y gastó 290.185 (+28,2%).

### I4 — El gate R2 de H24 no mide A1; hereda el hueco de A5

`sd4_sens.py` construye `valid_tasks` exigiendo A1 **y** A5 válidas y calcula
la media de A1 sobre ese subconjunto. Como A5 `tail-24` no se ejecutó, R2
usó solo 2 tareas: media 13,6364 y `A1_lt_100=2`. Con las 3 celdas A1, la
media sería **9,0909** y `A1_lt_100=3`; R2 habría pasado. **No se re-puntúa
H24** (R1/R3/R4/R5/R6 siguen rojos), pero R2 no es un gate independiente:
mide la validez del par, no la saturación de A1. H26 debe separar R1 de R2 y
usar todos los A1 disponibles.

### I5 — Denominadores mezclados y gates dependientes

El cierre de H24 dice `A5 con escritura 0/3` y `no atascada 2/3`, pero
`sd4_sens.py` calcula sobre 2 válidas: `A5_writes=0/2`, `A5_not_stuck=2/2`.
No cambia el veredicto, pero impide comparar gates. H26 debe fijar `n` por
gate y no usar el mismo subconjunto para todo.

### I6 — El modelo no recibe señal de truncado de salida

Cuando `write_file` se corta a 4.096 tokens, el parser devuelve “JSON
inválido” y el bucle reintenta la misma escritura completa. No hay
`finish_reason=length` ni un error `TOO_LARGE` que le diga “usa un parche más
pequeño”. El agente gasta turnos y tokens repitiendo una acción imposible.
H24: 5 + 2 escrituras truncadas, 0 escrituras efectivas.

### I7 — El constructo no tiene punto medio

H22 y H23 demuestran saturación de A1 cuando la tarea cabe en la salida.
H23 `breadth` y H24 demuestran que, cuando la tarea exige más salida, el
corte de 4.096/8.192 domina y el arnés no puede ejecutar. No se ha medido un
constructo donde A1 falle por razones de la tarea y A5 pueda resolver con
herramientas dentro del presupuesto. Ese es el hueco que SD-2/3/4 no han
cerrado.

## 5. Veredicto de auditoría

- **No hay constructo limpio** en H22-H24. Los tres cierres son correctos:
  **NO CUMPLE**.
- **No se debe lanzar SD-5** con el mismo harness. Cambiar de tareas sin
  corregir I1-I6 produciría otro resultado dominado por el canal de salida.
- **H24 no se reabre ni se re-puntúa**. El hallazgo de R2 es un defecto de
  diseño de gate para H26, no una enmienda del veredicto.
- **Recomendación: parar la línea SD**. No se construyen las 24 tareas, no
  hay oficial y no hay Harness Card SD-2/3/4. La ratificación es del dueño.

## 6. Opciones para H26

### H26-A — Reparar el instrumento y probar un constructo pequeño

Solo si el dueño quiere conservar el benchmark de software. Todo empieza con
**0 tokens**:

1. Cap duro antes de cada llamada, incluido one-shot: `max_tokens` limitado
   por `cell_remaining` y `techo_remaining`; si no cabe, parar.
2. Herramienta de parche (`apply_patch`/`replace_lines`/`append`) o ficheros
   de ≤2k chars; `write_file` rechaza contenido por encima del máximo con un
   error explícito, no con JSON inválido.
3. Propagar `finish_reason=length`; una salida truncada se registra como
   `output_limit` y no se reintenta igual.
4. A1 ve el fichero completo (ficheros pequeños) o se declara “sin
   herramientas”; prohibido confundir truncado de entrada con capacidad.
5. Gates independientes: A1 sobre todos los A1; A5 sobre todos los A5; R1
   separado; `n` explícito.
6. QA con `empty_score` bajo (≤30) y delta real; un 90 inicial invalida la
   tarea.
7. Efecto mínimo detectable y potencia declarados antes del probe. Un probe
   de 2 tareas solo valida el constructo, no una diferencia de arneses.

Coste orientativo del probe reparado: 2 tareas × A1/A5, ficheros de 1-2k,
cap 40.000/celda, techo 100.000. Si pasa, se planifica 6-12 tareas; no se
reutilizan fixtures H22-H24.

### H26-B — Cerrar SD y volver a B-1/B-2 + producto (recomendada)

1. Cerrar SD-2/3/4 como **NO CUMPLE** definitivo; no hay SD-5.
2. Usar **B-1 v2** y **B-2 H18** —ya ratificados, B-2 con CUMPLE— para
   evaluar arneses reales.
3. Dedicar el esfuerzo 0-token a lo que falta del producto: conectar
   `coevolve` a la ruta de producción, compilar skills/memoria y medir
   transferencia corpus → arnés.
4. No abrir una corrida nueva hasta declarar plan, techo y gates.

**Recomendación:** H26-B. La línea SD ha consumido 698.497 tokens en tres
constructos y no ha producido una medida limpia; B-1/B-2 ya existen y el
producto tiene huecos más valiosos que otro probe de software. H26-A queda
como opción si el dueño prioriza explícitamente el benchmark SD.

## 7. Qué NO se hace

- No lanzar SD-5 ni reanudar H24.
- No editar `result_sd2_calibracion.json`, `result_sd3_probe.json`,
  `result_sd4_probe.json`, sus logs, trazas, locks o fixtures.
- No bajar umbrales ni cambiar gates de H22-H24.
- No elegir tareas nuevas mirando A1/A5 de H22-H24.
- No commit ni push sin petición del dueño.

## 8. Reproducción

Las cifras salen de:

- `evals/results/result_sd2_calibracion.json`
- `evals/results/result_sd3_probe.json`
- `evals/results/result_sd4_probe.json`
- `evals/sd_pilot/traces_sd2_calibracion.sqlite`
- `evals/sd_pilot/traces_sd3_probe.sqlite`
- `evals/sd_pilot/traces_sd4_probe.sqlite`
- `evals/HITO22_PLAN.md` §7, `evals/HITO23_PLAN.md` §9,
  `evals/HITO24_PLAN.md` §9

Comandos de lectura usados (sin LLM):

```bash
.venv/bin/python -c "import json; ..."
.venv/bin/python -c "import sqlite3; ... spans ..."
```

## 9. Decisión del dueño

**Ratificada la opción B el 2026-10-25**: cerrar SD-2/3/4 como NO CUMPLE,
no abrir SD-5 y pasar a **H26-B** (B-1 v2 / B-2 H18 + producto:
`coevolve`, skills y memoria). H26-A queda descartada salvo nueva decisión.

Sin un plan H26 ratificado no se lanza ninguna corrida ni se construyen
tareas nuevas.
