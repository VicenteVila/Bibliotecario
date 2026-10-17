# HITO 8 — H1 intento 5: edición dirigida de cuerpo (máscara), mismo juez

Fecha de declaración: 2026-10-17. Commitear ESTE archivo ANTES de escribir
código (§4). Arm: `H15`.

## §0 Por qué — diagnóstico tras el intento 4 (HITO7, cerrado NO CUMPLE)

HITO7 §5 midió, con 0 reescrituras posibles (imposibles por construcción):

1. **Las marcas R6 no giran el veredicto**: WikiSkill se marcó la línea exacta
   de la queja (l37, única ocurrencia de «estratificado») y el juez repitió la
   misma queja R5 en r1, r2 y r3. Conviene además que los textos con marcas
   heredadas conviven con aprobaciones (PEARL, 4 marcas): la marca ni suspende
   ni neutraliza.
2. **Quejas ancladas en encabezados** (ReASearch, 2/2: l9 «Módulo 3:
   Refinador…», l18 «Orden de Ejecución»): el encabezado no se puede marcar
   sin romper V2, y el localizador apuntó a ellos correctamente rechazados.
3. **Localizador frágil**: 5/10 salidas `sin líneas parseables` (drift de
   formato) y ReASearch r1 respondió 1 de 2 frases **sin registrar la ausente**.

Lo que NO cambia: mismo juez (`gemini-3.1-flash-lite`, temp 0, prompt
intacto), mismas guardas (G1/G2/V1/V2/C1'), mismo contrato del localizador
(solo números + eco ≥20 verificado, cero reescritura), misma disciplina de
intento. El fallo de H5' 3/5 no se toca con umbrales: se toca **quitando del
texto la afirmación que el juez cita**.

## §1 Mecanismo — M5 máscara dirigida (edición, cero generación)

Unidad de reparación: igual que HITO7 — frases R4+R5 del juicio fallido →
**M1 localizador** (mejorado, abajo) → **M5 edición determinista**.

**M5a — `mascarar_lineas(blueprint, lineas) -> (text, stats)`**
- Reemplaza el contenido de cada línea señalada (no encabezado, no vacía, en
  rango, aún no mascarada) por la plantilla fija
  `MASCARA = "*[contenido retirado: no consta en la fuente]*"` más,
  **conservados**, todos los punteros `[doc:X:Y]` de la línea original
  (G1 no pierde resueltas). Conserva el salto de línea. Las demás líneas,
  byte a byte intactas.

**M5b — `mascara_seccion(blueprint, n_encabezado) -> (text, stats)`**
- Para quejas ancladas en encabezados: el cuerpo bajo el encabezado (hasta el
  siguiente `#`) se vacía en **una sola línea** con `MASCARA` + los punteros
  de todo el cuerpo. **El encabezado queda byte a byte intacto** (V2/G2).
  Sin cuerpo = no-op.

**M1 (localizador) — mismas reglas de verdad, tres arreglos declarados:**
- Pre-normalización **determinista** antes del parse (0 tokens): flechas
  unicode `→`/`⇒` → `->`; viñeta inicial (`-`, `*`, `•`) antes del número →
  fuera. El eco ≥20 chars sigue decidiendo si la línea es la correcta.
- Frases **sin entrada** en la salida pasan a contar como
  `frase N: sin entrada en la salida` (antes se perdían en silencio —
  H14 r1 perdió 1 de 2 frases sin registrar).
- Clave nueva `encabezados` (frases cuyo destino apunta a un encabezado): se
  sigue reintentando por formato (feedback igual), y esas líneas alimentan a
  M5b. Línea vacía = invalida, sin M5b.

**Validación tras cada edición:** `validate_structure(base, editado)` (V1 ≥50%
+ V2 encabezados) — vacía la lista = ronda ok; si fallara → fila
`ok=False` con causa `validacion_tras_edicion` (arnés fallo; declarado aquí,
riesgo estimado bajo: se editan ≤2 líneas o 1 sección por ronda sobre docs
de ≥2243 chars). V3/G1 lo da la conservación de punteros + resumen final.

**Garantías declaradas:** cero generación (plantilla fija, 0 tokens),
cero reescritura de prosa ajena, encabezados intocados, punteros
conservados, historia H1/H1R/H12/H13/H14 sin tocar.

**Riesgos declarados ANTES de medir (no se maquillan si ocurren):**
- ReASearch: si el juez sigue citando el encabezado **aunque el cuerpo quede
  vaciado con la máscara**, H5' queda en 4/5 y el intento es NO CUMPLE — se
  registrará tal cual.
- El localizador puede seguir devolviendo formatos no parseables (5/10 en
  H14; la pre-normalización ataca lo más probable sin relajar el eco).
- Tras una máscara efectiva, una ronda posterior puede volver sobre la misma
  línea ya mascarada (no-op) y quemar rondas con veredicto idéntico (temp 0).

## §2 Umbrales (a ratificar antes de la corrida)

Idénticos a HITO7 §2 — no se re-baja nada:

- **H5' 5/5** arneses con r4_ok y r5_ok en el último juicio.
- **G1 5/5** resueltas finales >= base.
- **G2 5/5** encabezados conservados.
- **C1'** : suite **>= 312** verdes (los 312 actuales + tests nuevos), finales
  >= 50% de la base, **ningún arnés `ok=False`**.
- **Global = los cuatro.** Coste ≤ 20 juicios + ≤ 12 localizadores = ≤ 32
  llamadas (edición 0). Mismo env del juez que los intentos anteriores
  (`JUDGE_MODEL=gemini-3.1-flash-lite`, `Q1_BASE_URL` de Google,
  `Q1_API_KEY` de `.env`).

## §3 Runner

`evals/run_fase1_h15.py` → `evals/result_fase1_h15.json` (filas `H15`) y
juicios `arm="H15", run=ronda` en `evals/result_q1_r4r5.json` (H1…H14 sin
tocar; solo-adición).

- Base por arnés = **mejor estado aprobado conocido** (cadena H14 → H13 →
  H1R → H1; los tres aprobados de H14 son bytes idénticos a los de H13).
- Ronda 0: guardado + juicio fresco de la base + M4 saneo de disco (<50%,
  hoy ya saneado). Si aprueba, arnés cerrado.
- Reparación: M1 (≤2 intentos con feedback) → M5a sobre `validas` → M5b
  sobre `encabezados` → `validate_structure` → fila + disco.
- Hasta **3 rondas**; tres fallos seguidos = arnés fin. Causas registradas
  (no maquilladas): `sin_frases_del_juez`,
  `presupuesto_localizador_agotado`, `validacion_tras_edicion`.
- `loc_info` guarda además `lineas` y `secciones` editadas (esta vez el
  diagnóstico post-mortem queda completo — hueco declarado de H14).
- Idempotente; apertura obligatoria con la env del juez (aborta sin ella).

## §4 Disciplina

1. Commit de ESTE archivo solo, antes de escribir código.
2. Implementación + tests (suite completa verde) + ruff.
3. Ratificación explícita del dueño de §2 y del env (incluidos los riesgos
   pre-declarados de §1).
4. Corrida oficial única; resultados en §5 de este archivo + hallazgo 26 en
   CONOCIMIENTO, en el commit de cierre.
5. NO CUMPLE se cierra igual; un intento 6 exigiría declaración nueva.

## §5 Cierre — 2026-10-17 · NO CUMPLE (evidencia)

- **Resultado**: H5' **3/5** · G1 **5/5** · G2 **5/5** · C1' **SÍ** → NO CUMPLE
  (§2 exige los cuatro). Coste **11 juicios + 10 localizadores = 21** de ≤32;
  **0 generaciones**; **ningún arnés `ok=False`** (V1/V2 nunca fallaron:
  0 causas `validacion_tras_edicion`). Suite al cierre: **320**. PEARL/PG/TCE
  aprueban r0 estables (temp 0).
- **Lo que sí funcionó (primera vez en 5 intentos): la máscara cambia el
  veredicto de la queja.**
  - WikiSkill: l37 (única con «estratificado») enmascarada en r0 →
    `estratificado` **desaparece del texto final** (verificado en el bp) y el
    juez r1 cambia de queja a «filtrado basado en consistencia histórica».
  - ReASearch: r0 enmascara [10,19] (los cuerpos bajo l9/l18) → las quejas de
    r1 son **completamente distintas** (Módulo 4 / state re-emission).
  - Contra H14 (marca R6 → queja intacta 3 rondas): el juez lee el documento
    **fresco** y **cada máscara mata su cita**.
- **Pero el juez es de «whack-a-mole»: cada ronda revela la siguiente
  fabricación.** ReASearch: quejas distintas en r0, r1, r2 y r3 (4 máscaras,
  nunca converge en 3 rondas). Su base (H1R) **jamás fue aprobada por el
  juez** — es un doc con muchas fabricaciones; drenarlas en ≤3 rondas × ≤2
  frases es inviable. WikiSkill: tras r0, **4 salidas `sin líneas parseables`
  consecutivas** (r1–r3) → 0 máscaras → misma queja ×2 (temp 0): la
  pre-normalización de flechas/viñetas **no bastó** (el drift de r1+ no eran
  flechas; la salida cruda sigue sin persistirse — límite declarado de H14,
  se confirma).
- **M5b no disparó jamás (0 secciones vaciadas) — bug de diseño medido:**
  los `encabezados` detectados en el intento 1 del localizador se descartan
  al reintentar (ReASearch r1: «frase 2: la línea 18 es encabezado» → el
  intento 2 omite la frase → parse final `enc=[]`), y el runner solo acciona
  el parse final. Las quejas ancladas en encabezados (l9/l18 de ReASearch)
  quedaron sin vaciar: siguen vivas en el bp final.
- **Lo bueno del arreglado H14**: «frase N: sin entrada en la salida» se ve
  en r1/r2 de ReASearch (antes se perdía en silencio); veredictos r0
  estables; encabezados intactos y punteros conservados en todas las filas.
- **Lección para un eventual intento 6** (exige declaración nueva): el
  whack-a-mole exige (i) que **M5b dispare de verdad** (acumular
  `encabezados` de todos los intentos, o aceptar encabezado como terminal),
  (ii) **rondas/presupuesto acordes al nº de fabricaciones** de la base (o
  una base de ReASearch con historial de aprobación que hoy no existe), y
  (iii) un **localizador que no muera de formato** (4 fallos seguidos
  mataron la convergencia de WikiSkill — candidato: guardar la salida cruda
  y añadir normalización adicional declarada). La enmienda del juez sigue
  descartada por comparabilidad (§0 del HITO8 / hallazgo 10).
