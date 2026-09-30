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


def build_blueprint(technique: str, goal: str) -> dict:
    """Blueprint de implementación: camina el grafo procedimental y sintetiza guía accionable."""
    from bibliotecario.knowledge import procedural as P
    procs = P.list_procedures(technique=technique) or P.list_procedures()
    names = [p.label for p in procs[:20]]
    paths = PEARL.retrieve_evidence(f"{technique} {goal}", top_m=5)
    chain = "\n".join(" → ".join(f"{s['label']}" for s in p["steps"]) for p in paths)
    prompt = (f"Guía accionable para implementar la técnica '{technique}' con objetivo: {goal}.\n"
              f"Procedimientos conocidos: {', '.join(names)}\nCadenas del grafo:\n{chain}\n\n"
              "Devuelve blueprint markdown: módulos, dependencias, orden, validación, riesgos.")
    bp = generate(prompt, max_tokens=1500) or "(sin LLM: usa los procedimientos listados)"
    return {"technique": technique, "goal": goal, "procedures": names, "blueprint": bp}


def instantiate_agent_template(technique: str, goal: str) -> dict:
    """Genera plantilla mínima de agente instanciable desde el blueprint (decisión 1)."""
    bp = build_blueprint(technique, goal)
    slug = "".join(c if c.isalnum() else "-" for c in technique.lower())[:40].strip("-")
    outdir = data_dir() / "agents" / slug
    outdir.mkdir(parents=True, exist_ok=True)
    code = f'''"""Agente {technique} — plantilla generada por Bibliotecario.
Objetivo: {goal}
Procedimientos: {", ".join(bp["procedures"][:8])}
"""
STEPS = {bp["procedures"][:8]!r}

def run(context: dict) -> dict:
    trace = []
    for step in STEPS:
        trace.append({{"step": step, "status": "todo"}})
    return {{"technique": "{technique}", "goal": "{goal}", "trace": trace}}
'''
    (outdir / "agent_template.py").write_text(code, encoding="utf-8")
    (outdir / "BLUEPRINT.md").write_text(f"# {technique}\n\nObjetivo: {goal}\n\n{bp['blueprint']}\n", encoding="utf-8")
    return {"dir": str(outdir), "files": ["agent_template.py", "BLUEPRINT.md"], "procedures": bp["procedures"]}


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
