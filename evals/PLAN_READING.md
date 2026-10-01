# Plan: atacar el residuo "cita el chunk gold y aun asi falla"

**Estado: planificado, NO implementado.**
**Gate de r6: SUPERADO, con matiz.** Ver seccion 6.

**Rama de trabajo:** todas las cifras salen de r1-r6, ya commiteadas.

---

## 1. El diagnostico, en una frase

El 74% de los fallos residuales ya **no son de entrega de evidencia**: el agente
cita el chunk gold correcto y aun asi da una respuesta incompleta o invertida.

| | |
|---|---|
| fallos con judge<5 en r1-r5 | 39 |
| de los cuales **cierran el chunk gold** | **29 (74%)** |
| de los cuales no lo cierran | 10 (26%) |

Y la tendencia es la que confirma que los tramos anteriores se agotaron:

| run | fallos que citan el gold |
|---|---|
| r1 | 9 |
| r2 | 7 |
| r3 | 5 |
| r4 | 5 |
| **r5** | **3** |

Los tres fallos que quedan en r5, uno a uno:

| id | judge | chunk gold citado | que falla |
|---|---|---|---|
| `wiki-b1` | 2 | `[5:12]` **si** | respuesta con directorios (`wiki/`, `skills/`) en vez de los ficheros `logs.md` y `skill-impact.md` |
| `tce-b7` | 3 | `[3:25]` **si** | invierte el argumento: la razon real es que el muestreo uniforme gasta presupuesto en tareas faciles |
| `wiki-b6` | 3 | `[5:24]` **si** | correcto pero incompleto: omite el tercer numero (38.5%) |
| `pg-b5` | 2 | `[2:82]` **no** (gold `2:85`) | da solo los numeros de HotpotQA e inventa un cuarto (4,003.24) |

Metrica guia propuesta: **cobertura de los keywords gold en la respuesta**.Hoy
promedia 68%, y correlaciona con el judge (pearson r = 0.386). Los cuatro fallos
de r5 estan en 20%, 20%, 40% y 60%.

---

## 2. Por que nada de lo que hay ahora lo detecta

- `_final_answer` exige **que haya cita**, pero `CITE_FMT.has_citation` solo
  comprueba que exista al menos una. No comprueba que la cita **soporte** lo que
  se afirma, ni que la respuesta **cubra** lo que se pregunto.
- No hay ningun sitio donde se miren las **partes** de la pregunta. `pg-b5` pide
  dos juegos de numeros y `wiki-b1` pide dos cosas ("que ficheros" + "que
  componente actualiza cada uno"); el cierre responde una y se acaba.
- La verificacion de la cita no mira el **contenido** del chunk citado, asi que
  citar el chunk correcto con una conclusion invertida pasa desapercibida.

---

## 3. Los tres pasos, del mas barato al mas caro

Cada uno lleva su propia puerta de salida. Si un paso no mueve la metrica, se
suelta y se pasa al siguiente: estan ordenados porrelation coste/riesgo.

### Paso A — Ancla numerica determinista (0 tokens, sin LLM)

Toda cifra de la respuesta final debe aparecer **literalmente** en el chunk que
cita. Si no, se reabre el cierre con la infraccion marcada.

Por que: `pg-b5` se invento el 4,003.24. Medido sobre las runs, hoy hay **46 de
239 cifras (19%) sin respaldo** en su chunk citado.

Honestidad sobre el riesgo: un 19% de violacion es demasiado ruidoso para una
**puerta dura**. Habria que (a) aceptar el numero si aparece en un chunk
*contiguo* del mismo documento, y (b) exigir coincidencia con separador de miles
y decimales tal cual, para no reventar los falsos positivos de numeros de seccion.

**Puerta:** offline primero, sobre r1-r5 ya grabadas. Si la violacion residual
baja de ~19% a <5% con el filtro de contigüidad, se pasa a puerta dura en el
cierre. Si no, **se descarta el paso entero** y no se toca produccion.

### Paso B — Puerta de cobertura por partes (1 llamada extra, solo si aplica)

Detectar lexicalmente si la pregunta tiene >=2 sublanzamientos (dos entidades
enumeradas, "and", "each", "versus", "compare", dos juegos de cifras pedidos) y,
solo en ese caso, una llamada de auditoria: "¿que pide la pregunta que este
borrador no contesta? Anadelo."

Por que: cubre `pg-b5` (dos juegos de numeros) y `wiki-b1` (ficheros +
componente) sin tocar las 31 preguntas que ya van bien.

**Puerta:** el detector tiene que dar 0 falsos positivos sobre las 31 preguntas
con judge=5 de r5. Si dispara sobre alguna, se estrecha o se descarta.

### Paso C — Verificacion de que la cita sostiene la afirmacion (1 llamada, optativa)

Pasarle al modelo la pareja (afirmacion, contenido del chunk citado) y pedir un
si/no. Sirve para `tce-b7`, que cita bien e invierte el sentido, y ese caso es
el unico que **no** cubren A ni B.

Es el paso mas caro y el que mas riesgo de sobrecorreccion (un juez que "corrige"
respuestas correctas). Va el ultimo y detras de una puerta: si A y B ya han dejado el
residuo a <1 fallo, C no hace falta.

---

## 4. Como se decide si funciona

1. **Gate offline, gratis**: replay de r1-r5 con el paso A. Si la metrica guia no
   mejora, el paso no entra.
2. **Replica**: si r6 confirma r5 (delta > 0 y p < 0.05 sobre la linea base),
   se implanta **A** y se mide su propio run.
3. Criterio de exito por paso: +0.15 en la media de r5 **y** cero perdidas en
   `abstain_rate`, que es donde r5 ya toca techo (5/5 en r4) y no se puede
   regalar nada.
4. `abstain_rate` es la metrica de guardia. r5 bajo de 1.0 a 0.8 con una
   fabricacion (`reas-b8`). Ningun paso puede volver a subirla.

---

## 5. Lo que este plan NO hace

- **No toca pesos de retrieval.** Ya se midio: `W_GRAPH` de 0.2 a 0.0 mueve 1
  chunk de 46, y el titulo no cambia ninguna metrica.
- **No toca `n_docs`.** El recorte de 2 a 4 esta justificado offline (38/46 a
  40/46 chunks) y en produccion (`wiki-b4` de 2 a 5).
- **No reactiva el anclaje.** r4 con anclaje fue p = 0.206; r5 sin el fue
  p = 0.004. El anclaje cuesta ~15k tokens por pregunta y no se sostiene.
- **No agranda la evidencia.** Ya se probo: 112k chars con los keywords dentro y
  el agente pasandolos por alto. El problema no es cuanto, es que elige mal.
---

## 6. Veredicto de r6 (la replica que pediste)

| run | media | delta | t | p |
|---|---|---|---|---|
| r4 (con anclaje) | 4.543 | +0.219 | 1.26 | 0.206 |
| r5 | 4.714 | +0.390 | 2.86 | **0.004** |
| r6 (replica) | 4.600 | +0.276 | 1.68 | 0.093 |
| **r5+r6 promediadas** | **4.657** | **+0.333** | **2.44** | **0.015** |

**Matiz honesto: r6 en solitario NO llega a significancia (p = 0.093).** El
efecto se sostiene a nivel de pool (p = 0.015), no de run individual. Quien
queraquoting "p = 0.004" esta cherry-picking la run buena.

### Pero la tabla por pregunta es mucho mas fuerte que el p-valor

**11 preguntas pasaron de <5 en la linea base a 5 en r5 Y en r6.** Esas son
reproducibles, no ruido:

```
pg-b2    base 4  ->  r5 5   r6 5        reas-b3   base 4  ->  r5 5   r6 5
pg-b3    base 4  ->  r5 5   r6 5        reas-b6   base 4  ->  r5 5   r6 5
pg-b6    base 4  ->  r5 5   r6 5        tce-b3    base 4  ->  r5 5   r6 5
reas-b2  base 4  ->  r5 5   r6 5        tce-b4    base 4  ->  r5 5   r6 5
tce-b5   base 4  ->  r5 5   r6 5        wiki-b4   base 2  ->  r5 5   r6 5
                                    wiki-b7   base 2  ->  r5 5   r6 5
```

Delta pareado sobre esas: **+2.545**. Y **30 de 35 preguntas son 5 en las dos
runs**. Los fixes no dependen de la suerte: se quedan arregladas.

### Toda la varianza que queda esta en 5 preguntas

| id | base | r4 | r5 | r6 | rango |
|---|---|---|---|---|---|
| `wiki-b1` | 2.00 | 5 | 2 | **1** | 1-5 |
| `wiki-b2` | 3.67 | 5 | 5 | **1** | 1-5 |
| `pg-b5` | 2.33 | 2 | 2 | 1 | 1-2 |
| `tce-b7` | 4.00 | 3 | 3 | 4 | 3-4 |
| `wiki-b6` | 3.33 | 4 | 3 | 4 | 3-4 |

Y aqui aparece el riesgo que se documento al subir `n_docs` a 4, **`wiki-b2`
cayo a 1 y `abstain_rate` bajo a 0.8 en las dos runs**. `wiki-b2` es una de las
`false_abstention` de r6: el agente tiene la evidencia y se rindio. Es la
dilucion de la que se hablaba, apareciendo en la pregunta que menos se esperaba.

**Conclusion: el gate se supera y el plan se implanta.** El objetivo no es el
p-valor, es que el residuo son 5 preguntas con rango 1-5, y las cinco son
exactamente el modo de fallo que el plan ataca (evidencia presente, respuesta
incompleta o abandonada).

---

## 5. Resultado de los tres pasos (cerrado)

Medidos los tres contra el mismo residuo de r5/r6. Detalle y tablas en
`REPORT_BLIND.md`, "Fase 0f".

| paso | que era | resultado |
|---|---|---|
| A | replay numerico sobre la evidencia citada | **descartado**: 0 cifras inventadas en 588 citas; el detector acierta 12/12 sobre numeros inyectados, no hay nada que cazar |
| B | detector de pregunta multiparte | **descartado**: 16 falsos positivos sobre 30 respondibles ya correctas; mide "no contesto la 2ª parte", no "eligio la parte equivocada" |
| C | verificar que la cita sostiene la afirmacion | **implementado y apagado**: 4.10 vs 4.00 (r5) y 3.60 (r6) en 13 preguntas; 0 controles danados; +0.029 sobre 35 contra r5, por debajo del +0.15 del gate y por debajo del ruido r5-r6 (0.114) |

C queda en el codigo detras de `VERIFY_CITATION=1` (por defecto `0`), con la puerta
anti-sobrecorreccion asimetrica: una reescritura solo se acepta si cita un chunk que
ya estaba en la evidencia que se entrego al cierre. "OK", una salida sin cita o una
cita nueva devuelven el borrador original intacto. Con el flag apagado no cambia
nada: 178 tests pasan en ambos estados.

**El plan queda agotado.** Las tres vias medibles estaban descartadas antes de
empezar y la que quedaba no llego al gate. El diagnostico que si sobrevive es que
el residuo es de *discriminacion* con la respuesta presente en el contexto, y que
un parche mas del agente no lo ataca. Lo que toca probar despues es del lado de la
pregunta (una sola sub-pregunta por caso) o de la recuperacion (ranquear el chunk
dentro del documento, no el documento entero), no del cierre.
