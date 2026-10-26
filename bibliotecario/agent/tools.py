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
from bibliotecario.core.tokens import count_terms, token_list, tokens
from bibliotecario.knowledge import graph as G
from bibliotecario.knowledge import pearl as PEARL
from bibliotecario.memory import memory_tree as MT
from bibliotecario.memory import retriever

logger = logging.getLogger(__name__)


def search_papers(query: str, top_k: int = 8) -> dict:
    """Búsqueda híbrida con expansión a chunks vecinos (el detalle va en el chunk contiguo)."""
    hits = retriever.search_with_neighbours(query, top_k=max(1, top_k - 2))
    keys = ("score", "doc_id", "chunk", "title", "text")
    return {"hits": [{k: h[k] for k in keys} | ({"neighbour_of": h["neighbour_of"]}
                                                  if "neighbour_of" in h else {}) for h in hits]}


def retrieve_evidence(query: str, top_m: int = 8) -> dict:
    """Evidencia del grafo, filtrada por la misma capa que el retriever.

    PEARL devuelve caminos por nodos, no por consulta de texto: si el filtro
    de capas (BIBLIOTECARIO_CAPAS) solo se aplicara en retriever.search(), la
    tool de evidencia seguiría exponiendo papers fuera de capa y el filtro no
    sería real. Los caminos sin ningún doc_id permitido se descartan.
    """
    paths = PEARL.retrieve_evidence(query, top_m=top_m)
    if retriever.allowed_capas() is None:
        return {"paths": paths}
    kept = [p for p in paths if retriever.docs_in_allowed_capa(p.get("doc_ids") or [])]
    return {"paths": kept}


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
    barato, y es lo que localiza esos chunks. Los términos y el conteo vienen del
    tokenizador compartido: tokens **exactos**, nunca subcadenas (`"use"` dentro
    de `"users"`), y con la stoplist común en vez de una guillotina de longitud
    que se comía `RAG`, `OCR` y las cifras.
    """
    terms = token_list(question)
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
        s = count_terms(r["text"] or "", terms)
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


def _fuente_chunks(technique: str, procs,
                   max_chunks: int = 8) -> tuple[int | None, list[tuple[int, str]]]:
    """Selección de chunks de la fuente de la técnica: (doc_id, [(chunk_idx, texto)]).

    Compartida por `_source_for` (legacy) y `_fuente_numerada` (posicional):
    la selección es la misma; lo que cambia es el formato de citado.
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
        return None, []

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
    return doc_id, [(r["chunk_idx"], r["text"]) for r in rows[:max_chunks]]


def _source_for(technique: str, procs, max_chunks: int = 8, max_chars: int = 7000) -> tuple[int | None, str]:
    """Chunks de la fuente de la técnica, para poder atribuir lo que se diga.

    P2 (§5): **no se puede exigir R1-R7 sin el texto al lado.** El prompt
    anterior solo llevaba nombres de procedimientos y cadenas del grafo, así
    que el modelo no tenía nada que citar — y por eso H3 midió 0 citas. Aquí se
    pasan los chunks que nombran esos procedimientos, más el chunk 0 (donde
    están autores y título, que es lo que R7 pide para la bibliografía).
    """
    doc_id, chunks = _fuente_chunks(technique, procs, max_chunks=max_chunks)
    if doc_id is None:
        return None, ""

    used = 0
    parts: list[str] = []
    for idx, text in chunks:
        piece = f"[chunk {idx}] {text}"
        if used + len(piece) > max_chars:
            break
        parts.append(piece)
        used += len(piece)
    return doc_id, "\n\n".join(parts)


def _toks(text: str) -> set[str]:
    return tokens(text)


def _fuente_numerada(technique: str, procs, max_chunks: int = 8,
                     max_chars: int = 7000) -> tuple[int | None, str, dict[int, tuple[int, int]]]:
    """Igual selección que `_source_for`, pero citable solo por posición.

    Presenta cada chunk como `[1]`, `[2]`… — sin `doc_id` ni `chunk_idx` a la
    vista. El modelo no puede fabricar identificadores que no ve: solo indices
    pequeños que este módulo mapea después. Devuelve además
    `mapa: {posición: (doc_id, chunk_idx)}` para `map_positional_citations`.
    """
    doc_id, chunks = _fuente_chunks(technique, procs, max_chunks=max_chunks)
    if doc_id is None:
        return None, "", {}

    used = 0
    parts: list[str] = []
    mapa: dict[int, tuple[int, int]] = {}
    for pos, (idx, text) in enumerate(chunks, start=1):
        piece = f"[{pos}] {text}"
        if used + len(piece) > max_chars:
            break
        mapa[pos] = (doc_id, idx)
        parts.append(piece)
        used += len(piece)
    return doc_id, "\n\n".join(parts), mapa


# Cita posicional `[N]`. No toca `[doc:X:Y]` (los dos puntos rompen el patrón),
# así que un blueprint legacy que mezcle formatos no se corrompe.
_POS_CITE = re.compile(r"\[\s*(\d{1,3})\s*\]")


def map_positional_citations(text: str, mapa: dict[int, tuple[int, int]]) -> tuple[str, dict]:
    """`[N]` → `[doc:doc_id:chunk_idx]`; índice fuera de rango → `[doc:0:0]`.

    Determinista, sin LLM y solo sobre tokens entre corchetes — la doctrina de
    `normalize_pointers`: no se reescribe prosa (P3 destruyó el documento
    reescribiéndola, §5.8.3). `[doc:0:0]` es un destino que nunca resuelve, así
    que el `check_attributions` existente lo caza como `puntero_roto` sin
    máquina nueva aguas abajo.
    """
    mapeados = fuera = 0

    def _sub(m: re.Match) -> str:
        nonlocal mapeados, fuera
        dest = mapa.get(int(m.group(1)))
        if dest is None:
            fuera += 1
            return "[doc:0:0]"
        mapeados += 1
        return f"[doc:{dest[0]}:{dest[1]}]"

    out = _POS_CITE.sub(_sub, text or "")
    return out, {"mapeados": mapeados, "fuera_de_rango": fuera}


def fuente_verificable(technique: str, blueprint: str,
                       procs=None, doc_id: int | None = None,
                       max_chars: int = 9000) -> tuple[int | None, str]:
    """HITO12 §1.A — ventana de verificación POR BLUEPRINT (enmienda 1, E12).

    `_source_for` muestrea chunks con `LIKE` sobre etiquetas de procedimiento
    (ES) contra el paper (EN) y devuelve ≤10,4% de la fuente (0,86% en
    ReASearch): el juez declara «el texto fuente no menciona…» sin ver el
    texto. Aquí la ventana es: chunk 0 del documento propio (título) + chunks
    citados por el propio `bp` vía `[doc:X:Y]` + top-10 del documento propio
    por score híbrido (0,5 densa local + 0,3 keyword, sin LLM ni cuota)
    contra `bp[:2500]`. Mismo formato `[chunk i]` y mismo pre-recorte a
    `max_chars` que `_source_for`. Devuelve (doc_id, ventana).
    """
    from bibliotecario.knowledge import procedural as P

    if doc_id is None:
        if procs is None:
            procs = P.list_procedures(technique=technique)
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

    cites: list[tuple[int, int]] = []
    for d, c in re.findall(r"\[doc:(\d+):(\d+)\]", blueprint or ""):
        t = (int(d), int(c))
        if t not in cites:
            cites.append(t)

    q = (blueprint or "")[:2500]
    try:
        import numpy as np

        from bibliotecario.core.embeddings import blob_to_vec, encode_one

        qvec = encode_one(q)
    except Exception:
        qvec = None
    qtok = _toks(q)

    with storage.get_conn() as conn:
        propios = conn.execute(
            "SELECT chunk_idx, text, embedding FROM chunks WHERE doc_id=? "
            "ORDER BY chunk_idx", (doc_id,)).fetchall()
        scored: list[tuple[float, int]] = []
        for r in propios:
            dense = 0.0
            if qvec is not None and r["embedding"]:
                dense = float(np.dot(qvec, blob_to_vec(r["embedding"])))
            kw = len(qtok & _toks(r["text"])) / max(1, len(qtok))
            scored.append((0.5 * dense + 0.3 * kw, r["chunk_idx"]))
        scored.sort(key=lambda x: (-x[0], x[1]))
        top10 = [c for _, c in scored[:10]]

        texto: dict[tuple[int, int], str] = {}
        for r in propios:
            texto[(doc_id, r["chunk_idx"])] = r["text"]
        faltan = [(d, c) for d, c in cites if (d, c) not in texto]
        if faltan:
            for d in sorted({d for d, _ in faltan}):
                for r in conn.execute(
                        "SELECT chunk_idx, text FROM chunks WHERE doc_id=?",
                        (d,)).fetchall():
                    texto[(d, r["chunk_idx"])] = r["text"]

    orden: list[tuple[int, int]] = []
    if (doc_id, 0) in texto:
        orden.append((doc_id, 0))
    for c in cites:
        if c not in orden and c in texto:
            orden.append(c)
    for c in top10:
        if (doc_id, c) not in orden and (doc_id, c) in texto:
            orden.append((doc_id, c))

    used = 0
    parts: list[str] = []
    for key in orden:
        piece = f"[chunk {key[1]}] {texto[key]}"
        if used + len(piece) > max_chars:
            break
        parts.append(piece)
        used += len(piece)
    return doc_id, "\n\n".join(parts)


def fuente_completa(technique: str, procs=None,
                    doc_id: int | None = None) -> tuple[int | None, str]:
    """HITO13 §1.B — enmienda 2: TODOS los chunks del documento propio.

    Sin recorte aquí (el cap vive en `q1`: `FUENTE_MAX=160000` en
    `eval_q1_r4r5.py`); formato `[chunk i]` idéntico a las ventanas
    anteriores para que el prompt lea la misma estructura.
    """
    from bibliotecario.knowledge import procedural as P

    if doc_id is None:
        if procs is None:
            procs = P.list_procedures(technique=technique)
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
        rows = conn.execute(
            "SELECT chunk_idx, text FROM chunks WHERE doc_id=? "
            "ORDER BY chunk_idx", (doc_id,)).fetchall()
    if not rows:
        return doc_id, ""
    return doc_id, "\n\n".join(
        f"[chunk {r['chunk_idx']}] {r['text']}" for r in rows)


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

# Variante posicional de las reglas (brazo de citas por índice). Idéntica en
# sustancia; cambia SOLO el formato del puntero: `[N]` en vez de
# `[doc:<id>:<chunk>]`, y añade R0 — el modelo nunca escribe identificadores,
# porque el identificador es justo lo que medía fabricar (doc_id invisible en
# FUENTE: `_source_for` nunca lo mostraba y el modelo lo adivinaba).
_WRITING_RULES_NUM = """R0. **El único puntero permitido es el número de candidato `[N]`**, tal como
    aparece en FUENTE («[1]», «[2]»…). No escribas `[doc:…]`, ni ids de
    documento, ni «chunk N»: si un número no está en FUENTE, no existe.
    La sección «evidencia reunida por el loop», si aparece, es ORIENTATIVA:
    no la cites ni la parafrasees como fuente — solo puedes citar [N].
""" + _WRITING_RULES.replace(
    "«<fragmento textual del paper, tal cual, en su idioma>» [doc:<id>:<chunk>] — <tu paráfrasis en español>.",
    "«<fragmento textual del paper, tal cual, en su idioma>» [N] — <tu paráfrasis en español>.",
).replace(
    "Ejemplo correcto: «the framework localizes the active node» [doc:2:41] — el método localiza el nodo activo antes de decidir.",
    "Ejemplo correcto: «the framework localizes the active node» [3] — el método localiza el nodo activo antes de decidir.",
).replace(
    "con el formato exacto de R1: «…» [doc:<id>:<chunk>]. **El puntero es `[doc:<id>:<chunk>]` y nada más**",
    "con el formato exacto de R1: «…» [N]. **El puntero es `[N]` y nada más**",
).replace(
    "«Según X [doc:0:0], los siguientes módulos son…»",
    "«Según X [1], los siguientes módulos son…»",
).replace(
    "más su [doc:<id>]", "más su [N]",
)


def build_blueprint(technique: str, goal: str, extra_source: str = "",
                    positional: bool = False,
                    temperature: float | None = None) -> dict:
    """Blueprint de implementación: camina el grafo procedimental y sintetiza guía accionable.

    P2 (§5): el prompt exige R1-R7 y va **con el texto de la fuente al lado**,
    que es lo único que permite cumplirlas. Sin fuente no hay cita posible y la
    exigencia sería papel mojado.

    `extra_source` lo pasa P1' (el brazo C del A/B): la evidencia que el loop
    reunió con las herramientas. En el brazo B va vacío, que es la condición
    de un solo `generate()`.

    `positional=True` (brazo posicional del A/B): la fuente se presenta como
    candidatos `[1]`..`[N]` sin doc_id visible, y tras generar se mapean a
    `[doc:X:Y]` por código (`map_positional_citations`). El modelo no escribe
    identificadores — el doc_id no está en FUENTE legacy y el modelo lo
    adivinaba, que es una fuente de `puntero_roto` medible sin juez.
    Por defecto False: el camino legacy queda byte-idéntico.

    `temperature` (None = default del backend, 0.2) se expone para poder medir
    temp 0 en el A/B sin cambiar la ruta por defecto.
    """
    from bibliotecario.knowledge import procedural as P
    procs = P.list_procedures(technique=technique)
    if not procs:
        # N1 (§3.4). Antes: `or P.list_procedures()` tiraba el grafo entero al
        # prompt — H5 lo tapó porque el modelo se negó por su cuenta, una vez.
        # Hoy se niega el código: no se escribe blueprint de algo sin respaldo.
        return {"technique": technique, "goal": goal, "procedures": [],
                "blueprint": f"(no existe: no hay ningun procedimiento registrado para '{technique}' en el grafo)",
                "citas_posicionales": None}
    names = [p.label for p in procs[:20]]
    paths = PEARL.retrieve_evidence(f"{technique} {goal}", top_m=5)
    # Cadena de evidencia: misma capa que retrieve_evidence (labels visibles
    # en el prompt). La fuente de chunks (procedure → doc) es flujo de
    # blueprint y no lleva filtro: los blueprints leen fundacional+extendido.
    if retriever.allowed_capas() is not None:
        paths = [p for p in paths if retriever.docs_in_allowed_capa(p.get("doc_ids") or [])]
    chain = "\n".join(" → ".join(f"{s['label']}" for s in p["steps"]) for p in paths)
    mapa: dict[int, tuple[int, int]] = {}
    if positional:
        doc_id, source, mapa = _fuente_numerada(technique, procs)
        reglas = _WRITING_RULES_NUM
    else:
        doc_id, source = _source_for(technique, procs)
        reglas = _WRITING_RULES
    if extra_source:
        source = f"{source}\n\n[evidencia reunida por el loop]\n{extra_source}" if source else extra_source
    if not source:
        # Sin fuente no se puede cumplir R1-R7; se declara en vez de fingir.
        return {"technique": technique, "goal": goal, "procedures": names, "doc_id": doc_id,
                "blueprint": "(sin fuente: no hay chunks de la técnica, no se puede escribir con cita)",
                "citas_posicionales": None}
    prompt = (
        f"Escribe un blueprint de implementación de la técnica '{technique}' "
        f"con objetivo: {goal}.\n\n"
        f"FUENTE (únicas fuentes disponibles; no hay más):\n{source}\n\n"
        f"Procedimientos registrados en el grafo desde esa fuente: {', '.join(names)}\n"
        f"Cadenas del grafo:\n{chain}\n\n"
        f"{reglas}\n\n"
        "Devuelve blueprint markdown: módulos, dependencias, orden, validación, "
        "riesgos, y la bibliografía."
    )
    # 1500 tokens cortaba la bibliografía: va al FINAL del documento, así que es
    # lo primero que se pierde. Medido en el A/B — 4 de 22 blueprints salieron
    # truncados. Se sube el tope; el coste por blueprint sube y hay que decirlo.
    temp_kw = {} if temperature is None else {"temperature": temperature}
    bp = generate(prompt, max_tokens=BLUEPRINT_MAX_TOKENS, **temp_kw) or "(sin LLM: usa los procedimientos listados)"
    cit_map: dict | None = None
    if positional and mapa and bp and not bp.startswith("("):
        bp, cit_map = map_positional_citations(bp, mapa)
    return {"technique": technique, "goal": goal, "procedures": names,
            "doc_id": doc_id, "blueprint": bp, "citas_posicionales": cit_map}


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

    Hito 5 (hallazgo 26, modo A): el informe suma las **huérfanas** — línea
    con término técnico sin puntero ni marca R6. Antes `verificado=True` era
    posible con fabricaciones que el juez luego suspendía (ReASearch: 0
    violaciones, 2/2 resueltas, R4 suspensa); un informe que no ve eso miente
    en falso. El texto sigue intacto: la reparación es del runner, no suya.
    """
    from bibliotecario.agent import attribution as A

    if not bp.get("blueprint") or bp["blueprint"].startswith("("):
        return {**bp, "verificado": False, "violaciones": []}

    orph = A.check_orphan_claims(bp["blueprint"])
    pointers = A._POINTER.findall(bp["blueprint"])
    if not pointers:
        # Un blueprint sin punteros no está "verificado": no hay nada que
        # comprobar. Marcarlo como limpio sería mentir con el mismo número
        # (medido: una run de Task-CoEvolve salió verificado=True con 0
        # citas). Con huérfanas, en cambio, sí hay fallo que informar.
        if orph:
            return {**bp, "verificado": False, "sin_punteros": True,
                    "violaciones": orph, "reescrituras": 0}
        return {**bp, "verificado": None, "sin_punteros": True, "violaciones": []}
    v = A.check_attributions(bp["blueprint"], _cited_chunks(bp.get("doc_id"), bp["blueprint"]))
    v_all = v + orph
    return {**bp, "verificado": not v_all, "violaciones": v_all, "reescrituras": 0}


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


def instantiate_agent_template(technique: str, goal: str, bp: dict | None = None) -> dict:
    """Genera plantilla de agente instanciable desde el blueprint (decisión 1).

    Hito 3, Fase 1 (declarado 2026-10-16): pasa por `build_blueprint_p4`,
    la ruta verificada (hueco A del plan), y no por `build_blueprint` crudo.
    Un arnés generado por el camino crudo podía salir con peor integridad que
    los blueprints ya medidos del Hito 2: eran dos recetas distintas para la
    misma promesa (H1 ratificada).

    Hito 3, Fase 2 (decidido 2026-10-16): el `run()` generado es la
    **composición de las 4 capas** del harness parametrizada por la técnica —
    una llamada real por procedimiento en rotación sobre las herramientas
    locales del loop, validada contra los schemas calibrados, registrada en la
    trayectoria y regulada, más un paso final de cobertura contra el blueprint.
    Sin LLM dentro de `run()`.

    `bp` opcional: reutiliza un blueprint ya construido (regeneración de
    plantillas sin tocar el LLM). Sin él se genera por la ruta verificada.
    """
    bp = bp or build_blueprint_p4(technique, goal)
    slug = "".join(c if c.isalnum() else "-" for c in technique.lower())[:40].strip("-")
    outdir = data_dir() / "agents" / slug
    outdir.mkdir(parents=True, exist_ok=True)
    # D (§2.D, dec. 13): el estado se CALCULA en runtime, no se escribe aquí.
    # Antes el literal "todo" estaba en este fichero, así que el resultado se
    # sabía antes de correrlo — 0 de 20 pasos se ejecutaron jamás (§8.6).
    code = f'''"""Agente {technique} — plantilla generada por Bibliotecario (Hito 3, Fase 2).
Objetivo: {goal}
Procedimientos: {", ".join(bp["procedures"][:8])}

Arnés = composición de las 4 capas del harness (RuntimeHarness),
parametrizada por la técnica (Fase 2, 2026-10-16): cada procedimiento es una
llamada real a una herramienta del loop — rotación deep_sweep →
search_papers → retrieve_evidence → get_subgraph — validada contra los
schemas calibrados, registrada en la trayectoria y regulada por el harness;
el paso final valida la cobertura de procedimientos contra el blueprint. El
estado done/empty sigue el gate 0.30 (2ª enmienda de dec. 13) en las tools
que traen score; las que no lo traen se declaran por recuento de items.
Sin LLM dentro de run(). Ningún estado está escrito en este fichero
(dec. 13, D2, 2ª enmienda)."""
from pathlib import Path

STEPS = {bp["procedures"][:8]!r}
_ROTACION = ("deep_sweep", "search_papers", "retrieve_evidence", "get_subgraph")


def _args(nombre: str, paso: str, objetivo: str) -> dict:
    q = f"{{paso}} {{objetivo}}".strip()
    if nombre == "deep_sweep":
        return {{"question": q, "per_doc": 3}}
    if nombre == "search_papers":
        return {{"query": q, "top_k": 6}}
    if nombre == "retrieve_evidence":
        return {{"query": q, "top_m": 5}}
    return {{"query": q, "depth": 2}}


def _mejores_scores(res) -> list:
    out = []

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k == "score" and isinstance(v, (int, float)):
                    out.append(float(v))
                else:
                    walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(res)
    return out


def _n_items(res) -> int:
    if isinstance(res, dict):
        for k in ("hits", "docs", "paths", "nodes", "chunks"):
            v = res.get(k)
            if isinstance(v, list):
                return len(v)
        return 1 if res else 0
    return 1 if res else 0


def _estado(res) -> tuple:
    scores = _mejores_scores(res)
    n = _n_items(res)
    if scores:
        mejor = max(scores)
        if mejor >= 0.30:
            return "done", f"{{n}} items, mejor score {{mejor:.3f}}"
        return "empty", f"{{n}} items, mejor score {{mejor:.3f}} < 0.30"
    if n:
        return "done", f"{{n}} items (tool sin campo score: el gate 0.30 no aplica)"
    return "empty", "0 items"


def run(context: dict) -> dict:
    objetivo = str((context or {{}}).get("objetivo", "") or "")
    from bibliotecario.agent.tools import TOOLS, tool_schemas
    from bibliotecario.harness.runtime import get_harness

    h = get_harness()
    schemas = h.calibrate(tool_schemas())
    rid = h.start_run({{"technique": "{technique}", "goal": "{goal}",
                       "origen": "agent_template"}})
    trace = []
    for i, paso in enumerate(STEPS):
        nombre = _ROTACION[i % len(_ROTACION)]
        v = h.validate_call(nombre, _args(nombre, paso, objetivo), schemas)
        if not v.valid:
            h.record_error(rid)
            trace.append({{"step": paso, "tool": nombre, "status": "error",
                          "detalle": v.error or "validacion fallo"}})
            continue
        try:
            res = TOOLS[nombre]["fn"](**v.canonicalized["arguments"])
            status, detalle = _estado(res)
        except Exception as exc:  # noqa: BLE001 — un paso que falla no tumba la traza
            h.record_error(rid)
            status, detalle = "error", f"{{type(exc).__name__}}: {{exc}}"
        h.record_action(rid, {{"step": i, "tool": nombre, "status": status}})
        trace.append({{"step": paso, "tool": nombre, "status": status,
                      "detalle": detalle}})
        for aviso in h.regulate(rid):
            trace.append({{"step": f"regulacion-{{i}}", "tool": "harness",
                          "status": "aviso", "detalle": aviso}})
    # Validación contra el blueprint (Fase 2): cobertura de procedimientos.
    bp_path = Path(__file__).resolve().parent / "BLUEPRINT.md"
    texto = bp_path.read_text(encoding="utf-8").lower() if bp_path.exists() else ""
    if not texto:
        status, detalle = "error", "sin BLUEPRINT.md al lado de la plantilla"
        faltan = list(STEPS)
    else:
        faltan = [s for s in STEPS if s.lower()[:24] not in texto]
        if not faltan:
            status = "done"
            detalle = (f"{{len(STEPS)}}/{{len(STEPS)}} procedimientos "
                       f"presentes en el blueprint")
        else:
            status = "partial"
            detalle = (f"{{len(STEPS) - len(faltan)}}/{{len(STEPS)}} presentes; "
                       f"falta: {{', '.join(faltan[:3])}}")
    trace.append({{"step": "validacion_blueprint", "tool": "cobertura",
                  "status": status, "detalle": detalle}})
    h.finish_run(rid, score=None, metadata={{"pasos": len(trace),
                     "hechos": sum(1 for t in trace if t["status"] == "done")}})
    return {{"technique": "{technique}", "goal": "{goal}", "run_id": rid,
             "trace": trace}}
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


def recall_memory(query: str, top_k: int = 8) -> dict:
    """Recupera memoria consolidada por léxico, sin cargar embeddings."""
    hits = MT.recall_text(query, top_k=max(1, top_k))
    return {"query": query, "hits": hits, "count": len(hits)}


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
    "recall_memory": {"fn": recall_memory, "description": "Recupera lecciones y estudios consolidados "
                                                         "por léxico (sin embeddings ni coste LLM)",
                      "parameters": {"type": "object", "properties": {
                          "query": {"type": "string"}, "top_k": {"type": "integer", "default": 8}},
                          "required": ["query"]}},
    "get_status": {"fn": get_status, "description": "Estado del sistema (docs, grafo, lessons, runs)",
                   "parameters": {"type": "object", "properties": {}}},
}


def tool_schemas() -> list[dict]:
    """Schemas estilo function-calling para el harness contract layer."""
    return [{"type": "function", "function": {"name": n, "description": t["description"],
                                              "parameters": t["parameters"]}} for n, t in TOOLS.items()]
