"""Pipeline de ingesta: extraer → validar → quality → chunks+embeddings → SQLite (upsert semántico)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from bibliotecario.core import storage
from bibliotecario.core.embeddings import embed_blob, encode
from bibliotecario.ingest import base, bibliography, citations, quality, schemas
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


def _load_meta(raw) -> dict:
    try:
        data = json.loads(raw) if raw else {}
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _merge_meta(old: dict, new: dict) -> dict:
    """Metadatos del upsert: lo nuevo y no vacío gana; lo viejo nunca se pierde.

    Distinto de `bibliography.merge_metadata` (que solo rellena lo vacío y da
    prioridad a lo guardado): aquí lo que cambia es que `store()` ya no devuelve
    temprano, así que hay que decidir qué hacer con un valor que difiere. Regla:
    un valor nuevo no vacío es una mejora de extracción (o la corrección de
    código de la corrida anterior) y actualiza; un valor vacío/None no borra
    nada (las páginas u OCR que solo se saben en el momento de la extracción
    siguen intactos).
    """
    merged = dict(old)
    for k, v in (new or {}).items():
        if v is None or v == "" or v == {} or v == []:
            continue
        merged[k] = v
    return merged


def _norm_title(title: str | None) -> str:
    """Título canónico para decidir identidad: minúsculas y espacios colapsados."""
    return " ".join((title or "").lower().split())


def _find_existing(conn, arxiv_id: str | None, fp: str, source: str):
    """Fila existente: hash → arXiv → (luego `path` en `store`) — nada más.

    1. **hash**: contenido idéntico = mismo documento (y es la clave UNIQUE de
       `documents`, así que mirarla primero también evita chocar contra ella).
       Cubre los papers sin identificador (el `.docx` del corpus no tiene).
    2. **arXiv**: mismo identificador = misma obra da igual el formato o la
       versión (v1 vs v2, PDF vs DOCX/OCR) — es la clase de duplicado que el
       dedup por hash no veía, la deriva de un carácter en la extracción. Pero
       **solo se adopta la fila si además coincide el `path`**: entre varias
       filas con el mismo id se prefiere la del mismo fichero, y si ninguna lo
       es, se devuelve `None` y el documento entra como fila nueva.

    Nunca se pisa un documento existente con un fichero distinto solo por
    compartir arXiv: una traducción conserva el título original, así que
    arXiv+título no distinguen «misma obra, otro idioma» de «mismo paper».
    Un duplicado se limpia a mano; un documento de `evaluacion` pisado con
    texto en otro idioma no se recupera.
    """
    row = conn.execute(
        "SELECT id, paper_hash, path, title, metadata FROM documents WHERE paper_hash=?",
        (fp,)).fetchone()
    if row:
        return row
    if arxiv_id:
        rows = conn.execute(
            "SELECT id, paper_hash, path, title, metadata FROM documents "
            "WHERE json_extract(metadata, '$.arxiv.id') = ? ORDER BY id",
            (arxiv_id,)).fetchall()
        if rows:
            for r in rows:
                if r["path"] == source:
                    return r
            logger.warning(
                "arXiv %s coincide pero el path no ('%s' frente a %d fila(s)): "
                "es otra variante del paper, se inserta como documento nuevo",
                arxiv_id, source, len(rows))
            return None
    return None


def _find_by_path(conn, source: str, title: str):
    """Misma fila por (path, título): solo entonces el texto distinto es deriva."""
    norm = _norm_title(title)
    rows = conn.execute(
        "SELECT id, paper_hash, path, title, metadata FROM documents "
        "WHERE path=? ORDER BY id", (source,)).fetchall()
    for r in rows:
        if _norm_title(r["title"]) == norm:
            if len(rows) > 1:
                logger.warning("path %s en %d filas; uso doc_id=%s",
                               source, len(rows), r["id"])
            return r
    if rows:
        logger.info("path %s con título distinto ('%s' vs '%s'): es otro documento",
                    source, rows[0]["title"], title)
    return None


def _write_chunks(conn, doc_id: int, title: str, text: str) -> int:
    """Chunks + embeddings del texto, y su página wiki `raw-<id>` (reescribible)."""
    chunks = base.chunk_text(text)
    if chunks:
        vecs = encode(chunks)
        conn.executemany(
            "INSERT INTO chunks (doc_id, chunk_idx, text, embedding) VALUES (?,?,?,?)",
            [(doc_id, i, ch, embed_blob(vecs[i])) for i, ch in enumerate(chunks)],
        )
    slug = f"raw-{doc_id}"
    conn.execute("DELETE FROM wiki_pages WHERE slug=?", (slug,))
    conn.execute("INSERT INTO wiki_pages (slug, title, body, kind) VALUES (?,?,?,?)",
                 (slug, f"[raw] {title}", text[:20000], "raw"))
    return len(chunks)


def store(doc: base.Document, capa: str | None = None) -> base.IngestResult:
    """Guarda el documento en su capa (por defecto `extendido`) — **upsert semántico**.

    La capa se etiqueta AQUÍ, en la ingesta, no a posteriori: es el diseño del
    corpus versionado (fundacional/evaluacion/extendido). Un duplicado no
    reetiqueta nada y una actualización **nunca toca `corpus_capa`**.

    Dedup por clave semántica (`_find_existing`), no solo por hash del texto:

    * hash igual y fila intacta → `duplicado`, ni una escritura;
    * hash igual pero metadatos/pítulo/path cambiaron → `UPDATE` de la fila
      **sin reindexar** (antes el `early return` hacía imposible que una mejora
      del extractor llegara a la BD sin un backfill manual);
    * hash distinto con la misma clave → `actualizado`: fila + chunks + wiki
      `raw-<id>` reescritos (v1→v2 o extracción mejorada), capa intacta;
    * sin fila → `insertado` con la capa de la corrida.

    `IngestResult.action` lleva esa etiqueta; `quality_alerts` sigue siendo
    solo calidad.
    """
    capa_norm = base.normalize_capa(capa)
    validation = schemas.validate(doc)
    q_score, q_alerts = quality.score(doc.source_type, doc.text, doc.metadata)
    if not validation["valid"]:
        return base.IngestResult(ok=False, title=doc.title, quality_score=q_score,
                                 quality_alerts=q_alerts, validation=validation,
                                 error=f"validación: {validation['issues']}")
    fp = base.fingerprint(doc.text)
    # Bibliografía: autores/año extraídos del propio texto y verificados
    # literalmente antes de guardarse (§2.E, R1/R7).
    meta = bibliography.merge_metadata(
        doc.metadata if isinstance(doc.metadata, dict) else None,
        bibliography.extract_bibliography(doc.text, title=doc.title),
    )
    arxiv_id = (meta.get("arxiv") or {}).get("id") or None
    with storage.get_conn() as conn:
        existing = _find_existing(conn, arxiv_id, fp, doc.source)
        if existing is None:
            existing = _find_by_path(conn, doc.source, doc.title)
        if existing is None:
            doc_id = conn.execute(
                "INSERT INTO documents (path, title, paper_hash, metadata, corpus_capa) VALUES (?,?,?,?,?)",
                (doc.source, doc.title, fp,
                 json.dumps(meta, ensure_ascii=False, default=str), capa_norm)).lastrowid
            n_chunks = _write_chunks(conn, doc_id, doc.title, doc.text)
            action = "insertado"
        else:
            doc_id = existing["id"]
            old = _load_meta(existing["metadata"])
            merged = _merge_meta(old, meta)
            # `_find_existing` mira el hash primero: si `fp` viviera en otra fila
            # habríamos adoptado esa, así que escribirlo aquí no puede chocar
            # contra UNIQUE(documents.paper_hash).
            same_text = existing["paper_hash"] == fp
            same_row = (same_text and merged == old
                        and existing["path"] == doc.source
                        and _norm_title(existing["title"]) == _norm_title(doc.title))
            if same_row:
                logger.info("Duplicado doc_id=%s '%s' (texto y fila intactos)", doc_id, doc.title)
                return base.IngestResult(
                    ok=True, doc_id=doc_id, title=doc.title, action="duplicado",
                    quality_score=q_score, quality_alerts=["duplicado: ya ingerido"],
                    validation=validation)
            conn.execute(
                "UPDATE documents SET path=?, title=?, paper_hash=?, metadata=? WHERE id=?",
                (doc.source, doc.title, fp,
                 json.dumps(merged, ensure_ascii=False, default=str), doc_id))
            if same_text:
                # Solo cambió lo que no vive en los chunks: no se re-embedde nada.
                action = "metadatos actualizados"
                n_chunks = 0
            else:
                # Texto nuevo para la misma clave: los chunks viejos ya no
                # corresponden. Borrar primero (UNIQUE(doc_id, chunk_idx)).
                conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
                n_chunks = _write_chunks(conn, doc_id, doc.title, doc.text)
                action = "actualizado"
    if action == "insertado":
        logger.info("Ingerido doc_id=%s '%s' (%d chunks, q=%.0f, capa=%s)",
                    doc_id, doc.title, n_chunks, q_score, capa_norm)
    else:
        logger.info("%s doc_id=%s '%s' (%d chunks nuevos, q=%.0f)",
                    action, doc_id, doc.title, n_chunks, q_score)
    return base.IngestResult(ok=True, doc_id=doc_id, title=doc.title, action=action,
                             chunks=n_chunks, quality_score=q_score,
                             quality_alerts=q_alerts, validation=validation)



def ingest(source: str, ocr: bool = False, capa: str | None = None) -> base.IngestResult:
    try:
        doc = extract(source, ocr=ocr)
        doc.metadata["citations"] = citations.extract_citations(doc.text)
        return store(doc, capa=capa)
    except Exception as e:
        logger.error("Ingesta falló para %s: %s", source, e)
        return base.IngestResult(ok=False, error=str(e))


_INBOX_EXTS = {".pdf", ".docx", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def ingest_dir(directory: str | Path, ocr: bool = False, capa: str | None = None) -> dict:
    """Ingesta por lotes de una carpeta inbox: omite no-soportados y duplicados.

    No entra en subcarpetas: `descartados/` y `game_development/` quedan fuera
    a propósito. Re-ingerir la raíz es idempotente — el upsert semántico de
    `store()` no reescribe nada si texto, metadatos, título y path están
    intactos, y solo reindexa cuando el texto de la misma clave cambió.
    `acciones` resume qué tocó la corrida (insertado/actualizado/metadatos
    actualizados/duplicado) para que «26 ficheros, 0 cambios» sea un dato del
    JSON, no una suposición.
    """
    d = Path(directory)
    if not d.is_dir():
        return {"ok": False, "error": f"No es directorio: {directory}", "files": []}
    capa_norm = base.normalize_capa(capa)
    files = sorted(p for p in d.iterdir() if p.is_file() and p.suffix.lower() in _INBOX_EXTS)
    results = []
    for f in files:
        r = ingest(str(f), ocr=ocr, capa=capa_norm)
        results.append({"file": f.name, "ok": r.ok, "title": r.title,
                        "chunks": r.chunks, "error": r.error, "action": r.action})
    ok_n = sum(1 for r in results if r["ok"])
    acciones: dict[str, int] = {}
    for r in results:
        if r["action"]:
            acciones[r["action"]] = acciones.get(r["action"], 0) + 1
    return {"ok": True, "total": len(files), "ingested": ok_n, "capa": capa_norm,
            "acciones": acciones,
            "skipped_unsupported": sum(1 for p in d.iterdir() if p.is_file() and p.suffix.lower() not in _INBOX_EXTS),
            "files": results}


def backfill_bibliography() -> dict:
    """Extrae autores/año de los documentos **ya ingeridos**, desde sus primeros chunks.

    Atajo cuando no quieres re-ingerir (el upsert de `store()` ya actualiza los
    metadatos de una fila existente al volver a pasar el fichero, pero eso
    exige tener a mano la fuente; esto trabaja solo contra los chunks).

    Usa los chunks 0-5 y **no pisa** ningún campo ya presente — `merge_metadata`
    solo rellena lo vacío. Hace falta más de la cabecera: el **sello de arXiv
    va girado 90° en el margen**, así que el extractor lo deja en los chunks
    2-4 y no en el 0 (comprobado empíricamente en 9 de los 10 documentos).
    """
    import json as _json
    scanned = updated = 0
    detail = []
    with storage.get_conn() as conn:
        docs = conn.execute("SELECT id, title, metadata FROM documents ORDER BY id").fetchall()
        for d in docs:
            scanned += 1
            rows = conn.execute(
                "SELECT text FROM chunks WHERE doc_id=? AND chunk_idx BETWEEN 0 AND 5 ORDER BY chunk_idx",
                (d["id"],),
            ).fetchall()
            if not rows:
                continue
            text = " ".join(r["text"] for r in rows)
            try:
                existing = _json.loads(d["metadata"]) if d["metadata"] else None
            except (TypeError, ValueError):
                existing = None
            if not isinstance(existing, dict):
                existing = None
            merged = bibliography.merge_metadata(
                existing, bibliography.extract_bibliography(text, title=d["title"])
            )
            if merged == (existing or {}):
                detail.append({"doc_id": d["id"], "authors": (existing or {}).get("authors"),
                               "year": (existing or {}).get("year"),
                               "arxiv": (existing or {}).get("arxiv"), "changed": False})
                continue
            conn.execute("UPDATE documents SET metadata=? WHERE id=?",
                         (_json.dumps(merged, ensure_ascii=False, default=str), d["id"]))
            updated += 1
            detail.append({"doc_id": d["id"], "authors": merged.get("authors"),
                           "year": merged.get("year"), "arxiv": merged.get("arxiv"),
                           "changed": True})
    logger.info("Backfill bibliográfico: %d/%d documentos actualizados", updated, scanned)
    return {"scanned": scanned, "updated": updated, "detail": detail}
