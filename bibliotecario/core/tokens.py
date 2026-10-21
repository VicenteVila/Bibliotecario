r"""Tokenizador compartido del canal keyword (retriever, tools, fuente y semillas PEARL).

Antes había tres dialectos distintos para la misma idea de «palabra»:

* `memory/retriever._tokens` — `[a-záéíóúñü]{4,}`: sin dígitos y sin la stoplist.
* `agent/tools._doc_keyword_chunks` — `[a-z0-9\-]{4,}`: con dígitos y guiones,
  con stoplist, y contando ocurrencias **por subcadena** (`"use"` contaba
  dentro de `"users"` y `"are"` dentro de `"care"`).
* `agent/tools._toks` (similitud léxica de la fuente) — igual que el retriever.
* `knowledge/pearl.seed_nodes` — `split()` sobre el texto crudo (`"failure?"`
  buscaba literalmente `failure?` en los labels) y `len(t) > 3`.

La guillotina de longitud mataba por igual `why`, `how`, `RAG`, `LLM`, `API`
y `OCR`, y las cifras (`τ=5`, `k=10`) no entraban en dos de los cuatro. Aquí
manda una sola regla: **letras de 3 o más, o cualquier cifra**; el ruido que
entra al bajar el umbral lo quita la stoplist compartida, no la longitud —
que era el filtro equivocado. El orden se conserva (`token_list`) porque las
semillas del grafo lo necesitan.
"""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable

# Cualquier cifra ("5", "10", "0"), compuesto con guion ("task-coevolve",
# "path-entity") o palabra de ≥3 letras. El compuesto se conserva entero: al
# trocearlo en `task` + `coevolve` términos que aparecen en casi todos los
# chunks del paper diluían el léxico y el chunk con el dato concreto se caía
# del top (medido: el chunk de "earliest candidate" pasaba del puesto 8 al 12).
TOKEN_RE = re.compile(r"[0-9]+|[a-záéíóúñü]+(?:-[a-z0-9áéíóúñü]+)+|[a-záéíóúñü]{3,}")

# Palabras vacías EN + ES. Solo funcionales: quitar un término de contenido
# aquí sería perder señal, y con `drop_stop=False` el que la necesite la omite.
STOP = frozenset({
    # inglés: artículo, pronombre, preposición, conjunción, auxiliar, adverbio débil
    "the", "and", "are", "was", "were", "for", "not", "but", "with", "that",
    "this", "these", "those", "from", "into", "each", "than", "them", "they",
    "there", "their", "then", "also", "such", "only", "over", "under", "via",
    "both", "either", "neither", "nor", "have", "has", "had", "does", "did",
    "been", "being", "will", "would", "shall", "should", "can", "could",
    "may", "might", "must", "when", "where", "which", "what", "who", "whom",
    "whose", "why", "how", "its", "one", "two", "more", "most", "much",
    "many", "some", "any", "all", "every", "other", "another", "very",
    # español
    "para", "por", "con", "una", "uno", "del", "que", "las", "los", "como",
    "este", "esta", "estos", "estas", "ese", "esa", "esos", "esas", "mas",
    "sin", "son", "era", "fueron", "ser", "muy", "donde", "cual", "cuando",
    "quien", "porque",
})


def token_list(text: str, *, drop_stop: bool = True) -> list[str]:
    """Tokens en orden de aparición (con repeticiones), en minúsculas."""
    found = TOKEN_RE.findall(text.lower())
    if not drop_stop:
        return found
    return [t for t in found if t not in STOP]


def tokens(text: str, *, drop_stop: bool = True) -> set[str]:
    """Conjunto de tokens: lo que usan los cálculos de solape (kw, similitud)."""
    return set(token_list(text, drop_stop=drop_stop))


def count_terms(text: str, terms: Iterable[str]) -> int:
    """Ocurrencias de `terms` como **tokens exactos** del texto (no subcadenas)."""
    term_set = set(terms)
    if not term_set:
        return 0
    counts = Counter(TOKEN_RE.findall(text.lower()))
    return sum(counts.get(t, 0) for t in term_set)
