"""Verificación mecánica de atribución: ¿lo que el blueprint dice que sale de la
fuente está realmente en la fuente?

Motivo: el A/B del Hito 2 midió que P2+P1' arreglan la forma (citas que
resuelven, bibliografía, cero plagio) pero **no la sustancia**: 11 de 15
blueprints del brazo C seguían atribuyendo a la fuente cosas que la fuente no
dice, con 2,67 fabricaciones de media. Las reglas en el prompt no bastan.

Lo que aquí se comprueba es lo que H1 fue en la práctica: **nombres de módulos
inventados** («Adaptive Harness Execution Engine», «History Profiler»). Un
término técnico que se atribuye al paper y no aparece en ningún chunk es una
fabricación, y es detectable **sin juez y sin coste**.

Lo que NO se comprueba, declarado: la paráfrasis. Una frase reescrita con
palabras propias puede ser honesta o no y seguir sin compartir términos con la
fuente. Eso solo lo resuelve el juez (Q1). Este módulo es el filtro barato que
corre siempre; Q1 es el que cierra.
"""
from __future__ import annotations

import re

# Término técnico: compuesto en CamelCase, con guion, o entrecomillado.
_TECH = re.compile(
    r"[\"“«']([^\"”»']{6,})[\"”»']"          # entrecomillado
    r"|\b([A-Z][a-z]+(?:[A-Z][a-z]+){1,})\b"  # CamelCase: AdaptiveHarnessEngine
    r"|\b([a-z]+(?:[-_][a-z]+){2,})\b"        # kebab/snake de 3+ piezas
    # P4: numeros tecnicos y ficheros. El verificador original solo miraba
    # nombres de modulos, y por eso no cazó λ_t=0.125 ni goal.yaml — que son
    # exactamente los que el juez se inventaba como ausentes.
    r"|(\d+\.\d+%?)"                          # decimal: 0.125, 7.0
    r"|(\d{1,3}%)"                            # porcentaje: 85%
    r"|([A-Za-z]+@\d+)"                       # metrica: Hits@10, R@100
    r"|([A-Za-z_][\w-]*\.(?:md|yaml|yml|json|txt|py|csv|toml))"  # fichero
)

# Frase con puntero a un chunk, que es lo que se puede verificar.
# OJO: `[^\n.!?]*` no sirve aquí — corta en el punto y se come el propio
# término inventado, que casi siempre va ANTES del puntero («usa
# AdaptiveHarnessEngine para orquestar. [doc:1:0]»). Medido: el primer
# verificador no cazó nada por esto. Se toma una ventana hacia atrás.
_POINTER = re.compile(r"\[doc:(\d+):(\d+)\]")
_WINDOW = 260


def _terms(sentence: str) -> list[str]:
    """Términos distintivos de una frase: los que tendrían que estar en la
    fuente si la atribución es honesta.

    Cubre nombres de módulo, compuestos técnicos, lo entrecomillado y —desde
    P4— números técnicos y ficheros. Las palabras comunes no cuentan, o todo
    sería sospechoso.
    """
    out: list[str] = []
    for m in _TECH.finditer(sentence):
        t = next((g for g in m.groups() if g), None)
        if t and t not in out:
            out.append(t)
    return out


def check_attributions(blueprint: str, chunks: dict[int, str]) -> list[dict]:
    """Devuelve las atribuciones cuyo término técnico no está en el chunk citado.

    `chunks` mapea (doc_id, chunk_idx) → texto. Solo se examinan las frases que
    llevan puntero `[doc:id:chunk]`: sin puntero no hay a qué verificar, y
    inventarle un destino a una frase ya es el fallo que caza B8.
    """
    violations: list[dict] = []
    for m in _POINTER.finditer(blueprint):
        doc_id, chunk_idx = int(m.group(1)), int(m.group(2))
        # Frase que acaba justo antes del puntero. Ojo: el punto inmediatamente
        # previo CIERRA esa frase, así que hay que ir a buscar el anterior.
        end_sent = blueprint.rfind(".", 0, m.start())
        if end_sent < 0:
            start = m.start() - _WINDOW
        else:
            prev = max(blueprint.rfind(". ", 0, end_sent - 1),
                       blueprint.rfind("\n", 0, end_sent - 1))
            start = 0 if prev < 0 else prev + 1
        sentence = blueprint[max(0, start): m.end() + 80].strip()
        cited = chunks.get((doc_id, chunk_idx))
        if cited is None:
            # B8: el puntero no resuelve. Es un fallo distinto y ya medido.
            # `pos` lo añadió el Hito 6: es lo que permite demotear in-place
            # sin volver a buscar la frase (HITO6 §1.A).
            violations.append({"tipo": "puntero_roto", "chunk": f"{doc_id}:{chunk_idx}",
                               "pos": m.start(),
                               "frase": sentence[:200], "termino": None})
            continue
        cited_flat = cited.lower()
        for term in _terms(sentence):
            if term.lower() not in cited_flat:
                violations.append({"tipo": "termino_ausente",
                                   "chunk": f"{doc_id}:{chunk_idx}",
                                   "pos": m.start(),
                                   "frase": sentence[:200], "termino": term})
    return violations


# Marcas de R6/de silencio que separan lo propio de lo de la fuente en la
# propia línea (o en la inmediatamente siguiente, que es lo que R6 exige).
_MARKER = re.compile(
    r"propuesta del blueprint"
    r"|el paper no\b"
    r"|no consta en la fuente",
    re.IGNORECASE,
)


def check_orphan_claims(blueprint: str) -> list[dict]:
    """Afirmaciones con término técnico que no llevan puntero NI marca R6.

    El modo A del hallazgo 26: `check_attributions` solo examina frases con
    puntero («sin puntero no hay a qué verificar»), así que una fabricación
    anclada sin `[doc:id:chunk]` le es invisible — ReASearch salió
    `verificado=True` con 2/2 citas resueltas y el juez lo suspendió por
    inventar módulos presentados como del paper. Aquí se mira justo eso:
    línea con término técnico (mismo detector `_TECH` de siempre), sin puntero
    y sin la marca que R6 obliga a poner en su propia línea.

    Declarado lo que NO caza: una paráfrasis sin términos técnicos («selecciona
    tareas por varianza» a secas) sigue sin poder comprobarse sin juez; esto
    amplía el informe al tramo mecánico, no sustituye al juicio. Cero tokens y
    cero reescritura: devuelve el listado, el texto no se toca.
    """
    lines = blueprint.splitlines()
    out: list[dict] = []
    for i, line in enumerate(lines):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if _POINTER.search(line):
            continue
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if _MARKER.search(line) or _MARKER.search(nxt):
            continue
        terms = _terms(line)
        if terms:
            out.append({"tipo": "huerfana", "chunk": None,
                        "termino": terms[0], "terminos": terms,
                        "frase": s[:200], "linea": i + 1})
    return out


def _repair_prompt(blueprint: str, violations: list[dict]) -> str:
    """Instrucción de reescritura con las violaciones concretas, no genérica."""
    lines = []
    for v in violations[:12]:
        if v["tipo"] == "puntero_roto":
            lines.append(f"- La frase «{v['frase'][:120]}» apunta a [{v['chunk']}, que no existe.")
        else:
            lines.append(f"- «{v['termino']}» no aparece en el chunk [{v['chunk']}], "
                         f"pero la frase se lo atribuye: «{v['frase'][:120]}».")
    joined = "\n".join(lines)
    return (
        "Este blueprint atribuye a la fuente cosas que la fuente no dice. "
        "Corrige SOLO lo señalado, sin reescribir el resto:\n"
        f"{joined}\n\n"
        "Para cada caso, una de dos: si el término o el hecho SÍ está en la fuente, "
        "apúntalo al chunk correcto. Si NO está, quítalo o márcalo como "
        "«propuesta del blueprint» (R6). No lo dejes atribuido al paper.\n\n"
        "Devuelve el blueprint completo ya corregido, en markdown."
    )


# ---------------------------------------------------------------- ruta 5 (§5.10)
#
# §5.9.2 midió que P4 empeora R4 (6/15 → 2/13): apretar la atribución amplía la
# superficie donde fabricar, y las 17 acusaciones que quedan son semánticas —
# no alcanzables con regex. §5.10 propone el verificador como crítico en el
# bucle. Aquí está.
#
# La lección de P3 (§5.8.3) gobierna el diseño: **no se reescribe la prosa.**
# P3 regeneraba el documento y destruyó citas, bibliografía y silencios en 3 de
# 3. Aquí la única acción es **quitar el puntero**, que es una edición de cadena
# determinista. Al quitarlo, la afirmación sale del denominador de R4 por
# construcción — no se corrige la frase, se deja de presentarla como de la fuente.

_CRITIC_PROMPT = """Estás verificando una cita de un blueprint de agente.

La frase de abajo atribuye algo a un paper, apuntando a un trozo concreto de ese
paper. El trozo está debajo.

Pregunta única: **¿ese trozo sostiene lo que la frase le atribuye?**

- NO sostiene si la frase presenta como dicho por el paper algo que el trozo
  no dice: un nombre de módulo inventado, un número que no aparece, una
  conclusión que el trozo no saca, o una relación causal que no está escrita.
- SÍ sostiene si el trozo lo dice o lo deja inferir de forma directa. Una
  paráfrasis en español de una idea en inglés **sí cuenta como sostenida**: no
  exijas coincidencia literal, exige que la idea esté.
- Si el trozo está vacío o es ilegible, responde "SIN_FUENTE".

FRASE:
{sentence}

TROZO CITADO:
{chunk}

Responde con UNA sola palabra, sin explicación: SOSTIENE o NO_SOSTIENE o SIN_FUENTE."""


def critic_claim(sentence: str, chunk: str, *, temperature: float = 0.0) -> str:
    """¿La fuente sostiene lo que esta frase le atribuye?

    Devuelve "SOSTIENE" | "NO_SOSTIENE" | "SIN_FUENTE". `temperature=0` a
    propósito: §4.2 midió que el juez parpadea a temperatura no nula, y un
    veredicto que parpadea no sirve para decidir.
    """
    from bibliotecario.core import llm
    if not chunk.strip():
        return "SIN_FUENTE"
    out = llm.generate(
        _CRITIC_PROMPT.format(sentence=sentence[:900], chunk=chunk[:7000]),
        max_tokens=16, temperature=temperature,
    ).strip().upper()
    if "NO_SOSTIENE" in out:
        return "NO_SOSTIENE"
    if "SIN_FUENTE" in out:
        return "SIN_FUENTE"
    if "SOSTIENE" in out:
        return "SOSTIENE"
    # Errata corregida: antes caía aquí a "SIN_FUENTE", y un fallo de llamada
    # (rate limit, 504, respuesta vacía) se contaba como fabricación. Un fallo
    # del juez no es una mentira del modelo — §7 prohíbe maquillar en los dos
    # sentidos, y este lo maquillaba contra el propio modelo.
    return "FALLO"


def _claim_span(blueprint: str, m: re.Match) -> tuple[int, int]:
    """Extensión de la afirmación que acaba en el puntero `m`.

    Misma lógica que `check_attributions`: el punto inmediatamente previo
    cierra la frase, así que hay que ir a buscar el anterior.
    """
    end_sent = blueprint.rfind(".", 0, m.start())
    if end_sent < 0:
        start = m.start() - _WINDOW
    else:
        prev = max(blueprint.rfind(". ", 0, end_sent - 1),
                   blueprint.rfind("\n", 0, end_sent - 1))
        start = 0 if prev < 0 else prev + 1
    return max(0, start), m.end() + 80


def critic_attributions(blueprint: str, chunks: dict[tuple[int, int], str],
                        *, temperature: float = 0.0,
                        limit: int | None = None) -> dict:
    """Crítica **una llamada por afirmación** (§5.10.2, opción A).

    Se descartó la opción B —una llamada por blueprint— porque §4.2 mide que
    el juez es fiable en lo mecánico y no en lo semántico; apretar ocho
    afirmaciones en un mismo mensaje empeora justo donde ya es malo, y lo hace
    baratísimo. A cuesta ~10k tokens por blueprint y es la única que sostiene
    el argumento.

    `limit` corta el número de afirmaciones criticadas: sirve para probar barato.

    Devuelve `{"violaciones": [...], "fallos": [...]}`. **`fallos` no son
    violaciones**: son llamadas al juez que no se pudieron leer (rate limit,
    504, respuesta vacía). Contarlas como tal inflaría R4 con errores del
    verificador — errata corregida el 2026-10-12.
    """
    seen: set[tuple[int, int]] = set()
    out: list[dict] = []
    fallos: list[dict] = []
    for m in _POINTER.finditer(blueprint):
        if limit is not None and len(out) + len(fallos) >= limit:
            break
        key = (int(m.group(1)), int(m.group(2)))
        s, e = _claim_span(blueprint, m)
        sentence = blueprint[s:e].strip()
        chunk = chunks.get(key, "")
        verdict = critic_claim(sentence, chunk, temperature=temperature)
        if verdict == "FALLO":
            fallos.append({"chunk": f"{key[0]}:{key[1]}", "frase": sentence[:220]})
            continue
        if verdict != "SOSTIENE":
            out.append({"tipo": "puntero_roto" if verdict == "SIN_FUENTE"
                        else "no_sostenida",
                        "chunk": f"{key[0]}:{key[1]}", "pos": m.start(),
                        "span": (s, e), "frase": sentence[:220]})
        seen.add(key)
    return {"violaciones": out, "fallos": fallos}


_DEMOTED = " (propuesta del blueprint)"


def demote_unsupported(blueprint: str, violations: list[dict]) -> tuple[str, dict]:
    """Quita el puntero de las afirmaciones que la fuente no sostiene.

    **No reescribe la frase**: sustituye `[doc:N:M]` por la marca de propuesta
    en la misma posición. La prosa queda intacta palabra por palabra; lo único
    que cambia es que la afirmación deja de presentarse como del paper, y por
    tanto sale del denominador de R4.

    Se procesa de atrás adelante para que los offsets no se muevan.
    """
    marks = {"no_sostenida": 0, "puntero_roto": 0}
    for v in sorted(violations, key=lambda x: -x["pos"]):
        m = _POINTER.match(blueprint, v["pos"])
        if not m:
            continue
        if v["tipo"] == "puntero_roto":
            # Se come tambien un espacio previo suelto: el puntero casi siempre
            # va pegado a la frase («…es 0.125. [doc:1:5]») y dejar el hueco
            # deja «0.125.  » con dos espacios.
            a = m.start()
            if a > 0 and blueprint[a - 1] == " ":
                a -= 1
            blueprint = blueprint[:a] + blueprint[m.end():]
            marks["puntero_roto"] += 1
        else:
            blueprint = blueprint[:m.start()] + _DEMOTED + blueprint[m.end():]
            marks["no_sostenida"] += 1
    return blueprint, marks


def critic_and_demote(blueprint: str, chunks: dict[tuple[int, int], str],
                      *, temperature: float = 0.0,
                      limit: int | None = None) -> dict:
    """Ruta 5 completa: critica y degrada. **Nunca reescribe prosa.**

    `reescrito` se mantiene en False a propósito — es la señal que distingue
    esto de P3, que destruyó el documento en 3 de 3 (§5.8.3).
    """
    res = critic_attributions(blueprint, chunks, temperature=temperature,
                              limit=limit)
    violations = res["violaciones"]
    fixed, marks = demote_unsupported(blueprint, violations)
    return {"blueprint": fixed, "violaciones": violations, "fallos": res["fallos"],
            "marcas": marks, "reescrito": False,
            "degradadas": sum(marks.values())}


# ----------------------------------------------------------- HITO6 (§1.A / §1.B)
#
# El intento 2 (HITO5) logró R4+R5 en 5/5 pagando con el documento: PG salió
# con 488 chars (base 3988) y ReASearch con 440 (un borrador de razonamiento
# del propio modelo), y el juez los aprobó — detecta fabricación, no
# integridad. Aquí lo determinista se aplica PRIMERO (lo que no necesita LLM
# no se le da al LLM) y todo borrador se VALIDA antes de aceptarse.

MIN_FRACCION = 0.5  # HITO6 §2 (V1): salida válida >= 50% de la longitud base.


def encabezados(blueprint: str) -> list[str]:
    """Encabezados `## ` en orden — misma definición literal que G2 (HITO5/6)."""
    return re.findall(r"^##\s+(.+)$", blueprint or "", re.MULTILINE)


def mech_repair(blueprint: str,
                chunks: dict[tuple[int, int], str]) -> tuple[str, dict]:
    """Reparación determinista previa: 0 tokens, sin LLM, sin reescribir prosa.

    1. `normalize_pointers` (§7.1): solo corchetes mal formados.
    2. `demote_unsupported`: puntero a chunk inexistente se quita; término
       ausente se marca «(propuesta del blueprint)». La frase no se toca.
    3. `check_orphan_claims`: cada huérfana recibe la marca R6 al final de su
       propia línea.

    Los chunks deben venir cargados ya sobre el texto normalizado (el runner
    normaliza antes de cargar); aquí normalizar de nuevo es idempotente.
    """
    from bibliotecario.knowledge import study as S

    blueprint, n_norm = S.normalize_pointers(blueprint)
    viols = check_attributions(blueprint, chunks)
    blueprint, marks = demote_unsupported(blueprint, viols)
    orph = check_orphan_claims(blueprint)
    lines = blueprint.splitlines(keepends=True)
    marcadas = 0
    for o in orph:
        i = o["linea"] - 1
        if not 0 <= i < len(lines):
            continue
        line = lines[i]
        nl = re.search(r"\r?\n$", line)
        lines[i] = (line[:nl.start()] + _DEMOTED + line[nl.start():]
                    if nl else line + _DEMOTED)
        marcadas += 1
    return "".join(lines), {
        "normalizados": n_norm,
        "violaciones": len(viols),
        "punteros_quitados": marks["puntero_roto"],
        "marcados_termino": marks["no_sostenida"],
        "huerfanas_marcadas": marcadas,
    }


def validate_structure(base_bp: str, draft_bp: str) -> list[str]:
    """Validación de salida de una reparación (HITO6 §1.B): V1 + V2.

    Devuelve los fallos concretos (lista vacía = aceptado); el runner añade
    V3 (citas resueltas >= base), que necesita puntuar contra el corpus.
    V1 es un endurecimiento de C1 declarado en HITO6 §2: no relaja nada.
    """
    fallos: list[str] = []
    draft = (draft_bp or "").strip()
    if not draft:
        return ["V1: la salida está vacía"]
    if draft.startswith("("):
        fallos.append("V1: no es un blueprint, es una respuesta de emergencia")
    min_len = int(len((base_bp or "").strip()) * MIN_FRACCION)
    if len(draft) < min_len:
        fallos.append(f"V1: {len(draft)} chars < 50% de la base ({min_len})")
    faltan = [h for h in encabezados(base_bp)
              if h not in set(encabezados(draft_bp))]
    if faltan:
        fallos.append("V2: faltan encabezados de la base: "
                      + ", ".join(f"«{h}»" for h in faltan[:8]))
    return fallos


# --------------------------------------------------------- HITO7 (§1 M1 / M2)
#
# El intento 3 midió que la reparación por regeneración no converge para 2 de
# 5 (trunca y pierde encabezados) y que la regeneración de WikiSkill INSERTÓ
# fabricaciones nuevas. Sonda previa a declarar: la localización literal
# frase-del-juez ↔ línea no es viable (LCS medido 8–27 chars: las frases del
# juez son paráfrasis). Aquí el único que entiende la paráfrasis es el LLM,
# y lo único que se le deja devolver son números de línea + eco — la edición
# sigue siendo determinista. **Cero reescritura de blueprint (HITO7 §1.M3).**

_ECO_MIN = 20  # eco mínimo (normalizado) para que una entrada cuente


def localizador_prompt(frases: list[str], blueprint: str) -> str:
    """Prompt del localizador guiado (HITO7 §1.M1; HITO9 §1.A: encabezados
    ancla permitidos con eco, para que M5b reciba material).

    La salida permitida es estrictamente `N -> M | eco` o `N -> -`; el modelo
    nunca ve permitido devolver texto del blueprint, solo apuntar a él.
    """
    lista = "\n".join(f"[{i + 1}] {f}" for i, f in enumerate(frases))
    numerado = "\n".join(f"{i + 1}| {ln}"
                         for i, ln in enumerate(blueprint.splitlines()))
    return f"""Un revisor automático señaló estas frases como problemas en el blueprint.

FRASES SEÑALADAS:
{lista}

BLUEPRINT (cada línea precedida de «N| » con su número de línea):
{numerado}

Para CADA frase, localiza la LÍNEA donde el blueprint afirma o rellena ese
contenido. Responde EXACTAMENTE una línea por frase, en este formato:

  <número de frase> -> <número de línea> | <eco literal de un fragmento de
  esa línea, tal cual aparece, mínimo 20 caracteres>

o, si la frase no corresponde a ninguna línea:

  <número de frase> -> -

Reglas:
- La línea debe existir y no estar vacía.
- Si la afirmación vive en una línea de contenido, apunta a esa línea (no
  empieza por #); si la frase se ancla en un encabezado, apunta al encabezado
  con su eco.
- El eco debe ser texto EXACTO de esa misma línea (puedes recortarlo, no
  cambiarlo).
- No inventes números y no reescribas nada: solo apunta.

Devuelve SOLO las líneas de respuesta, sin nada más."""


_REINTENTO_LOC = """

Tu intento anterior tuvo entradas inválidas:
{fallos}
Corrígelas. Recuerda: eco EXACTO de la línea real, sin cambiar caracteres."""


def localizador_reintento(base_prompt: str, fallos: list[str]) -> str:
    """Bloque de feedback del 1 reintento (HITO6 §1.B aplicado al M1)."""
    return base_prompt + _REINTENTO_LOC.format(
        fallos="\n".join(f"- {x}" for x in fallos))


def parse_localizador(salida: str, blueprint: str,
                      n_frases: int) -> dict:
    """Valida la salida del localizador contra el blueprint real (HITO7 §1.M1;
    HITO8 §1: frases sin entrada acreditadas; HITO9 §1.A+B: encabezados con
    eco válido alimentan M5b, y normalizaciones deterministas de formato
    —separadores, prefijos, negrilla, prefijo del eco— sin relajar nunca el
    eco ≥20 real que decide la verdad; HITO10 §1.A: corchetes `[N]` alrededor
    de frase y destino — la deriva medida en las salidas crudas de H9).

    Devuelve `validas` (números de línea ya saneados), `no_localizadas`,
    `invalidas` (motivos legibles para el feedback), `lineas` (frase→línea)
    y `encabezados` (encabezados con eco válido, materia prima de M5b).
    """
    lines = blueprint.splitlines()
    validas: dict[str, int] = {}
    no_loc: list[int] = []
    invalidas: list[str] = []
    encabs: list[int] = []
    resueltas: set[int] = set()   # frases ya con entrada válida (o «-» o enc.)
    vistas: set[int] = set()      # frases con CUALQUIER entrada parseada
    pat_cab = re.compile(
        r"^\s*\[?\s*(?:frase\s+|Frase\s+)?(\d+)\s*\]?\s*(?:->|:)\s*"
        r"\[?\s*(?:línea\s+|linea\s+|Línea\s+)?(-|\d+)\s*\]?\s*$",
        re.IGNORECASE)
    entradas = 0
    for raw in (salida or "").splitlines():
        raw = re.sub(r"^\s*[-*•]\s+(?=\[?\d)", "", raw)
        if "|" in raw:
            cab, eco = raw.split("|", 1)
            eco = re.sub(r"^\s*\(?\s*eco\s*[:)]\s*", "", eco,
                         flags=re.IGNORECASE)
        else:
            cab, eco = raw, None
        # formato solo del lado de la cabecera: el eco se toca lo mínimo
        cab = (cab.replace("→", "->").replace("⇒", "->")
                  .replace("—", "->").replace("–", "->")
                  .replace("**", "").replace("__", ""))
        m = pat_cab.match(cab)
        if not m:
            continue
        entradas += 1
        n_f, dest = int(m.group(1)), m.group(2)
        if not 1 <= n_f <= n_frases:
            invalidas.append(f"frase {n_f}: número fuera de rango")
            continue
        vistas.add(n_f)
        if n_f in resueltas:
            continue  # ya resuelta; una entrada inválida no tapa su corrección
        if dest == "-":
            no_loc.append(n_f)
            resueltas.add(n_f)
            continue
        ln_i = int(dest)
        if not 1 <= ln_i <= len(lines):
            invalidas.append(f"frase {n_f}: línea {ln_i} fuera de rango")
            continue
        linea = lines[ln_i - 1]
        if not linea.strip():
            invalidas.append(f"frase {n_f}: la línea {ln_i} está vacía")
            continue
        linea_norm = " ".join(linea.split())
        eco_norm = " ".join((eco or "").split())
        es_enc = linea.lstrip().startswith("#")
        if es_enc:
            texto_enc = linea.lstrip("#").strip()   # sin almohadillas
            umbral = max(1, min(_ECO_MIN, len(texto_enc)))
        else:
            umbral = _ECO_MIN
        if len(eco_norm) < umbral:
            invalidas.append(
                f"frase {n_f}: eco demasiado corto"
                + (" para el encabezado" if es_enc else "")
                + (f" de la línea {ln_i}" if es_enc else ""))
            continue
        if eco_norm not in linea_norm:
            invalidas.append(
                f"frase {n_f}: el eco no aparece en "
                + ("el encabezado de la línea " if es_enc else "la línea ")
                + str(ln_i))
            continue
        if es_enc:
            encabs.append(ln_i)     # HITO9 §1.A: ancla en encabezado → M5b
            resueltas.add(n_f)
            continue
        validas[str(n_f)] = ln_i
        resueltas.add(n_f)
    if entradas == 0:
        invalidas.append("salida sin líneas parseables «N -> M | eco»")
    else:
        for n in range(1, n_frases + 1):
            if n not in vistas:
                invalidas.append(f"frase {n}: sin entrada en la salida")
    return {"validas": sorted(set(validas.values())),
            "no_localizadas": no_loc,
            "invalidas": invalidas,
            "lineas": {int(k): v for k, v in validas.items()},
            "encabezados": sorted(set(encabs))}


def marcar_lineas(blueprint: str, lineas: list[int]) -> tuple[str, dict]:
    """Aplica la marca R6 al final de cada línea localizada (HITO7 §1.M2).

    Edición de línea, nunca de frase: los bytes de la prosa quedan intactos.
    Inmune a encabezados, vacíos, números fuera de rango y dobles (defensa en
    profundidad — la validación ya los filtra en `parse_localizador`).
    """
    lines = blueprint.splitlines(keepends=True)
    marcadas = omitidas = 0
    for ln_i in sorted({int(x) for x in lineas}):
        i = ln_i - 1
        if not 0 <= i < len(lines):
            omitidas += 1
            continue
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            omitidas += 1
            continue
        if _DEMOTED in line:
            omitidas += 1
            continue
        nl = re.search(r"\r?\n$", line)
        lines[i] = (line[:nl.start()] + _DEMOTED + line[nl.start():]
                    if nl else line + _DEMOTED)
        marcadas += 1
    return "".join(lines), {"marcadas": marcadas, "omitidas": omitidas}


# --------------------------------------------------------- HITO8 (§1 M5 a/b)
#
# HITO7 midió que la marca R6 no gira el veredicto del juez (WikiSkill: línea
# exacta marcada, misma queja 3 rondas más) y que las quejas ancladas en
# encabezados no son marcables sin romper V2. Aquí el edit se lleva la
# afirmación CITADA del texto: plantilla fija, punteros conservados,
# encabezados byte a byte intactos, 0 generación (HITO8 §1).

MASCARA = "*[contenido retirado: no consta en la fuente]*"


def _mascara_con_punteros(origen: str) -> str:
    """MASCARA + los punteros `[doc:X:Y]` de `origen`, en orden y sin dobles."""
    vistos: set[str] = set()
    extra: list[str] = []
    for a, b in _POINTER.findall(origen or ""):
        t = f"[doc:{a}:{b}]"
        if t not in vistos:
            vistos.add(t)
            extra.append(t)
    return MASCARA + (" " + " ".join(extra) if extra else "")


def editar_m5(blueprint: str, lineas: list[int],
              encabezados: list[int]) -> tuple[str, dict]:
    """M5 completa (HITO8 §1): M5a sobre líneas + M5b sobre cuerpos de
    encabezados, en UN solo pas sobre los índices originales (máscaras y
    vaciados no se pisan ni se desplazan entre sí).

    `lineas`: números 1-based de líneas a reemplazar por la plantilla;
    `encabezados`: números 1-based de encabezados cuyo cuerpo (hasta el
    siguiente `#`) se vacía en una sola línea de plantilla con los punteros
    de todo el cuerpo. El encabezado nunca se modifica.
    """
    lines = blueprint.splitlines(keepends=True)
    a_mascara = {int(x) for x in lineas}
    ancla: dict[int, str] = {}
    borrar: set[int] = set()
    secciones = lineas_vaciadas = omitidas = 0
    for n_enc in sorted({int(x) for x in encabezados}):
        i = n_enc - 1
        if not 0 <= i < len(lines) or not lines[i].lstrip().startswith("#"):
            omitidas += 1
            continue
        cuerpo: list[int] = []
        j = i + 1
        while j < len(lines) and not lines[j].lstrip().startswith("#"):
            cuerpo.append(j)
            j += 1
        if not cuerpo:
            omitidas += 1
            continue
        if len(cuerpo) == 1 and MASCARA in lines[cuerpo[0]]:
            omitidas += 1  # ya vaciada: no-op idempotente
            continue
        texto = "\n".join(lines[k] for k in cuerpo)
        nl = re.search(r"\r?\n$", lines[cuerpo[-1]])
        ancla[cuerpo[0]] = _mascara_con_punteros(texto) + (
            nl.group(0) if nl else "")
        borrar.update(cuerpo[1:])
        secciones += 1
        lineas_vaciadas += len(cuerpo)
    mascaradas = 0
    out: list[str] = []
    for idx, line in enumerate(lines):
        if idx in borrar:
            continue
        if idx in ancla:
            out.append(ancla[idx])
            continue
        cuerpo = re.sub(r"\r?\n$", "", line)
        if (idx + 1) in a_mascara:
            if (cuerpo.strip() and not cuerpo.lstrip().startswith("#")
                    and MASCARA not in cuerpo):
                out.append(_mascara_con_punteros(cuerpo)
                           + line[len(cuerpo):])
                mascaradas += 1
                continue
            omitidas += 1
        out.append(line)
    # números de línea que ni siquiera existen (fuera de rango) también omiten
    omitidas += sum(1 for x in a_mascara if not 1 <= x <= len(lines))
    return "".join(out), {"mascaradas": mascaradas, "secciones": secciones,
                          "lineas_vaciadas": lineas_vaciadas,
                          "omitidas": omitidas}


def mascarar_lineas(blueprint: str, lineas: list[int]) -> tuple[str, dict]:
    """M5a (HITO8 §1): reemplaza cada línea señalada por MASCARA + sus
    punteros. Inmune a encabezados, vacíos, rango y dobles."""
    return editar_m5(blueprint, lineas, [])


def mascara_seccion(blueprint: str, n_enc: int) -> tuple[str, dict]:
    """M5b (HITO8 §1): vacía el cuerpo bajo un encabezado en una línea de
    plantilla; el encabezado queda byte a byte intacto."""
    return editar_m5(blueprint, [], [n_enc])
