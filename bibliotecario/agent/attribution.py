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
)

# Frase con puntero a un chunk, que es lo que se puede verificar.
# OJO: `[^\n.!?]*` no sirve aquí — corta en el punto y se come el propio
# término inventado, que casi siempre va ANTES del puntero («usa
# AdaptiveHarnessEngine para orquestar. [doc:1:0]»). Medido: el primer
# verificador no cazó nada por esto. Se toma una ventana hacia atrás.
_POINTER = re.compile(r"\[doc:(\d+):(\d+)\]")
_WINDOW = 260


def _terms(sentence: str) -> list[str]:
    """Términos técnicos distintivos de una frase.

    Son lo que tendría que aparecer en la fuente si la atribución es honesta:
    nombres de módulo, compuestos técnicos y lo entrecomillado. Las palabras
    comunes no cuentan, o todo sería sospechoso.
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
            violations.append({"tipo": "puntero_roto", "chunk": f"{doc_id}:{chunk_idx}",
                               "frase": sentence[:200], "termino": None})
            continue
        cited_flat = cited.lower()
        for term in _terms(sentence):
            if term.lower() not in cited_flat:
                violations.append({"tipo": "termino_ausente",
                                   "chunk": f"{doc_id}:{chunk_idx}",
                                   "frase": sentence[:200], "termino": term})
    return violations


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
