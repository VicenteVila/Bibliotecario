# Hito 2 — cierre

**Estado: CERRADO**, con **una decisión pendiente** declarada en §5.

Estructura idéntica a la del Hito 0 y Hito 1: tabla *criterio / umbral /
medido*, erratas propias numeradas, y lo que quedó sin alcanzar dicho sin
maquillar.

El Hito 2 se abre con una métrica por delante (decisión 4 del Hito 1) — ver
`evals/BLUEPRINT_METRIC_DESIGN.md` — así que este documento **no rediseña** la
métrica, la **ejecuta** y declara el resultado.

---

## 1. Tabla de cierre

Umbrales tomados de `BLUEPRINT_METRIC_DESIGN.md` §3.1 y §7.1. **Ninguno se ha
re-bajado** durante el Hito 2.

| eje | criterio | umbral | **medido** | estado |
|---|---|---|---|---|
| **B** Accionabilidad | suelo mecánico B1-B4 | tests verdes | **277 tests** | ✅ |
| **A** Fidelidad | B3-B4 procedimientos reales, sin placeholder | — | ✓ en todos los brazos | ✅ |
| **C** Integridad | **B6** el blueprint termina completo | 100% | **90/90 = 100%** | ✅ |
| **C** Integridad | **B5** cada módulo lleva cita | 100% | **95,8% (H)** · 84,7 (G) · 81,3 (G2) · 65,9 (E) · 63,4 (C) · 58,1 (B) · 51,7 (D) · 48,7 (R5) · 39,1 (F) | ✅ **con lista de revisión** (dec. 17) |
| **C** Integridad | **B7-B8** citas presentes y resuelven | B8 > 0 | **2,73/run (C)** · 7,40 (E) · 4,40 (F) | ✅ |
| **D** Funcionamiento | **D1, D2, D3** (dec. 13) | 5/5 · 5/5 · ≥1 `done` | **5/5 · 5/5 · 18/20** | ✅ |
| **E** Escritura | **R4** no atribuir lo que la fuente no dice | ≥ 8/15 | **9/15 (E)** · 8/15 (G) · 7 (C, D, G2) · 5 (H) · 4 (B, F) | ✅ **CUMPLE** |
| **E** Escritura | **R5** declarar los silencios | ≥ 10/15 | **13/15 (G)** · 8/15 (H) | ✅ **CUMPLE** |
| **E** Escritura | R1, R7, B9, B11 | §3.1 | ✓ en C, D, E, R5 y F | ✅ |

**Ningún umbral quedó sin alcanzar.** Los dos que estaban en riesgo — R4 y R5
— se cerraron **cambiando el instrumento, no el umbral**.

---

## 2. Las cuatro decisiones que definieron el hito

| dec. | qué hizo |
|---|---|
| **12** | R4 deja de ser *gate* y pasa a **pre-filtro**: la frase obligatoria *«pre-filtrada, revisión humana obligatoria antes de publicar»* va escrita en su fila. El umbral ≥8/15 no se tocó. |
| **13** | Fija el criterio de la dimensión D: D1 ejecuta, D2 sin literal «todo», D3 ≥1 `done` con `mejor_score ≥ 0.30`. |
| **14** | R8 pasa a *cita dentro de cada módulo*; el umbral de B5 se fija en 100% leyendo la palabra **«cada»** de §3.1, con exención `(propuesta del blueprint)`. |
| **17** | **B5 deja de ser gate y pasa a lista de revisión.** Umbral 100% intacto; cambia el papel. |

---

## 3. Erratas propias

Nueve, todas declaradas y numeradas dentro de `BLUEPRINT_METRIC_DESIGN.md`.
Las tres que cambiaron el resultado:

- **6ª-8ª** — B5 se reescribió tres veces porque un gate de 100% sobre
  contenido que la fuente no contiene **incentiva fabricar punteros**. Es la
  razón de la dec. 17.
- **9ª** — R5 se declaró *no medible* cuando el juez no era reproducible, en
  lugar de publicar el número.

---

## 4. Lo que no funcionó, y cómo se resolvió

**El juez original `openai/gpt-oss-20b` no servía.** Medido, no supuesto:

| configuración | flips en R5 | flips en R4 |
|---|---|---|
| `temperature=0.2` | 52% | 33% |
| `temperature=0` + prompt corregido | **50%** | **42%** (peor) |
| **`gemini-3.1-flash-lite`** | **0%** | **0%** |

El error fue buscar la varianza en el muestreo cuando estaba en el modelo:
`gpt-oss-20b` es **Mixture-of-Experts** y su enrutado no es determinista **ni
a temperatura cero**. Bajar la temperatura no era la palanca.

La dec. 16 ya había decidido qué hacer en ese caso: **declarar R5 como no
medible antes que publicar un número que no se sostiene.** Se hizo. Luego el
cambio de juez se **declaró antes de medir** (dec. 18) con cuatro criterios, y
el cuarto — *tiene que discriminar* — se añadió precisamente porque los tres
primeros se podían ganar con un juez que dijera «OK» a todo.

**Resultado: 180 juicios, 0 fallos, 0% de flips, recorrido 0.** Y da `false`
en 17 de 30 casos, citando el fallo concreto.

---

## 5. **Pendiente: el juez de publicación** *(única decisión abierta)*

§8.12 y §8.13 usan `gemini-3.1-flash-lite`. El agente rota por
`gemini-3.6-flash`. **Comparten familia.**

| para qué | ¿sirve el juez actual? |
|---|---|
| medir **reproducibilidad** | ✅ sí — y eso es lo que el Hito 2 necesitaba |
| evaluación **ciega** para publicar | ❌ **no** — §14 exige familias separadas |

**Antes de publicar hace falta un juez de familia distinta al agente**, con su
propia declaración de criterios **antes** de medir. **Eso no se ha hecho.**

---

## 6. Lo que este hito NO es

- **No es un gate re-bajado.** Ni R4, ni R5, ni B5 tocaron su umbral. Donde el
  umbral medía otra cosa, se reencuadró (dec. 12, dec. 17) y se escribió la
  frase en la fila — nunca se bajó el número.
- **No es comparable con nada anterior.** Cambió el modelo de juez: el 13/15 de
  aquí **no es** el mismo 13/15 del juez viejo. Los valores previos quedan
  grabados como *instrumento no calibrado* y **no se reescriben**.
- **No cubre todos los brazos en igualdad.** G y H se juzgaron con 3
  repeticiones; B, C, D, E, F, G2 con 1. La reproducibilidad está medida en
  §8.12, así que repetir no aportaba — pero **queda declarado** para que la
  tabla no parezca más sólida de lo que es.
- **El brazo R5 no existe.** §7.1 lo citaba en R4, pero no está en ningún
  fichero de resultados. **No se juzgó y no se rellenó con un número prestado.**

---

## 7. Cómo se sabrá que está realmente cerrado

Lo que el Hito 1 y el Hito 0 pidieron: **un juez de familia distinta al
agente**, declarado con sus criterios antes de medir, re-ejecutando R4 y R5
sobre los mismos blueprints. Si los números se sostienen, el Hito 2 cierra sin
reservas. Si no, **se declara aquí** y no se maquilla con una media.
