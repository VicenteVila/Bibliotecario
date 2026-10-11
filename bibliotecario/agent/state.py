"""Estado re-emitido por turno (diseño en 2 capas ReASearch).

Capa estática: reglas + descripción del loop + catálogo de tools (una vez).
Capa dinámica: re-emitida CADA turno — objetivo, mejor resultado, tabla de evidencia,
historial reciente, lessons, avisos de estancamiento (3+/7+), resumen del árbol.
"""
from __future__ import annotations

import os

# Prompt de parada (HITO0, commit 15261a0): la orden "CIERRE OBLIGADO: responde YA"
# era la causa de la fabricacion (31.5% -> 0%, McNemar p <= 4.8e-07). PROMPT_LEGACY=1
# restaura el texto previo.
#
# Existe para poder comparar LOS DOS PROMPTS A LA MISMA TEMPERATURA. Sin esto, la
# ventaja de r5 (4.714) no se puede separar del efecto de temperatura: r5 corrio a
# 0.2 y promptstop a 0.0, y bajar de 0.2 a 0.0 cuesta ~0.17 de juez en respondibles
# mientras baja la fabricacion del 51.6% al 33.9% (p=0.019). Es una palanca con
# efecto de signo opuesto en los dos umbrales del Hito 1.
PROMPT_LEGACY = os.environ.get("PROMPT_LEGACY", "0") == "1"

# Eje independiente: el cierre de _close_prompt cambio en el mismo commit que el
# texto de arriba, pero no hace el mismo trabajo. El de estado pone la orden de
# responder; el de cierre decide que hacer cuando el dato NO esta. Desacoplarlos
# da el 2x2 (estado x cierre) con las dos esquinas ya medidas:
#
#   estado viejo + cierre viejo = r5 / r5legacy_t0  -> juez 4.667, fab 22-27%
#   estado nuevo + cierre nuevo = promptstop        -> juez 4.314, fab   0%
#
# y deja las dos esquinas que faltan, que son las candidatas del Hito 1.
# Por defecto sigue a PROMPT_LEGACY para que `PROMPT_LEGACY=1` siga siendo la
# config de r5 exacta.
CLOSE_LEGACY = os.environ.get("CLOSE_LEGACY", "1" if PROMPT_LEGACY else "0") == "1"

# Candidata C del Hito 1. El diff de arriba hace 4 cosas y el experimento del
# 2x2 las ha separado: cambiar SOLO el cierre no movio nada (candA vs legacy:
# juez +0.000 con p=1.0, y 14/64 de fabricacion en las dos), mientras que
# cambiar el estado bajo la fabricacion de 14/64 a 0/64 y el juez 0.315.
# O sea: la fabricacion la arreglo el objetivo ("declarar que no aparece" vale
# como respuesta) y la calidad la costearon las dos lineas de urgencia que se
# quitaron al mismo tiempo. URGENCY=1 las devuelve SIN tocar el objetivo.
URGENCY = os.environ.get("URGENCY", "0") == "1"

# Candidata E del Hito 1. Mide lo que de verdad separa a promptstop de r5, mirando
# los items y no el prompt: la ventaja de calidad no es "ansiedad por responder"
# (E la quita candA a candC), esta en dos fallos concretos de anclaje medidos en
# la run de candA contra promptstop:
#
#   tce-b1  promptstop "evidence does not contain..." (juez 2, 0 citas)
#           candA      "89 tasks ... GPT-5.6 Luna ... [3:22][3:23]" (juez 5)
#           -> falsa abstencion: el dato SI esta en el corpus y no se recupera
#   reas-b4 ambos responden lo mismo, promptstop con 0 citas (juez 2),
#           candA con [4:33][4:36] y cifras (juez 5)
#           -> responde sin anclaje, no abstiene
#
# Esos dos items valen 6 puntos sobre los 6,55 que cuesta pasar de 4,314 a 4,50.
# E solo anade: busqueda profunda ANTES de poder declarar ausencia, y cita
# OBLIGATORIA antes de poder responder. No toca el objetivo de abstencion ni el
# cierre condicional, que es lo que mantiene la fabricacion a 0/64.
E_GROUND = os.environ.get("E_GROUND", "0") == "1"

# Candidata F = E + guarda contra fuga de razonamiento.
#
# E subio el juez +0,086 (4,314 -> 4,400) y de verdad arreglo los dos items que
# apuntaba (tce-b1 2->5, reas-b2 1->5), pero encima DUPLICO las respuestas que
# son narracion del propio proceso emitiendose como respuesta final:
#
#   promptstop: 2 (pg-b5=1, wiki-b4=1)
#   candE      : 4 (tce-b5=1, tce-b6=1, tce-b7=4, wiki-b4=1)
#
#   tce-b5 bajo E: 'We need to answer: ... The deep sweep shows chunk 15, 16, 17, 18...'
#   tce-b6 bajo E: 'We need to answer: ... We saw in deep sweep chunk [3:24]... Let's locate...'
#
# Eso cuesta -8 a -9 puntos sobre los +12 que gano en el resto: neto +3 de 35.
# F solo anade la prohibicion explicita de devolver razonamiento, lista de chunks
# o plan de busqueda. Proyeccion con la fuga eliminada: 4,63-4,66, es decir por
# encima de 4,50. No toca E_GROUND, el objetivo de estado ni el cierre.
ANS_CLEAN = os.environ.get("ANS_CLEAN", "0") == "1"

_STATIC_PROMPT_NUEVO = """Eres Bibliotecario, agente de búsqueda sobre papers ingeridos.
Objetivo: responder con evidencia citada [doc:chunk], producir blueprints de
implementación, o declarar que la evidencia reunida no contiene lo pedido. Las tres
son respuestas válidas; una respuesta con un dato que no responde a lo preguntado no.

REGLAS:
- Razona antes de actuar. Decide qué tool invocar, cuándo verificar, cuándo parar.
- Verifica ganancias prometidoras con una segunda búsqueda antes de responder.
- Si una estrategia falla 2 veces, cambia de estrategia (no reintentes lo mismo).
- Responde SIEMPRE con citas [doc:chunk] cuando afirmes hechos de los papers.
- Para implementar técnicas: usa build_blueprint y, si se pide código, instantiate_agent_template.

LOOP: piensa → emite UN bloque ```json {"tool": nombre, "args": {...}}``` → recibe resultado → repite.
Cuando tengas la respuesta final, escríbela SIN bloque json.

CIERRE (obligatorio):
- Con 1-2 tools suele haber evidencia suficiente: cierra pronto.
- Máximo 3 llamadas a tools por pregunta.
- Nunca devuelvas JSON crudo como respuesta final: es una llamada a tool, no una respuesta.
- Si lo que pide la pregunta no aparece en la evidencia, decláralo en una frase y cierra
  sin dar ningún dato por cierto. Responder con algo parecido es peor que no responder.
- Si algún tool falla, dilo con una frase y pasa a la respuesta final.

TOOLS:
- search_papers(query, top_k): búsqueda híbrida sobre chunks.
- retrieve_evidence(query, top_m): caminos de razonamiento PEARL.
- get_subgraph(query, depth): subgrafo contextual.
- deep_sweep(question, per_doc): barrido profundo de los mejores chunks de cada paper
  (para detalles que el top-6 no alcanza; no consume LLM). Úsalo si la evidencia es débil.
- get_paper(doc_id): metadata y citas de un documento.
- answer_multi_hop(question, top_k): síntesis multi-documento con citas.
- build_blueprint(technique, goal): guía de implementación.
- instantiate_agent_template(technique, goal): plantilla de agente + BLUEPRINT.md.
- register_skill(name, skill_md, purpose_md): guarda skill ejecutable.
- get_status(): estado del sistema.
"""

# Texto previo a 15261a0, literal. Solo se usa con PROMPT_LEGACY=1.
_STATIC_PROMPT_LEGACY = """Eres Bibliotecario, agente de búsqueda sobre papers ingeridos.
Objetivo: responder con evidencia citada [doc:chunk] o producir blueprints de implementación.

REGLAS:
- Razona antes de actuar. Decide qué tool invocar, cuándo verificar, cuándo parar.
- Verifica ganancias prometedoras con una segunda búsqueda antes de responder.
- Si una estrategia falla 2 veces, cambia de estrategia (no reintentes lo mismo).
- Responde SIEMPRE con citas [doc:chunk] cuando afirmes hechos de los papers.
- Para implementar técnicas: usa build_blueprint y, si se pide código, instantiate_agent_template.

LOOP: piensa → emite UN bloque ```json {"tool": nombre, "args": {...}}``` → recibe resultado → repite.
Cuando tengas la respuesta final, escríbela SIN bloque json.

CIERRE (obligatorio):
- Con 1-2 tools ya tienes evidencia suficiente: RESPONDE de inmediato.
- Máximo 3 llamadas a tools por pregunta; después responde con lo que tengas.
- Nunca devuelvas JSON crudo como respuesta final: es una llamada a tool, no una respuesta.
- Si algún tool falla o no hay evidencia, dilo con una frase y pasa a la respuesta final.

TOOLS:
- search_papers(query, top_k): búsqueda híbrida sobre chunks.
- retrieve_evidence(query, top_m): caminos de razonamiento PEARL.
- get_subgraph(query, depth): subgrafo contextual.
- deep_sweep(question, per_doc): barrido profundo de los mejores chunks de cada paper
  (para detalles que el top-6 no alcanza; no consume LLM). Úsalo si la evidencia es débil.
- get_paper(doc_id): metadata y citas de un documento.
- answer_multi_hop(question, top_k): síntesis multi-documento con citas.
- build_blueprint(technique, goal): guía de implementación.
- instantiate_agent_template(technique, goal): plantilla de agente + BLUEPRINT.md.
- register_skill(name, skill_md, purpose_md): guarda skill ejecutable.
- get_status(): estado del sistema.
"""

if URGENCY:
    # Solo las dos lineas de urgencia del CIERRE. El objetivo con la rama de
    # abstencion y la linea "si no aparece, declaralo" se quedan como estan: son
    # lo que mantiene la fabricacion a 0.
    _STATIC_PROMPT_NUEVO = (
        _STATIC_PROMPT_NUEVO
        .replace("- Con 1-2 tools suele haber evidencia suficiente: cierra pronto.",
                 "- Con 1-2 tools ya tienes evidencia suficiente: RESPONDE de inmediato.")
        .replace("- Máximo 3 llamadas a tools por pregunta.",
                 "- Máximo 3 llamadas a tools por pregunta; después responde con "
                 "lo que tengas.")
    )

if E_GROUND:
    # Se insertan ANTES de la rama de ausencia, no en su lugar: primero hay que
    # haber buscado de verdad y tener cita, y solo despues se permite declarar
    # que no aparece. Si se sustituyera la rama, se reintroduciria la
    # fabricacion que el objetivo de estado ya no permite.
    _VIEJO = "- Si lo que pide la pregunta no aparece en la evidencia, decláralo en una frase y cierra"
    _NUEVO = ("- Antes de declarar que no aparece, ejecuta deep_sweep: el dato puede estar\n"
              "  en el corpus y fuera de las piezas que recuperaste.\n"
              "- Si vas a responder, cada afirmación necesita su [doc:chunk]: sin ninguna\n"
              "  cita, recupera evidencia antes de cerrar.\n"
              + _VIEJO)
    assert _VIEJO in _STATIC_PROMPT_NUEVO, "el cierre de estado cambio: E_GROUND no se puede aplicar"
    _STATIC_PROMPT_NUEVO = _STATIC_PROMPT_NUEVO.replace(_VIEJO, _NUEVO, 1)

if ANS_CLEAN:
    # Se ancla en la ultima linea de CIERRE y se inserta ANTES: es una restriccion
    # sobre la forma de la respuesta final, vale tanto si se responde como si se
    # declara ausencia, y va despues de las reglas de busqueda para que se lea
    # como "una vez buscaste, ya no vuelques el proceso".
    _VIEJO = "- Si algún tool falla, dilo con una frase y pasa a la respuesta final."
    _NUEVO = ("- La respuesta final es SOLO la respuesta ya resuelta con sus citas:\n"
              "  nunca el razonamiento, la lista de chunks mirados ni el plan de búsqueda.\n"
              + _VIEJO)
    assert _VIEJO in _STATIC_PROMPT_NUEVO, "el cierre de estado cambio: ANS_CLEAN no se puede aplicar"
    _STATIC_PROMPT_NUEVO = _STATIC_PROMPT_NUEVO.replace(_VIEJO, _NUEVO, 1)

STATIC_PROMPT = _STATIC_PROMPT_LEGACY if PROMPT_LEGACY else _STATIC_PROMPT_NUEVO


def render_state(question: str, evidence: list[str], history: list[str], lessons: str,
                 flat_count: int, best: str) -> str:
    lines = [f"PREGUNTA: {question}", f"MEJOR HASTA AHORA: {best or '—'}", "",
             "EVIDENCIA ACUMULADA:"]
    lines += [f"- {e}" for e in evidence[-10:]] or ["(ninguna)"]
    lines += ["", "HISTORIAL RECIENTE:"]
    lines += [f"- {h}" for h in history[-8:]] or ["(inicio)"]
    lines += ["", f"LESSONS:\n{lessons or '(ninguna)'}"]
    if flat_count >= 7:
        lines.append("\n[AVISO ESTANCAMIENTO 7+] Llevas 7 turnos sin progreso: responde AHORA con la "
                     "evidencia acumulada, citing [doc:chunk]. No lances más tools.")
    elif flat_count >= 3:
        lines.append("\n[AVISO ESTANCAMIENTO 3+] Sin progreso en 3 turnos: cambia de tool o responde ya.")
    lines.append("\nAcción: UN bloque json de tool, o la respuesta final en prosa. "
                 "Si ya tienes evidencia, la respuesta final es la opción correcta.")
    return "\n".join(lines)
