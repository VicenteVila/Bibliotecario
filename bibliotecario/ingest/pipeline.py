"""Pipeline de ingesta: extraer → validar → quality → chunks+embeddings → SQLite (con dedup por hash)."""
from __future__ import annotations

import logging
from pathlib import Path

from bibliotecario.core import storage
from bibliotecario.core.embeddings import embed_blob, encode
from bibliotecario.ingest import base, citations, quality, schemas
from bibliotecario.ingest.image import extract_image
from bibliotecario.ingest.pdf import extract_pdf
from bibliotecario.ingest.text import extract_docx, extract_txt
from bibliotecario.ingest.url import extract_url, is_youtube_url
from bibliotecario.ingest.youtube import extract_youtube

logger = logging.getLogger(__name__)


def extract(source: str, ocr: bool = False) -> base.Document:
    if source.startswith(("http://", "https://")):
        if is_youtube_url(source):
            return extract_youtube(source)
        return extract_url(source)
    p = Path(source)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {source}")
    ext = p.suffix.lower()
    if ext == ".pdf":
        return extract_pdf(p, ocr=ocr)
    if ext == ".docx":
        return extract_docx(p)
    if ext in (".txt", ".md", ".csv"):
        return extract_txt(p)
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"):
        return extract_image(p)
    raise ValueError(f"Tipo no soportado: {ext}")


def store(doc: base.Document) -> base.IngestResult:
    validation = schemas.validate(doc)
    q_score, q_alerts = quality.score(doc.source_type, doc.text, doc.metadata)
    if not validation["valid"]:
        return base.IngestResult(ok=False, title=doc.title, quality_score=q_score,
                                 quality_alerts=q_alerts, validation=validation,
                                 error=f"validación: {validation['issues']}")
    fp = base.fingerprint(doc.text)
    with storage.get_conn() as conn:
        row = conn.execute("SELECT id FROM documents WHERE paper_hash=?", (fp,)).fetchone()
        if row:
            return base.IngestResult(ok=True, doc_id=row["id"], title=doc.title,
                                     quality_score=q_score, quality_alerts=["duplicado: ya ingerido"],
                                     validation=validation)
        import json as _json
        cur = conn.execute("INSERT INTO documents (path, title, paper_hash, metadata) VALUES (?,?,?,?)",
                           (doc.source, doc.title, fp,
                            _json.dumps(doc.metadata, ensure_ascii=False, default=str)))
        doc_id = cur.lastrowid
        chunks = base.chunk_text(doc.text)
        if chunks:
            vecs = encode(chunks)
            conn.executemany(
                "INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
                [(doc_id, i, ch, embed_blob(vecs[i])) for i, ch in enumerate(chunks)],
            )
        slug = f"raw-{doc_id}"
        conn.execute("INSERT INTO wiki_pages (slug, title, body, kind) VALUES (?,?,?,?)",
                     (slug, f"[raw] {doc.title}", doc.text[:20000], "raw"))
    logger.info("Ingerido doc_id=%s '%s' (%d chunks, q=%.0f)", doc_id, doc.title, len(chunks), q_score)
    return base.IngestResult(ok=True, doc_id=doc_id, title=doc.title, chunks=len(chunks),
                             quality_score=q_score, quality_alerts=q_alerts, validation=validation)


def ingest(source: str, ocr: bool = False) -> base.IngestResult:
    try:
        doc = extract(source, ocr=ocr)
        doc.metadata["citations"] = citations.extract_citations(doc.text)
        return store(doc)
    except Exception as e:
        logger.error("Ingesta falló para %s: %s", source, e)
        return base.IngestResult(ok=False, error=str(e))


_INBOX_EXTS = {".pdf", ".docx", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def ingest_dir(directory: str | Path, ocr: bool = False) -> dict:
    """Ingesta por lotes de una carpeta inbox: omite no-soportados y duplicados (por hash)."""
    d = Path(directory)
    if not d.is_dir():
        return {"ok": False, "error": f"No es directorio: {directory}", "files": []}
    files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in _INBOX_EXTS)
    results = []
    for f in files:
        r = ingest(str(f), ocr=ocr)
        results.append({"file": f.name, "ok": r.ok, "title": r.title,
                        "chunks": r.chunks, "error": r.error})
    ok_n = sum(1 for r in results if r["ok"])
    return {"ok": True, "total": len(files), "ingested": ok_n,
            "skipped_unsupported": sum(1 for p in d.iterdir() if p.is_file() and p.suffix.lower() not in _INBOX_EXTS),
            "files": results}
