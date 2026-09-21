"""Estado re-emitido por turno (diseño en 2 capas ReASearch).

Capa estática: reglas + descripción del loop + catálogo de tools (una vez).
Capa dinámica: re-emitida CADA turno — objetivo, mejor resultado, tabla de evidencia,
historial reciente, lessons, avisos de estancamiento (3+/7+), resumen del árbol.
"""
from __future__ import annotations

STATIC_PROMPT = """Eres Bibliotecario, agente de búsqueda sobre papers ingeridos.
Objetivo: responder con evidencia citada [doc:chunk] o producir blueprints de implementación.

REGLAS:
- Razona antes de actuar. Decide qué tool invocar, cuándo verificar, cuándo parar.
- Verifica ganancias prometedoras con una segunda búsqueda antes de responder.
- Si una estrategia falla 2 veces, cambia de estrategia (no reintentes lo mismo).
- Responde SIEMPRE con citas [doc:chunk] cuando afirmes hechos de los papers.
- Para implementar técnicas: usa build_blueprint y, si se pide código, instantiate_agent_template.

LOOP: piensa → emite UN bloque ```json {"tool": nombre, "args": {...}}``` → recibe resultado → repite.
Cuando tengas la respuesta final, escríbela SIN bloque json.

TOOLS:
- search_papers(query, top_k): búsqueda híbrida sobre chunks.
- retrieve_evidence(query, top_m): caminos de razonamiento PEARL.
- get_subgraph(query, depth): subgrafo contextual.
- get_paper(doc_id): metadata y citas de un documento.
- answer_multi_hop(question, top_k): síntesis multi-documento con citas.
- build_blueprint(technique, goal): guía de implementación.
- instantiate_agent_template(technique, goal): plantilla de agente + BLUEPRINT.md.
- register_skill(name, skill_md, purpose_md): guarda skill ejecutable.
- get_status(): estado del sistema.
"""


def render_state(question: str, evidence: list[str], history: list[str], lessons: str,
                 flat_count: int, best: str) -> str:
    lines = [f"PREGUNTA: {question}", f"MEJOR HASTA AHORA: {best or '—'}", "",
             "EVIDENCIA ACUMULADA:"]
    lines += [f"- {e}" for e in evidence[-10:]] or ["(ninguna)"]
    lines += ["", "HISTORIAL RECIENTE:"]
    lines += [f"- {h}" for h in history[-8:]] or ["(inicio)"]
    lines += ["", f"LESSONS:\n{lessons or '(ninguna)'}"]
    if flat_count >= 7:
        lines.append("\n[AVISO ESTANCAMIENTO 7+] Llevas 7 turnos sin progreso: haz DIAGNÓSTICO "
                     "(get_subgraph con otra formulación) o responde con lo disponible.")
    elif flat_count >= 3:
        lines.append("\n[AVISO ESTANCAMIENTO 3+] Sin progreso en 3 turnos: cambia de tool o de consulta.")
    lines.append("\nResponde con UN bloque json de tool o con la respuesta final.")
    return "\n".join(lines)
