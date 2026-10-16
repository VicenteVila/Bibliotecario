"""Tools de dominio del agente: QA sobre papers + consultoría de implementación.

Protocolo: el agente emite ```json {"tool": nombre, "args": {...}}```; el loop valida
(ActionRealization) y ejecuta. Todo devuelve dicts JSON-serializables.
"""
from __future__ import annotations

import json
import logging
import re

from bibliotecario.config import data_dir
from bibliotecario.core import storage
from bibliotecario.core.llm import generate
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import pearl as PEARL
from bibliotecario.memory import retriever

logger = logging.getLogger(__name__)


def search_papers(query: str, top_k: int = 8) -> dict:
    """Búsqueda híbrida con expansión a chunks vecinos (el detalle va en el chunk contiguo)."""
    hits = retriever.search_with_neighbours(query, top_k=max(1, top_k - 2))
    keys = ("score", "doc_id", "chunk", "title", "text")
    return {"hits": [{k: h[k] for k in keys} | ({"neighbour_of": h["neighbour_of"]}
                                                  if "neighbour_of" in h else {}) for h in hits]}


def retrieve_evidence(query: str, top_m: int = 8) -> dict:
    return {"paths": PEARL.retrieve_evidence(query, top_m=top_m)}


def _doc_nchunks(doc_id: int) -> int:
    """Número de chunks de un documento (0 si no se puede leer la DB)."""
    try:
        with storage.get_conn() as conn:
            r = conn.execute("SELECT COUNT(*) n FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()
        return r["n"] if r else 0
    except Exception:
        return 0


def _doc_text(doc_id: int, idx: int) -> str:
    """Texto de un chunk concreto; '' si no existe."""
    try:
        with storage.get_conn() as conn:
            r = conn.execute("SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=?",
                             (doc_id, idx)).fetchone()
        return r["text"] if r else ""
    except Exception:
        return ""


def _doc_keyword_chunks(doc_id: int, question: str, per_doc: int) -> list[dict]:
    """Chunks del documento con más coincidencias léxicas con la pregunta.

    El ranking global (denso+keyword+grafo) favorece los chunks temáticamente
    cercanos; el detalle fino (la cifra exacta, la regla de desempate) está en un
    chunk que comparte vocabulario con la *pregunta* aunque no sea el más cercano.
    Contar ocurrencias de términos dentro del propio documento es determinista y
    barato, y es lo que localiza esos chunks.
    """
    stop = {"when", "which", "does", "the", "and", "for", "how", "what", "with", "that",
            "from", "this", "into", "each", "than", "them", "they", "there", "their"}
    terms = [t for t in re.findall(r"[a-z0-9\-]{4,}", question.lower()) if t not in stop]
    if not terms:
        return []
    try:
        with storage.get_conn() as conn:
            rows = conn.execute("SELECT chunk_idx, text FROM chunks WHERE doc_id=?",
                                (doc_id,)).fetchall()
    except Exception:
        return []
    scored = []
    for r in rows:
        t = (r["text"] or "").lower()
        s = sum(t.count(term) for term in terms)
        if s:
            scored.append({"chunk": r["chunk_idx"], "kw": s, "text": r["text"]})
    scored.sort(key=lambda x: (-x["kw"], x["chunk"]))
    top = scored[: per_doc * 2]
    return top + [{"chunk": c["chunk"], "kw": c["kw"], "text": _doc_text(doc_id, c["chunk"])}
                  for c in top if _doc_text(doc_id, c["chunk"] + 1)][:per_doc]


def _doc_coverage_chunks(doc_id: int, per_doc: int) -> list[dict]:
    """Muestreo uniforme del documento, con ventana de vecinos.

    Complementario al scoring por léxico: garantiza que el apéndice de un paper
    largo siempre se vea, aunque ninguna de sus palabras aparezca en la pregunta.
    """
    n = _doc_nchunks(doc_id)
    if not n:
        return []
    step = max(1, n // max(per_doc, 1))
    seeds = list(range(0, n, step))
    seeds += [c + d for c in list(seeds) for d in (-1, 1) if 0 <= c + d < n]
    out = []
    for c in seeds:
        t = _doc_text(doc_id, c)
        if t:
            out.append({"chunk": c, "text": t})
    return out


def deep_sweep(question: str, per_doc: int = 4) -> dict:
    """Barrido profundo: los mejores chunks por relevancia, léxico y cobertura.

    El detalle muy específico (un tope, una regla de desempate) vive en un chunk que
    el ranking global no alcanza: es el que más palabras de la *pregunta* contiene, o
    bien uno que solo aparece al recorrer el paper entero. Se combinan los tres
    criterios y se ordena por índice para que el agente lea contexto contiguo.
    Determinista: no consume cuota ni introduce varianza.
    """
    hits = retriever.search_with_neighbours(question, top_k=60)
    by_doc: dict[int, list] = {}
    for h in hits:
        by_doc.setdefault(h["doc_id"], []).append(h)
    out = []
    for doc, hs in by_doc.items():
        best = sorted(hs, key=lambda x: -x["score"])[:per_doc]
        picked: dict[int, dict] = {h["chunk"]: h for h in best}
        # léxico: localiza el chunk con los términos exactos de la pregunta
        extra = _doc_keyword_chunks(doc, question, per_doc) + _doc_coverage_chunks(doc, per_doc)
        for c in extra:
            picked.setdefault(c["chunk"], {"score": 0.0, "chunk": c["chunk"],
                                           "title": best[0]["title"], "text": c["text"]})
        rows = [r for r in sorted(picked.values(), key=lambda x: x["chunk"]) if r.get("text")]
        out.append({"doc_id": doc, "title": rows[0]["title"],
                    # sin truncar: el dato concreto suele estar al final del chunk
                    "chunks": [{"chunk": h["chunk"], "score": h["score"], "text": h["text"]}
                               for h in rows]})
    out.sort(key=lambda d: -max(c["score"] for c in d["chunks"]))
    return {"docs": out}


def get_subgraph(query: str, depth: int = 2) -> dict:
    seeds = PEARL.seed_nodes(query)
    nodes, edges = PEARL.contextual_subgraph([s.id for s in seeds], depth=depth)
    labels = {}
    with storage.get_conn() as conn:
        for r in conn.execute("SELECT id, kind, label FROM nodes").fetchall():
            labels[r["id"]] = f"{r['kind']}:{r['label']}"
    return {"seeds": [s.label for s in seeds],
            "nodes": [labels.get(n, str(n)) for n in sorted(nodes)],
            "edges": [f"{labels.get(s, s)} --[{rel}]--> {labels.get(d, d)}" for s, d, rel, _k, _w in edges[:80]]}


def get_paper(doc_id: int) -> dict:
    with storage.get_conn() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        n = conn.execute("SELECT COUNT(*) c FROM chunks WHERE doc_id=?", (doc_id,)).fetchone()["c"]
    if not doc:
        return {"error": f"doc_id {doc_id} inexistente"}
    meta = {}
    try:
        meta = json.loads(doc["metadata"]) if doc["metadata"] else {}
    except ValueError:
        pass
    return {"doc_id": doc_id, "title": doc["title"], "path": doc["path"],
            "chunks": n, "citations": meta.get("citations", {}), "extra": {k: v for k, v in meta.items() if k != "citations"}}


def answer_multi_hop(question: str, top_k: int = 6) -> dict:
    """QA multi-documento con cadena de razonamiento y citas (estilo HotpotQA del Word)."""
    hits = retriever.search(question, top_k=top_k)
    if not hits:
        return {"answer": "", "citations": [], "error": "sin evidencia"}
    ctx = "\n\n".join(f"[{h['doc_id']}:{h['chunk']}] {h['title']}\n{h['text'][:1200]}" for h in hits)
    prompt = ("Responde la pregunta usando SOLO los documentos. Razona encadenando evidencia "
              "entre documentos y cita como [doc:chunk].\n\nPregunta: " + question +
              "\n\nDocumentos:\n" + ctx + "\n\nRespuesta (con citas):")
    answer = generate(prompt, max_tokens=1024)
    if not answer:
        # Fallback extractivo si Gemini no disponible (FallbackPF)
        best = hits[0]
        answer = f"(extractivo) {best['text'][:600]}"
    cites = sorted({(h["doc_id"], h["chunk"]) for h in hits})
    return {"answer": answer, "citations": [f"[{d}:{c}] {next(h['title'] for h in hits if h['doc_id']==d and h['chunk']==c)}" for d, c in cites]}


def _source_for(technique: str, procs, max_chunks: int = 8, max_chars: int = 7000) -> tuple[int | None, str]:
    """Chunks de la fuente de la técnica, para poder atribuir lo que se diga.

    P2 (§5): **no se puede exigir R1-R7 sin el texto al lado.** El prompt
    anterior solo llevaba nombres de procedimientos y cadenas del grafo, así
    que el modelo no tenía nada que citar — y por eso H3 midió 0 citas. Aquí se
    pasan los chunks que nombran esos procedimientos, más el chunk 0 (donde
    están autores y título, que es lo que R7 pide para la bibliografía).
    """
    from bibliotecario.core import storage
    from bibliotecario.knowledge import graph as G

    doc_id = None
    for n in G.find_nodes(technique, kind="technique", limit=5):
        if n.metadata.get("doc_id"):
            doc_id = n.metadata["doc_id"]
            break
    if doc_id is None:
        for p in procs:
            if p.metadata.get("doc_id"):
                doc_id = p.metadata["doc_id"]
                break
    if doc_id is None:
        return None, ""

    with storage.get_conn() as conn:
        # Cabecera (título/autores/sello) + cualquier chunk que nombre un
        # procedimiento: son los que la fuente sostiene de verdad.
        idxs = {0}
        for p in procs:
            for r in conn.execute(
                "SELECT chunk_idx FROM chunks WHERE doc_id=? AND text LIKE ? ORDER BY chunk_idx LIMIT 3",
                (doc_id, f"%{p.label[:28]}%"),
            ).fetchall():
                idxs.add(r["chunk_idx"])
        rows = conn.execute(
            f"SELECT chunk_idx, text FROM chunks WHERE doc_id=? AND chunk_idx IN "
            f"({','.join('?' * len(idxs))}) ORDER BY chunk_idx",
            (doc_id, *sorted(idxs)),
        ).fetchall()

    used = 0
    parts: list[str] = []
    for r in rows:
        piece = f"[chunk {r['chunk_idx']}] {r['text']}"
        if used + len(piece) > max_chars:
            break
        parts.append(piece)
        used += len(piece)
    return doc_id, "\n\n".join(parts[:max_chunks])


# Presupuesto del blueprint. 1500 no alcanzaba: R7 pide la bibliografía al FINAL
# del documento y el corte la pegaba (medido en el A/B, 4/22 truncados).
BLUEPRINT_MAX_TOKENS = 3000

# Reglas R1-R7 de §2.E. Van en el prompt porque son escritura; B7-B11 son la
# prueba mecánica de que se cumplen (§3.1).
#
# R1 lleva además el puntero `[doc:id:chunk]`: la cita en prosa es para el
# lector, el puntero es para que B8 (citas que resuelven) se pueda comprobar
# sin juicio humano. Sin él, la comprobación mecánica no tiene nada que seguir.
_WRITING_RULES = """Reglas de escritura, obligatorias:
R1. **Ancla cada afirmación a una cita literal, en este orden y en la misma línea:**
    «<fragmento textual del paper, tal cual, en su idioma>» [doc:<id>:<chunk>] — <tu paráfrasis en español>.
    Ejemplo correcto: «the framework localizes the active node» [doc:2:41] — el método localiza el nodo activo antes de decidir.
    La cita va **PRIMERO**, entrecomillada, y tiene que ser **idéntica** a un trozo del chunk que hayas visto en FUENTE. Después el puntero. Después tu paráfrasis.
    «Según el paper, el sistema selecciona tareas» a secas **no vale**: es una atribución sin ancla, y sin ancla no se puede comprobar nada.
    **R1 es suelo: sin cita literal + puntero no hay salvación por ninguna otra regla.**
    **Única excepción (dec. 15)**: las declaraciones de silencio de R5 («el paper no especifica/describe/indica…») **no llevan cita porque no tienen fuente que citar** — llevan la marca de R6. Una frase que declara un hueco no es una atribución. Fuera de esa excepción, R1 sigue siendo suelo sin tocar.
R2. Comillas ⇔ literal, sin excepción: entrecomilla **solo** fragmentos idénticos a la fuente. Si cambias una palabra, no va entrecomillado — va en tu paráfrasis, después de la cita.
R3. La paráfrasis va **después de la cita y el puntero, en la misma línea**, y no añade nada que la cita no sostenga: tus palabras explican la cita, no la extienden. Si necesitas ir más allá de lo que la cita dice, eso ya no es paráfrasis — es R4 y R6.
R4. No presentes como de la fuente algo que no esté en FUENTE. Puentear hacia un objetivo que la fuente no trata está permitido **solo si la frase lleva la marca de la regla R6 junto a la afirmación** — misma línea o la inmediatamente siguiente.
R5. Declara los silencios: si la fuente no especifica un detalle (cómo se fija un umbral, qué hacer con X), dilo — «el paper no especifica …» — en vez de rellenarlo.
R6. Separa lo tuyo de lo de la fuente **EN LA PROPIA FRASE**: escribe «(propuesta del blueprint)» o «(el paper no lo especifica)» **en la misma línea, o en la línea justo debajo del mismo punto**. Una marca en otra sección no vale: no se puede saber a que afirmación se refiere, y se lee como si fuera del paper. Nota: R6 no tapa R1 — si la frase atribuye algo al paper, lleva cita literal + puntero, aunque también diga que es propuesta.
R8. **Cada módulo y cada dependencia lleva su propia cita dentro del propio punto.** Una cita en la cabecera de la sección («Según X [doc:0:0], los siguientes módulos son…») **no cubre los puntos de debajo**: cada módulo que enumeres necesita su cita literal + puntero **en su propia línea**, con el formato exacto de R1: «…» [doc:<id>:<chunk>]. **El puntero es `[doc:<id>:<chunk>]` y nada más**: «citado en §3.2.1», «(Figura 2)», «(ecuación 4)» o «Yang et al. 2026» **no son punteros** y no cuentan como cita. Si el módulo es propuesta tuya y no del paper, márcalo con R6 («(propuesta del blueprint)») **en vez** de citarlo: no le pongas un puntero que no hay. No vale citar solo el primero y dejar el resto sin ancla.
R7. **Última sección del documento, sin falta**: «## Bibliografía», listando SOLO los documentos realmente consultados, cada uno con autores y año **tal como aparecen en la fuente** más su [doc:<id>]. Si no puedes extraer autores o año, di «no consta en la fuente»; no los inventes."""


def build_blueprint(technique: str, goal: str, extra_source: str = "") -> dict:
    """Blueprint de implementación: camina el grafo procedimental y sintetiza guía accionable.

    P2 (§5): el prompt exige R1-R7 y va **con el texto de la fuente al lado**,
    que es lo único que permite cumplirlas. Sin fuente no hay cita posible y la
    exigencia sería papel mojado.

    `extra_source` lo pasa P1' (el brazo C del A/B): la evidencia que el loop
    reunió con las herramientas. En el brazo B va vacío, que es la condición
    de un solo `generate()`.
    """
    from bibliotecario.knowledge import procedural as P
    procs = P.list_procedures(technique=technique)
    if not procs:
        # N1 (§3.4). Antes: `or P.list_procedures()` tiraba el grafo entero al
        # prompt — H5 lo tapó porque el modelo se negó por su cuenta, una vez.
        # Hoy se niega el código: no se escribe blueprint de algo sin respaldo.
        return {"technique": technique, "goal": goal, "procedures": [],
                "blueprint": f"(no existe: no hay ningun procedimiento registrado para '{technique}' en el grafo)"}
    names = [p.label for p in procs[:20]]
    paths = PEARL.retrieve_evidence(f"{technique} {goal}", top_m=5)
    chain = "\n".join(" → ".join(f"{s['label']}" for s in p["steps"]) for p in paths)
    doc_id, source = _source_for(technique, procs)
    if extra_source:
        source = f"{source}\n\n[evidencia reunida por el loop]\n{extra_source}" if source else extra_source
    if not source:
        # Sin fuente no se puede cumplir R1-R7; se declara en vez de fingir.
        return {"technique": technique, "goal": goal, "procedures": names, "doc_id": doc_id,
                "blueprint": "(sin fuente: no hay chunks de la técnica, no se puede escribir con cita)"}
    prompt = (
        f"Escribe un blueprint de implementación de la técnica '{technique}' "
        f"con objetivo: {goal}.\n\n"
        f"FUENTE (únicas fuentes disponibles; no hay más):\n{source}\n\n"
        f"Procedimientos registrados en el grafo desde esa fuente: {', '.join(names)}\n"
        f"Cadenas del grafo:\n{chain}\n\n"
        f"{_WRITING_RULES}\n\n"
        "Devuelve blueprint markdown: módulos, dependencias, orden, validación, "
        "riesgos, y la bibliografía."
    )
    # 1500 tokens cortaba la bibliografía: va al FINAL del documento, así que es
    # lo primero que se pierde. Medido en el A/B — 4 de 22 blueprints salieron
    # truncados. Se sube el tope; el coste por blueprint sube y hay que decirlo.
    bp = generate(prompt, max_tokens=BLUEPRINT_MAX_TOKENS) or "(sin LLM: usa los procedimientos listados)"
    return {"technique": technique, "goal": goal, "procedures": names,
            "doc_id": doc_id, "blueprint": bp}


def _cited_chunks(doc_id: int | None, blueprint: str) -> dict[tuple[int, int], str]:
    """Carga el texto de los chunks que el blueprint cita, para verificarlos."""
    if doc_id is None:
        return {}
    import re as _re
    pairs = {(int(d), int(c)) for d, c in _re.findall(r"\[doc:(\d+):(\d+)\]", blueprint)}
    if not pairs:
        return {}
    from bibliotecario.core import storage
    out: dict[tuple[int, int], str] = {}
    with storage.get_conn() as conn:
        for d, c in sorted(pairs):
            row = conn.execute("SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=?",
                               (d, c)).fetchone()
            if row:
                out[(d, c)] = row["text"]
    return out


def build_blueprint_verified(technique: str, goal: str, extra_source: str = "") -> dict:
    """P3 (§5): genera, **verifica la atribución** y reescribe una vez si falla.

    Por qué existe: el A/B midió que P2+P1' arreglan la forma —citas que
    resuelven, bibliografía, cero plagio— pero no la sustancia: 11 de 15
    blueprints del brazo C atribuían a la fuente cosas que la fuente no dice
    (2,67 de media). Las siete reglas en el prompt no bastan. Aquí se comprueba
    cada atribución contra el chunk citado y se devuelve al modelo **con las
    violaciones concretas**, que es una instrucción que sí se puede seguir.

    Cuesta dos `generate()`. Solo paga la segunda si la primera fabrica.
    """
    bp = build_blueprint(technique, goal, extra_source=extra_source)
    return verify_and_repair(bp)


def verify_and_repair(bp: dict) -> dict:
    """P3 sobre un blueprint ya generado (por `build_blueprint` o por el loop).

    Se separa de `build_blueprint_verified` para poder componer: el brazo D del
    A/B es P1' + P2 + P3 — el loop reúne la evidencia, la tool escribe, y
    **entonces** se verifica. Aplicar P3 sobre el camino de un solo `generate()`
    pierde lo único que P1' aportaba (citas que resuelven), y así salió la
    primera versión del brazo D: B8=0,00.
    """
    from bibliotecario.agent import attribution as A

    if not bp.get("blueprint") or bp["blueprint"].startswith("("):
        return {**bp, "verificado": False, "violaciones": []}

    pointers = A._POINTER.findall(bp["blueprint"])
    chunks = _cited_chunks(bp.get("doc_id"), bp["blueprint"])
    # Un blueprint sin punteros no está "verificado": no hay nada que comprobar.
    # Marcarlo como limpio sería mentir con el mismo número (medido: una run de
    # Task-CoEvolve salió `verificado=True` con 0 citas).
    if not pointers:
        return {**bp, "verificado": None, "sin_punteros": True, "violaciones": []}
    v1 = A.check_attributions(bp["blueprint"], chunks)
    if not v1:
        return {**bp, "verificado": True, "violaciones": [], "reescrituras": 0}

    repair = generate(A._repair_prompt(bp["blueprint"], v1),
                      max_tokens=BLUEPRINT_MAX_TOKENS)
    if not repair:
        # Sin reescritura posible: se devuelve el original **con las
        # violaciones marcadas**, no un blueprint que parece limpio.
        return {**bp, "verificado": False, "violaciones": v1, "reescrituras": 0}

    chunks2 = _cited_chunks(bp.get("doc_id"), repair)
    v2 = A.check_attributions(repair, chunks2)
    return {**bp, "blueprint": repair, "verificado": not v2,
            "violaciones": v2, "violaciones_previas": len(v1), "reescrituras": 1}


def verify_and_mark(bp: dict) -> dict:
    """P3 en modo informe: **marca** las violaciones, no reescribe.

    Por qué existe y no se sustituye a `verify_and_repair`: la reescritura se
    midió en el brazo D del A/B y empeora el blueprint — las 3 runs que tocó
    salieron peor, perdiendo la bibliografía (R7) y los silencios (R5), y una
    acabó con más violaciones de las que tenía (§5.8.3). Pid «el blueprint
    completo ya corregido» y el modelo regenera el documento entero en vez de
    corregir lo señalado.

    Aquí no se pide eso: se devuelven las violaciones **junto** al blueprint
    original, sin tocarlo. Cuesta cero `generate()` extra y el responsable
    decide. R6 cubre el caso de no saber: una violación puede ser un término
    legítimo que simplemente no está en ese chunk.
    """
    from bibliotecario.agent import attribution as A

    if not bp.get("blueprint") or bp["blueprint"].startswith("("):
        return {**bp, "verificado": False, "violaciones": []}

    pointers = A._POINTER.findall(bp["blueprint"])
    if not pointers:
        return {**bp, "verificado": None, "sin_punteros": True, "violaciones": []}
    v = A.check_attributions(bp["blueprint"], _cited_chunks(bp.get("doc_id"), bp["blueprint"]))
    return {**bp, "verificado": not v, "violaciones": v, "reescrituras": 0}


def build_blueprint_p4(technique: str, goal: str) -> dict:
    """P1' + P2 + P4 sin reescritura — la composición del brazo E (§5.9).

    El loop reúne la evidencia, `build_blueprint` escribe con las reglas
    actuales (R1-R8) y `verify_and_mark` devuelve el informe de atribución
    **sin tocar el texto**: cero `generate()` extra y el blueprint queda
    byte-idéntico al del mismo loop sin P4.

    Ruta del arnés (Hito 3, Fase 1, declarada 2026-10-16): es la única
    candidata que verifica sin reescribir. `verify_and_repair` midió
    empeorar (§5.8.3, D: R4 7/15) y `critic_and_demote` está descartada
    (§8.4.1: B8 7,40 → 2,87 · R4 4/15). Sobre el texto de G — único brazo
    con R4 (8/15) y R5 (13/15) medidas con el juez calibrado (§8.12/§8.13)
    — añade la comprobación que G no hacía.
    """
    from bibliotecario.agent import loop as LOOP

    return verify_and_mark(LOOP.run_blueprint(technique, goal))


def instantiate_agent_template(technique: str, goal: str) -> dict:
    """Genera plantilla mínima de agente instanciable desde el blueprint (decisión 1).

    Hito 3, Fase 1 (declarado 2026-10-16): pasa por `build_blueprint_p4`,
    la ruta verificada (hueco A del plan), y no por `build_blueprint` crudo.
    Un arnés generado por el camino crudo podía salir con peor integridad que
    los blueprints ya medidos del Hito 2: eran dos recetas distintas para la
    misma promesa (H1 ratificada).
    """
    bp = build_blueprint_p4(technique, goal)
    slug = "".join(c if c.isalnum() else "-" for c in technique.lower())[:40].strip("-")
    outdir = data_dir() / "agents" / slug
    outdir.mkdir(parents=True, exist_ok=True)
    # D (§2.D, dec. 13): el estado se CALCULA en runtime, no se escribe aquí.
    # Antes el literal "todo" estaba en este fichero, así que el resultado se
    # sabía antes de correrlo — 0 de 20 pasos se ejecutaron jamás (§8.6).
    code = f'''"""Agente {technique} — plantilla generada por Bibliotecario.
Objetivo: {goal}
Procedimientos: {", ".join(bp["procedures"][:8])}

Cada paso consulta el corpus con su nombre de procedimiento y guarda el estado
con score >= 0.30, `empty` si no llega, `error` si falla. Ningún estado está
escrito en este fichero (dec. 13, D2, 2ª enmienda).
"""
STEPS = {bp["procedures"][:8]!r}


def run(context: dict) -> dict:
    objetivo = str((context or {{}}).get("objetivo", "") or "")
    trace = []
    for step in STEPS:
        consulta = f"{{step}} {{objetivo}}".strip()
        try:
            from bibliotecario.agent.tools import deep_sweep
            docs = (deep_sweep(consulta) or {{}}).get("docs", [])
            mejor = max((c["score"] for d in docs for c in d["chunks"]), default=0.0)
            # Umbral 0.30 fijado en la 2ª enmienda de dec. 13: deep_sweep
            # devuelve docs para cualquier cadena, asi que "hay docs" no
            # discrimina. Hueco medido: sin sentido <=0.154, real >=0.546.
            if docs and mejor >= 0.30:
                status = "done"
                detalle = f"{{len(docs)}} docs, mejor score {{mejor:.3f}}"
            else:
                status = "empty"
                detalle = f"{{len(docs)}} docs, mejor score {{mejor:.3f}} < 0.30"
        except Exception as exc:  # noqa: BLE001 — un paso que falla no tumba el trace
            status, detalle = "error", f"{{type(exc).__name__}}: {{exc}}"
        trace.append({{"step": step, "status": status, "detalle": detalle}})
    return {{"technique": "{technique}", "goal": "{goal}", "trace": trace}}
'''
    (outdir / "agent_template.py").write_text(code, encoding="utf-8")
    (outdir / "BLUEPRINT.md").write_text(f"# {technique}\n\nObjetivo: {goal}\n\n{bp['blueprint']}\n", encoding="utf-8")
    return {"dir": str(outdir), "files": ["agent_template.py", "BLUEPRINT.md"],
            "procedures": bp["procedures"], "blueprint": bp.get("blueprint", ""),
            "violaciones": bp.get("violaciones"), "verificado": bp.get("verificado")}


def register_skill(name: str, skill_md: str, purpose_md: str = "") -> dict:
    with storage.get_conn() as conn:
        conn.execute("INSERT INTO skills (name, skill_md, purpose_md) VALUES (?,?,?) "
                     "ON CONFLICT(name) DO UPDATE SET skill_md=excluded.skill_md, "
                     "purpose_md=excluded.purpose_md, updated_at=datetime('now')",
                     (name, skill_md, purpose_md))
    return {"ok": True, "name": name}


def get_status() -> dict:
    with storage.get_conn() as conn:
        docs = conn.execute("SELECT COUNT(*) c FROM documents").fetchone()["c"]
        chunks = conn.execute("SELECT COUNT(*) c FROM chunks").fetchone()["c"]
        lessons = conn.execute("SELECT COUNT(*) c FROM lessons").fetchone()["c"]
        skills = conn.execute("SELECT COUNT(*) c FROM skills").fetchone()["c"]
        runs = conn.execute("SELECT COUNT(*) c FROM harness_runs").fetchone()["c"]
    return {"documents": docs, "chunks": chunks, **G.stats(), "lessons": lessons,
            "skills": skills, "harness_runs": runs}


TOOLS: dict[str, dict] = {
    "search_papers": {"fn": search_papers, "description": "Búsqueda híbrida sobre chunks de papers",
                      "parameters": {"type": "object", "properties": {
                          "query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}},
                          "required": ["query"]}},
    "retrieve_evidence": {"fn": retrieve_evidence, "description": "Caminos de razonamiento PEARL sobre el grafo",
                          "parameters": {"type": "object", "properties": {
                              "query": {"type": "string"}, "top_m": {"type": "integer", "default": 8}},
                              "required": ["query"]}},
    "deep_sweep": {"fn": deep_sweep, "description": "Barrido profundo: mejores chunks de cada paper relevante "
                                                   "(para detalles que el top-6 no alcanza; sin coste LLM)",
                   "parameters": {"type": "object", "properties": {
                       "question": {"type": "string"}, "per_doc": {"type": "integer", "default": 4}},                       "required": ["question"]}},
    "get_subgraph": {"fn": get_subgraph, "description": "Subgrafo contextual alrededor de la consulta",
                     "parameters": {"type": "object", "properties": {
                         "query": {"type": "string"}, "depth": {"type": "integer", "default": 2}},
                         "required": ["query"]}},
    "get_paper": {"fn": get_paper, "description": "Metadata, citas y nº chunks de un documento",
                  "parameters": {"type": "object", "properties": {"doc_id": {"type": "integer"}},
                                 "required": ["doc_id"]}},
    "answer_multi_hop": {"fn": answer_multi_hop, "description": "Responde con razonamiento multi-documento y citas",
                         "parameters": {"type": "object", "properties": {
                             "question": {"type": "string"}, "top_k": {"type": "integer", "default": 6}},
                             "required": ["question"]}},
    "build_blueprint": {"fn": build_blueprint, "description": "Guía accionable para implementar una técnica",
                        "parameters": {"type": "object", "properties": {
                            "technique": {"type": "string"}, "goal": {"type": "string"}},
                            "required": ["technique", "goal"]}},
    "instantiate_agent_template": {"fn": instantiate_agent_template,
                                   "description": "Genera plantilla de agente instanciable + BLUEPRINT.md",
                                   "parameters": {"type": "object", "properties": {
                                       "technique": {"type": "string"}, "goal": {"type": "string"}},
                                       "required": ["technique", "goal"]}},
    "register_skill": {"fn": register_skill, "description": "Registra/actualiza una skill ejecutable",
                       "parameters": {"type": "object", "properties": {
                           "name": {"type": "string"}, "skill_md": {"type": "string"},
                           "purpose_md": {"type": "string", "default": ""}},
                           "required": ["name", "skill_md"]}},
    "get_status": {"fn": get_status, "description": "Estado del sistema (docs, grafo, lessons, runs)",
                   "parameters": {"type": "object", "properties": {}}},
}


def tool_schemas() -> list[dict]:
    """Schemas estilo function-calling para el harness contract layer."""
    return [{"type": "function", "function": {"name": n, "description": t["description"],
                                              "parameters": t["parameters"]}} for n, t in TOOLS.items()]
