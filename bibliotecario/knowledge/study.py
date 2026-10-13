"""Estudio de un paper: capa de comprensión, no de construcción.

Hay dos capas y no se confunden:

- **blueprint** (`agent/tools.py`) — *cómo levantar eso*. Especificación de
  construcción, se implementa y se mide con R1-R7.
- **study** (este módulo) — *qué dice y qué no dice el paper*. Comprensión, se
  lee y se retiene.

El blueprint es el entregable medible; el estudio es el que se puede aprender.
El estudio existe además como ancla de transferencia: es el único artefacto que
cruza papers entre sí, y por tanto el único que un run posterior puede reutilizar
sin tener que re-leer la fuente.

Disciplina heredada de §2.E, con una adaptación: **R6 no aplica** — un estudio
describe, no propone, así que no hay puente que marcar. **R7 sí**, pero como
sección `## Fuente` de ese paper. **R5 se aplica al propio estudio**: declara
qué no dice el paper, que es lo que separa estudiar de resumir.
"""
from __future__ import annotations

import logging
import re

from bibliotecario.core import storage

logger = logging.getLogger(__name__)

STUDY_MAX_TOKENS = 3500
# Presupuesto de texto fuente. El doc más gordo del corpus son 139k chars
# (~35k tokens). Se manda entero cuando cabe; si no, se trunca **y se declara**
# en el propio estudio — misma regla que R5: lo que falta se dice, no se omite.
STUDY_MAX_CHARS = 140_000

_RULES = """Reglas de escritura, obligatorias:
R1. Di de donde sale cada afirmación: «Según <autores> (<año>) [doc:<id>:<chunk>]…»,
    no «el método selecciona tareas» a secas. El puntero es obligatorio, tiene
    que apuntar a un chunk que hayas visto en FUENTE, y **el formato es exactamente
    `[doc:3:14]`** — dos números separados por dos puntos, sin la palabra
    «chunk» y sin espacios: `[doc:3:chunk:14]` y `[doc3:14]` **no valen**, no se
    resuelven. **R1 es suelo: sin puntero no hay salvación por ninguna otra regla.**
R2. Comillas ⇔ literal: entrecomilla SOLO cuando la frase sea idéntica a la
    fuente. Si la reescribes, no la entrecomilles.
R3. Parafrasea sin comillas, pero atribuyendo: tus palabras + quien lo dice.
R4. No presentes como de la fuente algo que no esté en FUENTE. Si llevas la
    idea hacia algo que el paper no trata, márcalo como «(propuesta del
    bibliotecario)» **en la misma línea, o en la inmediatamente siguiente**.
R5. Declara los silencios: si el paper no especifica un detalle, dilo —«el
    paper no especifica…»— en vez de rellenarlo. Esto se aplica también al
    propio estudio: si tu fuente estaba truncada, dilo aquí.

R6 no aplica: un estudio describe, no propone. La única marca permitida es la
de R4, y solo cuando dejes el terreno del paper."""


def _full_source(doc_id: int, max_chars: int | None = None) -> tuple[str, bool]:
    """Texto completo del paper, con [chunk M] delante de cada trozo.

    Devuelve (texto, truncado). `truncado` se declara en el estudio: un estudio
    que se queda corto y no lo dice es exactamente el defecto que R5 existe
    para cazar.
    """
    if max_chars is None:
        max_chars = STUDY_MAX_CHARS   # en tiempo de llamada, no de definicion
    from bibliotecario.core import storage as S
    with S.get_conn() as conn:
        rows = conn.execute(
            "SELECT chunk_idx, text FROM chunks WHERE doc_id=? ORDER BY chunk_idx",
            (doc_id,),
        ).fetchall()
    if not rows:
        return "", False
    used = 0
    parts: list[str] = []
    truncado = False
    for r in rows:
        piece = f"[chunk {r['chunk_idx']}] {r['text']}"
        if used + len(piece) > max_chars:
            truncado = True
            break
        parts.append(piece)
        used += len(piece)
    return "\n\n".join(parts), truncado


def _doc_title(doc_id: int) -> str:
    with storage.get_conn() as conn:
        r = conn.execute("SELECT title FROM documents WHERE id=?", (doc_id,)).fetchone()
    return r["title"] if r else f"doc{doc_id}"


def _other_docs(doc_id: int) -> list[tuple[int, str, str]]:
    """Otros papers de la base, con su chunk 0 (título+resumen) para poder
    relacionarlos **con cita** y no de memoria. Sin ese texto el cruce sería
    una afirmación sin fuente, o sea una fabricación — lo mismo que §5.9 mide
    que mata a R4 en los blueprints."""
    out: list[tuple[int, str, str]] = []
    with storage.get_conn() as conn:
        for r in conn.execute(
            "SELECT id, title FROM documents WHERE id<>? ORDER BY id", (doc_id,)
        ).fetchall():
            ch = conn.execute(
                "SELECT text FROM chunks WHERE doc_id=? AND chunk_idx=0", (r["id"],)
            ).fetchone()
            out.append((r["id"], r["title"], ch["text"] if ch else ""))
    return out


def _prompt(doc_id: int) -> tuple[str, dict]:
    source, truncado = _full_source(doc_id)
    title = _doc_title(doc_id)
    otros = _other_docs(doc_id)
    bloque_otros = "\n".join(
        f"- doc{i}: {t}\n  {c[:600]}" for i, t, c in otros
    ) or "(ninguno)"
    trunc_note = (
        "\nATENCIÓN: el texto fuente NO cabe entero y se ha truncado. "
        "Di explícitamente al final, en «Qué no dice», que el estudio se apoya "
        "en una parte del paper y declara cuál es el límite de lo leído.\n"
        if truncado else ""
    )
    p = f"""Eres un bibliotecario que estudia papers para un humano. Tu tarea NO
es enseñar a construir nada: es hacer que el paper se entienda. Escribe en
español.

{_RULES}

No es un resumen de implementación, ni una guía de arnés, ni una lista de
instrucciones. Es comprensión: qué pregunta responde el paper, cómo lo
resuelve y dónde se le acaba el terreno.
{trunc_note}
## Qué propone
La idea central, en prosa. Qué problema ataca y qué respuesta da.

## Cómo funciona
El mecanismo: qué entra, qué sale, en qué orden. Concreto, no adjetivos.

## Qué es nuevo
Frente a qué se define el paper. Qué ya existía y qué aporta él.

## Qué no dice / límites
Los silencios: qué deja sin tratar, qué asume sin demostrar, dónde no se
puede generalizar. Esto es lo que separa estudiar de resumir; dedícale espacio
real y no una frase de cortesía.

## Relación con otras técnicas de la base
Cruza con la lista de abajo. Cita **a cada paper con el que relaciones** usando
su propio `[doc:i:0]`: no se puede afirmar parentesco sin leerlo. Si la
relación es inferencia tuya y no del paper, márcala como «Propuesta».

## Fuente
Bibliografía del paper estudiado, con año y sello si aparecen en la fuente.

---

[ESTUDIANDO] doc{doc_id}: {title}

{source}

---

[OTRAS TECNICAS DE LA BASE — usalas solo para la sección de relación]
{bloque_otros}"""
    return p, {"doc_id": doc_id, "title": title, "truncado": truncado,
               "chars_fuente": len(source), "n_otros": len(otros)}


def normalize_pointers(text: str) -> tuple[str, int]:
    """Normaliza punteros mal formados a `[doc:N:M]`, el único que parsean
    `_cited_chunks`, `calibrate_r4` y `rescore_r4`.

    Se corrigió el 2026-10-12 al medir el brazo E: **48 de 197 punteros**
    salían como `[doc:5:chunk:13]` y no resolvían nunca — existían en el texto
    pero eran invisibles para B8 y para la capa mecánica de R4 (§7.1).

    Es una edición de **cadena, determinista, sin LLM** y solo sobre corchetes:
    no reescribe prosa, que es exactamente lo que destruyó P3 (§5.8.3). Lo
    entreparentizado del estilo «(doc6: chunk 0)» **no se toca** — es prosa, no
    un puntero, y convertirlo sería reescribir la frase.
    """
    n = 0

    def _fix(m: re.Match) -> str:
        nonlocal n
        inner = m.group(0)[1:-1]
        nums = re.findall(r"\d+", inner)
        if len(nums) >= 2:
            out = f"[doc:{nums[0]}:{nums[1]}]"
        elif len(nums) == 1:
            out = f"[doc:{nums[0]}:0]"
        else:
            return m.group(0)
        n += 1
        return out

    # Solo corchetes que no son ya canonicos y que parecen puntero.
    out = re.sub(r"\[(?!doc:\d+:\d+\])doc[^\]]{0,30}\]", _fix, text)
    return out, n


def study_paper(doc_id: int, *, force: bool = False, temperature: float = 0.0) -> dict:
    """Genera (o recupera) el estudio de un paper y lo persiste en la wiki.

    `force=True` regenera aunque ya exista. Por defecto el estudio es
    **estable**: se escribe una vez y se reutiliza, que es lo que le da valor
    de transferencia — regenerarlo cada vez sería volver a empezar de cero.
    """
    slug = f"study-{doc_id}"
    if not force:
        from bibliotecario.coevolve import wiki
        cur = wiki.get_page(slug)
        if cur and cur.get("body"):
            return {"ok": True, "doc_id": doc_id, "slug": slug, "cached": True,
                    "study": cur["body"], "meta": {"title": cur["title"]}}

    from bibliotecario.core import llm
    prompt, meta = _prompt(doc_id)
    text = llm.generate(prompt, max_tokens=STUDY_MAX_TOKENS, temperature=temperature)
    if not text.strip():
        logger.error("study_paper: LLM devolvio vacio para doc%s", doc_id)
        return {"ok": False, "doc_id": doc_id, "slug": slug, "error": "llm_vacio"}

    text, n_norm = normalize_pointers(text)
    if n_norm:
        logger.info("study_paper: normalizados %d punteros en doc%s", n_norm, doc_id)

    from bibliotecario.coevolve import wiki
    wiki.upsert_page(slug, f"[estudio] {meta['title']}", text, "study")
    logger.info("study_paper: doc%s estudiado (%d chars, truncado=%s)",
                doc_id, len(text), meta["truncado"])
    return {"ok": True, "doc_id": doc_id, "slug": slug, "cached": False,
            "study": text, "meta": meta}


def get_study(doc_id: int) -> str | None:
    from bibliotecario.coevolve import wiki
    p = wiki.get_page(f"study-{doc_id}")
    return p["body"] if p else None


def list_studies() -> list[dict]:
    from bibliotecario.coevolve import wiki
    return [p for p in wiki.list_pages(kind="study")]
