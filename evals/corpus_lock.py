"""CORPUS_LOCK: congela el corpus de evaluación y sus capas (§ corpus/versionado).

Tres subcomandos, en este orden:

    python evals/corpus_lock.py label            # etiqueta documents.corpus_capa
    python evals/corpus_lock.py build            # escribe evals/CORPUS_LOCK.json
    python evals/corpus_lock.py check            # sale 1 si el corpus cambió

`label` deriva las capas de dos sitios que ya existen en el repo, no de una
lista escrita a mano de memoria:

  * `evaluacion` — unión de los `doc_id` de TODOS los golden*.jsonl (los
    no respondibles también: son preguntas SOBRE ese paper, y si el filtro
    lo excluye el "abstiene" deja de ser una medida y pasa a ser gratis).
  * `fundacional` — los cinco papers de los que arranca el grafo
    (knowledge/seed.py, set original), detectados por título.

El resto va a `extendido`, y un paper que además es diana de preguntas ciegas
lleva `evaluacion,extendido`: su origen es de crecimiento, pero ahora está
congelado. `corpus_capa` es multivalor precisamente por esto.

Nada de esto se inventa en el retrieval: el filtro de capas vive en
`memory/retriever.py` (`BIBLIOTECARIO_CAPAS`) y el sello de integridad aquí.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bibliotecario.core import storage

LOCK = EVALS / "CORPUS_LOCK.json"
CAPAS = ("fundacional", "evaluacion", "extendido")
# Subcadena (minúsculas) del título del documento. Por título y no por doc_id:
# si la BD se reconstruye, los ids pueden desplazarse y la capa congelada no.
# Cada entrada es una tupla y se exige TODA: una sola sería ambigua, y el
# separador cambia entre el título extraído ("Título: subtítulo") y el nombre
# de fichero ("Título, subtítulo"), que es como se detectó el fallo.
FUNDACIONAL_TITLES = (
    ("pearl", "path-entity aligned relational learning"),
    ("procedural graphs", "self-evolving execution structures"),
    ("task-coevolve",),
    ("the optimizer is the agent",),
    ("wikiskill", "compiling agent experience"),
)


def _sha256(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        return h.hexdigest()
    except OSError:
        return None


def _resolve(path: str) -> Path:
    """Path de la BD (relativo al repo) → fichero real, si existe."""
    p = Path(path)
    if p.is_absolute():
        return p
    return ROOT / p


def golden_files() -> dict[str, str]:
    """Todos los golden*.jsonl → sha256. Si cambian, cambian las preguntas."""
    return {p.name: (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "")
            for p in sorted(EVALS.glob("golden*.jsonl"))}


def evaluacion_doc_ids() -> dict[str, list[int]]:
    """doc_id por golden: los que son diana de preguntas (respondibles o no)."""
    out: dict[str, list[int]] = {}
    for p in sorted(EVALS.glob("golden*.jsonl")):
        ids: set[int] = set()
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("doc_id"):
                ids.add(int(row["doc_id"]))
            for d in row.get("answerable_docs") or []:
                ids.add(int(d))
            for cite in row.get("cite_chunks") or []:
                head = str(cite).split(":")[0]
                if head.isdigit():
                    ids.add(int(head))
        if ids:
            out[p.name] = sorted(ids)
    return out


def _capa_de(title: str, evaluacion: set[int], doc_id: int) -> str:
    t = (title or "").lower()
    fundacional = any(all(s in t for s in grupo) for grupo in FUNDACIONAL_TITLES)
    capas = []
    if fundacional:
        capas.append("fundacional")
    if doc_id in evaluacion:
        capas.append("evaluacion")
    if not fundacional:
        capas.append("extendido")
    return ",".join(capas)


def _docs(db: Path | None = None) -> list[dict]:
    with storage.get_conn(db) as conn:
        rows = conn.execute(
            "SELECT d.id, d.path, d.title, d.paper_hash, d.corpus_capa,"
            " (SELECT COUNT(*) FROM chunks c WHERE c.doc_id=d.id) AS chunks"
            " FROM documents d ORDER BY d.id").fetchall()
    return [dict(r) for r in rows]


def _canon(capas: str | list[str]) -> str:
    """Orden canónico fundacional,evaluacion,extendido (multivalor)."""
    partes = capas.split(",") if isinstance(capas, str) else list(capas)
    partes = {p.strip().lower() for p in partes if p.strip()}
    return ",".join(c for c in CAPAS if c in partes)


def label(db: Path | None = None, reset: bool = False) -> dict:
    """Escribe `corpus_capa` en todos los documentos (idempotente).

    Sin `reset`, solo rellena lo vacío y garantiza que los dianas de preguntas
    lleven `evaluacion`: no pisa una etiqueta puesta a mano en un documento que
    no es diana de ninguna pregunta. Con `reset` reescribe todo desde los
    goldens y los títulos fundacionales.
    """
    por_golden = evaluacion_doc_ids()
    evaluacion = {i for ids in por_golden.values() for i in ids}
    cambios = []
    with storage.get_conn(db) as conn:
        for d in conn.execute("SELECT id, title, corpus_capa FROM documents ORDER BY id").fetchall():
            actual = d["corpus_capa"] or ""
            if reset or not actual:
                nueva = _capa_de(d["title"] or "", evaluacion, d["id"])
            elif d["id"] in evaluacion and "evaluacion" not in actual.split(","):
                nueva = _canon([*actual.split(","), "evaluacion"])
            else:
                nueva = _canon(actual)
            if nueva == _canon(actual):
                continue
            conn.execute("UPDATE documents SET corpus_capa=? WHERE id=?", (nueva, d["id"]))
            cambios.append({"doc_id": d["id"], "de": actual, "a": nueva})
    resumen: dict[str, int] = {}
    for c in cambios:
        resumen[c["a"]] = resumen.get(c["a"], 0) + 1
    return {"etiquetados": len(cambios), "por_capa": resumen,
            "evaluacion_doc_ids": sorted(evaluacion), "cambios": cambios}
    aplicados = [c for c in cambios if c["de"] != c["a"]]
    resumen: dict[str, int] = {}
    for c in aplicados:
        resumen[c["a"]] = resumen.get(c["a"], 0) + 1
    return {"etiquetados": len(aplicados), "por_capa": resumen,
            "evaluacion_doc_ids": sorted(evaluacion), "cambios": aplicados}


def build(db: Path | None = None, out: Path | None = None, nombre: str = "") -> dict:
    """Congela el estado actual de la BD en `CORPUS_LOCK.json`.

    Los documentos ya declarados conservan su lote; los nuevos pasan a un lote
    siguiente (así "lote 1" aparece solo como diff, sin contadores a mano).
    """
    out = out or LOCK
    prev_lock = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    prev = prev_lock.get("docs", {})
    prev_lotes = prev_lock.get("lotes", [])
    nuevo_lote = max((l["lote"] for l in prev_lotes), default=-1) + 1
    if not prev_lotes:
        nuevo_lote, nombre = 0, (nombre or "corpus-inicial")
    docs, lotes = {}, {}
    for l in prev_lotes:
        lotes[l["lote"]] = {"lote": l["lote"], "nombre": l["nombre"], "doc_ids": []}
    for d in _docs(db):
        key = str(d["id"])
        meta = prev.get(key)
        if meta is None:
            lot = nuevo_lote
            docs[key] = {"lote": lot}
        else:
            lot = meta.get("lote", nuevo_lote)
            docs[key] = {"lote": lot, **{k: v for k, v in meta.items() if k == "nota"}}
        capas = [c for c in (d["corpus_capa"] or "extendido").split(",") if c]
        docs[key].update({
            "title": d["title"],
            "path": d["path"],
            "capas": capas,
            "paper_hash": d["paper_hash"],
            "file_sha256": _sha256(_resolve(d["path"])),
            "chunks": d["chunks"],
        })
        lotes.setdefault(lot, {"lote": lot, "nombre": nombre or f"lote-{lot}", "doc_ids": []})
        lotes[lot]["doc_ids"].append(d["id"])
    por_golden = evaluacion_doc_ids()
    lock = {
        "version": 1,
        "db": str(db) if db else "data/bibliotecario.db",
        "built_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "capas": list(CAPAS),
        "fundacional_titles": list(FUNDACIONAL_TITLES),
        "goldens": golden_files(),
        "evaluacion_por_golden": por_golden,
        "evaluacion_doc_ids": sorted({i for v in por_golden.values() for i in v}),
        "lotes": [lotes[k] for k in sorted(lotes)],
        "docs": docs,
    }
    out.write_text(json.dumps(lock, indent=1, ensure_ascii=False, default=str) + "\n",
                   encoding="utf-8")
    return lock


def check(db: Path | None = None, lock_path: Path | None = None) -> dict:
    """Compara la BD con el lock. `fatal` rompe la eval; `avisos` no.

    El criterio es el del propósito: rompe lo que invalida una comparación
    (corpus de evaluación y goldens); avisa de lo que el filtro de capas ya
    aísla (documentos nuevos en `extendido`).
    """
    lock_path = lock_path or LOCK
    if not lock_path.exists():
        return {"fatal": [("no existe evals/CORPUS_LOCK.json: ejecuta "
                           "`python evals/corpus_lock.py label` y luego `build`")],
                "avisos": []}
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    fatal, avisos = [], []
    actuales = {d["id"]: d for d in _docs(db)}
    docs_lock = lock.get("docs", {})

    for nombre, sha in (lock.get("goldens") or {}).items():
        real = golden_files().get(nombre)
        if real is None or not real:
            fatal.append(f"desapareció el golden set {nombre}")
        elif real != sha:
            fatal.append(f"cambiaron las preguntas de {nombre} "
                         f"(sha {sha[:12]} → {real[:12]}): el benchmark ya no es el mismo, "
                         f"decláralo con `build` y corre una línea base nueva")
    for nombre, sha in golden_files().items():
        if nombre not in (lock.get("goldens") or {}):
            fatal.append(f"golden nuevo sin declarar: {nombre}")

    for key, m in docs_lock.items():
        doc_id = int(key)
        eval_doc = bool(set(m.get("capas") or []) & {"fundacional", "evaluacion"})
        d = actuales.get(doc_id)
        destino = fatal if eval_doc else avisos
        if d is None:
            destino.append(f"doc {doc_id} ('{m.get('title')}') ya no está en la BD")
            continue
        if d["paper_hash"] != m.get("paper_hash"):
            destino.append(f"doc {doc_id}: cambió el texto (paper_hash "
                           f"{str(m.get('paper_hash'))[:12]} → {str(d['paper_hash'])[:12]})")
        if d["chunks"] != m.get("chunks"):
            destino.append(f"doc {doc_id}: cambió el troceado "
                           f"({m.get('chunks')} → {d['chunks']} chunks)")
        capas = [c for c in (d["corpus_capa"] or "").split(",") if c]
        if capas != m.get("capas"):
            destino.append(f"doc {doc_id}: cambió la capa "
                           f"({m.get('capas')} → {capas})")
        real_sha = _sha256(_resolve(d["path"]))
        if real_sha != m.get("file_sha256"):
            destino.append(f"doc {doc_id}: cambió o desapareció el fichero {d['path']}")

    for doc_id, d in actuales.items():
        if str(doc_id) in docs_lock:
            continue
        capas = [c for c in (d["corpus_capa"] or "").split(",") if c]
        if "evaluacion" in capas:
            fatal.append(f"doc {doc_id} etiquetado 'evaluacion' sin declarar en el lock")
        else:
            avisos.append(f"doc {doc_id} nuevo sin declarar ({','.join(capas) or 'sin capa'}) — "
                          f"decláralo con `build` para llevar su lote")
    return {"fatal": fatal, "avisos": avisos}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Capas y congelación del corpus de evaluación")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("label", help="escribe documents.corpus_capa desde los goldens")
    s.add_argument("--reset", action="store_true", help="reescribe también etiquetas manuales")
    s = sub.add_parser("build", help="congelar estado actual en CORPUS_LOCK.json")
    s.add_argument("--nombre", default="", help="nombre del lote nuevo")
    s = sub.add_parser("check", help="comprobar BD contra el lock (exit 1 si cambió)")
    s.add_argument("--strict", action="store_true", help="los avisos también rompen")
    a = ap.parse_args(argv)

    if a.cmd == "label":
        r = label(reset=a.reset)
        print(json.dumps({k: v for k, v in r.items() if k != "cambios"}, indent=1,
                         ensure_ascii=False))
        for c in r["cambios"]:
            if c["de"] != c["a"]:
                print(f"  doc {c['doc_id']}: {c['de'] or '(vacío)'} → {c['a']}")
        return 0
    if a.cmd == "build":
        lock = build(nombre=a.nombre)
        print(f"lock: {LOCK} — {len(lock['docs'])} docs, "
              f"{len(lock['lotes'])} lotes, evaluacion={lock['evaluacion_doc_ids']}")
        for l in lock["lotes"]:
            print(f"  lote {l['lote']} ({l['nombre']}): {len(l['doc_ids'])} docs")
        return 0
    r = check()
    for p in r["fatal"]:
        print(f"FATAL: {p}")
    for p in r["avisos"]:
        print(f"aviso: {p}")
    if r["fatal"] or (a.strict and r["avisos"]):
        print("el corpus de evaluación cambió respecto al lock")
        return 1
    print("lock OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
