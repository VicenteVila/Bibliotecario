"""Extracción de bibliografía del propio texto: autores y año.

Motivo (§2.E, R1/R7): hoy `documents` no guarda autores, y sin ellos el
sistema no puede producir una cita citable — solo un pointer interno
`[doc:chunk]`. Comprobado campo a campo: autores solo en el texto del chunk 0,
año no extraído, arXiv propio ausente del chunk 0 de los 10 documentos.

Principio rector: **precisión sobre recall, y todo anclado.** Un nombre
omitido es preferible a uno inventado — R4 dice «no atribuye lo que la fuente
no dice», y aquí eso se aplica también a la extracción: **un nombre solo se
devuelve si aparece literalmente en el texto de origen.** Lo que no se pueda
verificar, se descarta en vez de rellenarse.

Lo que este módulo NO hace, declarado:
- no valida el *significado* (un nombre literalmente presente puede ser de una
  afiliación, no de un autor): es un candidato verificado, no una verdad.

Errata corregida: se afirmó que el arXiv propio «no aparece en el chunk 0 de
ninguno de los 10 documentos». Cierto **para el chunk 0**, y de ahí la
conclusión errónea de que no era extraíble. El sello de arXiv va **girado 90°
en el margen izquierdo**, así que el extractor lo deja fuera del chunk 0 y cae
en los chunks 2-4. Aparece en 9 de los 10 documentos (el doc 4, no).
"""
from __future__ import annotations

import re

# Sello de arXiv del margen: id, categoría y fecha de envío.
# Ejemplo real del corpus: `arXiv:2609.02216v1  [cs.AI]  2 Sep 2026`
# La categoría va en mayúsculas mezcladas (`cs.AI`), así que la clase admite A-Z.
_ARXIV = re.compile(
    r"arXiv:(\d{4}\.\d{4,5})(v\d+)?\s*(?:\[([A-Za-z.\-]+)\])?\s*"
    r"(\d{1,2}\s+([A-Z][a-z]{2})\s+(\d{4}))?",
)

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Marcas que delimitan el final del bloque de autores (afiliación o sección).
_AFFILIATION = re.compile(
    r"\b(University|Universidad|Universitat|School|Escuela|Facultad|Faculty|"
    r"Institute|Instituto|Department|Departamento|Laboratory|Laboratorio|College|"
    r"Research|Centro|Center|Centre|Google|Microsoft|OpenAI|DeepMind|Amazon|"
    r"Anthropic|Meta AI|Labs|CSAIL|Researcher|Professor|Chair|Team|Group|"
    # Tokens de afiliación del corpus que no casan con el patrón genérico.
    r"Tech|Independent|BOSS|Alto|"
    r"Abstract|ABSTRACT|Resumen|Keywords|Palabras clave|"
    r"arXiv|https?://|www\.)\b",
    re.IGNORECASE,
)

# Tres o más palabras seguidas en minúscula = prosa, no un nombre.
_PROSE = re.compile(r"\b[a-záéíóúñöü]{2,}\s+[a-záéíóúñöü]{2,}\s+[a-záéíóúñöü]{2,}\b")

# Límite duro de líneas escaneadas tras el título.
_MAX_LINES = 30
# Presupuesto en caracteres del bloque de autores (título + nombres + afiliaciones).
_BODY_BUDGET = 900

_YEAR = re.compile(r"\b(19[89]\d|20[0-3]\d)\b")

# Términos que nunca forman parte de un nombre de autor.
_STOP = {
    "the", "a", "an", "and", "of", "for", "with", "on", "in", "to", "via",
    "using", "from", "at", "by", "is", "are", "our", "we", "this", "towards",
    "toward", "based", "over", "under", "into", "across", "new", "novel",
    "el", "la", "los", "las", "de", "del", "en", "y", "para", "con", "un",
    "una", "por", "sobre", "hacia", "entre", "como", "que",
    # Secciones y sustantivos que el filtro de inicial-mayúscula no caza.
    "abstract", "keywords", "introduction", "conclusion", "references", "acknowledgment",
}

_MERGE_KEYS = ("authors", "year", "arxiv")


def _title_end(raw: str, title: str | None) -> int:
    """Índice en `raw` donde termina el título, **ignorando espacios y mayúsculas**.

    El texto extraído de un PDF parte el título con `\n` pero `documents.title`
    lo guarda en una línea — comparar cadenas literales falla siempre. Y el
    título **no siempre empieza en el 0**: los docs 5 y 6 traen delante un sello
    de arXiv (`2026-08-28`) o un número de página. Así que se comprime `raw`
    quitando espacios, se busca el título comprimido, y se devuelve el índice
    raw correspondiente. Devuelve -1 si no aparece; entonces no se recorta nada.
    """
    if not title:
        return -1
    t = re.sub(r"\s+", "", title)
    if len(t) < 12:
        return -1
    comp_chars: list[str] = []
    idx_map: list[int] = []
    for i, ch in enumerate(raw):
        if not ch.isspace():
            comp_chars.append(ch)
            idx_map.append(i)
    pos = "".join(comp_chars).lower().find(t.lower())
    if pos < 0:
        return -1
    return idx_map[pos + len(t) - 1] + 1


def _strip_title(head: str, title: str | None) -> str:
    end = _title_end(head, title)
    return head[end:] if end > 0 else head


def _normalize_part(part: str) -> list[str]:
    """Limpia un fragmento de línea y devuelve sus palabras si parece nombre propio.

    Quita superíndices de afiliación (`Lu1,2,3` → `Lu`), símbolos de autor
    (`Li∗` → `Li`) y puntuación. Descarta si queda una sola palabra o si alguna
    es término genérico de sección.
    """
    part = part.replace("∗", "").replace("*", "").replace("†", "").replace("‡", "")
    words: list[str] = []
    for w in re.split(r"\s+", part.strip()):
        w = re.sub(r"\d", "", w)          # superíndice de afiliación pegado
        w = w.strip(",;:()[]{}·•")
        # El punto se conserva si el token es corto: es una inicial («Ö.», «K.»),
        # no puntuación final.
        if len(w) > 2:
            w = w.rstrip(".")
        if w:
            words.append(w)
    if not (2 <= len(words) <= 4):
        return []
    if any(w.lower() in _STOP for w in words):
        return []
    # Todo-mayúsculas de 3+ letras = rótulo de figura o título roto, no un nombre.
    if any(len(w) >= 3 and w.isupper() for w in words):
        return []
    # Al menos un token de verdad: «Longlong Li» vale, «Palo Alto» no (ambos de 2).
    if not any(len(w) > 2 for w in words):
        return []
    return words


def _looks_like_affiliation(line: str) -> bool:
    return bool(_AFFILIATION.search(line)) or "@" in line


def _next_email(body: str, consumed: int, window: int = 5) -> bool:
    """¿Hay otro correo en las `window` líneas no vacías siguientes a `consumed`?"""
    n = 0
    for ln in body.split("\n"):
        s = ln.strip()
        if not s:
            continue
        n += 1
        if n <= consumed:
            continue
        if n > consumed + window:
            break
        if "@" in s:
            return True
    return False


def _literal_in(cand: str, flat: str) -> bool:
    """¿Aparece `cand` en `flat`, ignorando espacios y puntos?

    Se comprimen ambos lados quitando espacios **y puntos**: el limpiado quita
    el punto de «Ö.» y «K.», y el texto del PDF mete `\n` donde va un espacio.
    Exigir coincidencia con espacios y puntuación exactos descartaría autores
    legítimos por ruido de extracción, no por falta de anclaje.
    """
    return re.sub(r"[\s.]+", "", cand) in re.sub(r"[\s.]+", "", flat)


def extract_authors(text: str, title: str | None = None, limit: int = 12) -> list[str]:
    """Autores candidatos del bloque inicial, **solo si aparecen literal en `text`**.

    Extracción **por líneas**, que es como el PDF real viene separado. Cubre las
    tres disposiciones que tiene el corpus:
    - autores uno por línea con su afiliación **intercalada** (docs 1, 3, 10) —
      un corte en la primera afiliación se quedaría con el primero solo;
    - todos los autores en una línea separados por comas (docs 2, 6);
    - nombres con superíndices de afiliación (`Lu1,2,3`).

    Se descarta cualquier línea que parezca afiliación, correo o sección, y se
    corta el escaneo en «Abstract». **Anclaje**: el nombre se guarda solo si
    aparece literalmente en el texto (sin exigir la misma forma de espacios).
    """
    if not text or len(text) < 80:
        return []
    head = text[:4000]
    end = _title_end(head, title)
    # El bloque de autores vive en la cabecera; más allá hay resumen o figuras.
    body = (head[end:] if end > 0 else head)[:_BODY_BUDGET]

    flat = re.sub(r"\s+", " ", text)
    seen: set[str] = set()
    kept: list[str] = []
    scanned = 0
    for raw_line in body.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        scanned += 1
        if scanned > _MAX_LINES:
            break
        if re.match(r"^(abstract|resumen|keywords|palabras clave)\b", line, re.IGNORECASE):
            break
        # Fin del bloque: prosa del resumen. Un nombre no lleva tres minúsculas
        # seguidas ni ocupa una línea entera de párrafo.
        if _PROSE.search(line) or len(line) > 110:
            break
        # Título partido por guion («OPTIMIZA- / TION»): se salta la línea, pero
        # no corta el escaneo, porque los autores vienen justo debajo.
        if line.endswith("-"):
            continue
        if _looks_like_affiliation(line):
            # Tras un correo el bloque de autores suele terminar. Se mira 5
            # líneas adelante: si no hay otro correo, no hay más autores
            # intercalados (doc 3, rótulos de figura) y se corta. Si lo hay,
            # el patrón es nombre/correo/afiliación repetido (docs 1, 9) y se
            # sigue — cortar ahí se dejaría la mitad de los autores.
            if "@" in line and not _next_email(body, scanned):
                break
            continue
        # Los símbolos de autor (∗ † ‡) van pegados al nombre y, en el doc 3,
        # separan dos autores en la misma línea: se trocean también por ahí.
        for part in re.split(r"[,∗*†‡]|\by\b|\band\b", line):
            words = _normalize_part(part)
            if not words:
                continue
            cand = " ".join(words)
            key = cand.lower()
            if key in seen:
                continue
            if not _literal_in(cand, flat):
                continue
            seen.add(key)
            kept.append(cand)
            if len(kept) >= limit:
                return kept
    return kept


def extract_arxiv(text: str) -> dict | None:
    """Sello de arXiv del margen: id, versión, categoría y fecha de envío.

    El sello va **girado 90° en el margen izquierdo**, así que el extractor de
    PDF lo deja fuera del chunk 0 y cae en los chunks 2-4. Es la única fuente
    **estructurada y autoritativa** de fecha del corpus. Las siguientes
    apariciones de `arXiv:` en el texto son referencias ajenas — id solo, sin
    versión ni fecha — por eso se toma la primera que lleve fecha.
    """
    if not text:
        return None
    for m in _ARXIV.finditer(text):
        full = m.group(4)
        if not full:
            continue
        day = re.match(r"(\d{1,2})\s+", full)
        month = _MONTHS.get((m.group(5) or "").lower()[:3])
        year = m.group(6)
        out: dict = {"id": m.group(1)}
        if m.group(2):
            out["version"] = m.group(2)
        if m.group(3):
            out["category"] = m.group(3)
        if day and month and year:
            out["date"] = f"{year}-{month:02d}-{int(day.group(1)):02d}"
            out["year"] = year
        return out
    return None


def extract_year(text: str) -> str | None:
    """Año de publicación. Prefiere el sello de arXiv; si no hay, heurística."""
    stamp = extract_arxiv(text)
    if stamp and stamp.get("year"):
        return stamp["year"]
    if not text:
        return None
    years = _YEAR.findall(text[:900])
    if not years:
        return None
    # Contraprobar: el año debe ser también el más frecuente en todo el texto,
    # o es una cifra suelta (código postal, id de afiliación) no el del paper.
    from collections import Counter
    top_head, n_head = Counter(years).most_common(1)[0]
    top_all = Counter(_YEAR.findall(text[:40000])).most_common(1)[0][0]
    return top_head if (n_head >= 2 or top_head == top_all) else None


def extract_bibliography(text: str, title: str | None = None) -> dict:
    """Campos bibliográficos extraíbles del propio texto, sin inventar nada."""
    out: dict = {}
    authors = extract_authors(text, title=title)
    if authors:
        out["authors"] = authors
    stamp = extract_arxiv(text)
    if stamp:
        out["arxiv"] = stamp
        if stamp.get("year"):
            out["year"] = stamp["year"]
    if "year" not in out:
        year = extract_year(text)
        if year:
            out["year"] = year
    return out


def merge_metadata(existing: dict | None, extracted: dict) -> dict:
    """Fusiona metadatos existentes con la extracción, sin pisar nada ya guardado."""
    base = dict(existing) if existing else {}
    for k in _MERGE_KEYS:
        v = extracted.get(k)
        if v and not base.get(k):
            base[k] = v
    return base


def format_citation(meta: dict, title: str | None = None, doc_id: int | None = None) -> str:
    """Cita legible para un lector humano: autores, año, título.

    Hoy solo puede resolver lo que el corpus contiene. Donde falta dato se deja
    vacío en vez de rellenarse — R4 aplicada a la bibliografía.
    """
    authors = meta.get("authors") or []
    year = meta.get("year")
    if authors:
        names = ", ".join(authors[:3])
        if len(authors) > 3:
            names += " et al."
    else:
        names = "(autores no extraídos)"
    parts = [names]
    if year:
        parts.append(f"({year})")
    if title:
        parts.append(title if title.endswith((".", "?", "!")) else title + ".")
    if doc_id is not None:
        parts.append(f"[doc:{doc_id}]")
    return " ".join(parts)
