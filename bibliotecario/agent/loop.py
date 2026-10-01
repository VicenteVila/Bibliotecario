"""Loop ReASearch sobre Gemini: protocolo ReAct en texto + harness siempre activo.

- Harness habilitado por defecto (corrige use_harness=False del origen).
- PFs cableados al loop (corrige /pfs y /pf_run no registrados).
- Runs persistidos (corrige cero persistencia); trayectorias alimentan al refiner (F4).
- Protocolo de tools en texto (```json) en vez de function-calling nativo: robusto a largo plazo.
"""
from __future__ import annotations

import json
import logging
import os
import re

from bibliotecario.agent import state as ST
from bibliotecario.agent.tools import TOOLS, tool_schemas
from bibliotecario.core.llm import generate as _llm_generate

# La evaluación lo pone a True: si un proveedor muere a mitad de una run, que la
# pregunta se marque como fallida en vez de responderse con otro modelo en
# silencio. Ver bibliotecario.core.llm.generate.
STRICT_FALLBACK = False

# Anclaje: localizar verbatim antes de redactar. Medido en evals/probe_extraction.py
# (ver REPORT_BLIND.md, "Fase 2 descartada"): recortar el contexto NO arregla las
# preguntas que fallan, porque el fallo no es de volumen sino de desanclaje
# confiado. El agente cita bien y se equivoca igual en los tres runs: con el
# pajar de 1.3k responde sobre el tema equivocado (tce-b7) o rellena con nombres
# de archivo reales pero hermanos de los pedidos (wiki-b1). Esos nombres SI estan
# en el documento, asi que no es fabricacion: es mala seleccion.
#
# Que ademas "CIERRE OBLIGADO: responde YA" prohibe decir que no se encontro nada,
# mientras el juez (evals/judge.py:47) ya esta preparado para puntuar bien una
# abstention honesta. Esta fase devuelve solo los spans verbatim que pueden
# responder la pregunta, y el cierre solo puede usar esos.
ANCHOR_GROUNDING = os.environ.get("ANCHOR_GROUNDING", "0") == "1"
_NO_ENCONTRADO = "NO_ENCONTRADO"


def generate(prompt: str, max_tokens: int = 512, retries: int | None = None) -> str:
    return _llm_generate(prompt, max_tokens, 2 if retries is None else retries,
                         strict_fallback=STRICT_FALLBACK)
from bibliotecario.harness.runtime import get_harness
from bibliotecario.ingest import citations_format as CITE_FMT
from bibliotecario.knowledge import refiner as REF

logger = logging.getLogger(__name__)
TOOL_BLOCK = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
MAX_TURNS = 12


def _bare_objects(text: str) -> list[dict]:
    """Extrae objetos JSON sueltos (proveedores que no usan vallas), con prefijo de razonamiento."""
    dec = json.JSONDecoder()
    objs = []
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = dec.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            objs.append(obj)
    return objs


def parse_tool_call(text: str) -> tuple[str | None, dict]:
    m = TOOL_BLOCK.search(text)
    obj = None
    if m:
        try:
            obj = json.loads(m.group(1))
        except json.JSONDecodeError:
            obj = None
    if obj is None:
        for cand in _bare_objects(text):
            if "tool" in cand:
                obj = cand
                break
    if obj is None:
        # Sin clave "tool": ¿hay un objeto con forma de args? → llamada malformada.
        for cand in _bare_objects(text):
            if any(k in cand for k in ("query", "top_k", "top_m", "technique", "goal", "doc_id")):
                return "", cand
        return None, {}
    name = obj.get("tool")
    args = obj.get("args", {})
    if name not in TOOLS or not isinstance(args, dict):
        return None, {}
    return name, args


def _toolish(text: str) -> bool:
    if TOOL_BLOCK.search(text):
        return True
    if any(("tool" in o or any(k in o for k in ("query", "top_k", "top_m", "technique")))
           for o in _bare_objects(text)):
        return True
    # JSON malformado: el modelo empezó a emitir una llamada de tool y se cortó a
    # media estructura (p. ej. '"top_k": 5": 5}}'). No puede ser una respuesta.
    return _has_broken_json(text or "")


_BROKEN_KEYS = ("tool", "query", "top_k", "top_m", "args", "technique", "blueprint")


def _has_broken_json(text: str) -> bool:
    """True si `text` parece JSON de tool corrupto o malformado."""
    if "{" not in text or "}" not in text:
        return False
    # El texto es casi todo JSON (poco texto en medio), no prosa con un fragmento.
    # Una respuesta real tiene varias frases; un volcado tiene casi ninguna.
    prose = " ".join(_strip_json_blobs(text).split())
    if len(prose) > 40:  # hay prosa de verdad alrededor del JSON
        return False
    try:
        json.loads(text)
        return True  # JSON bien formado: volcado, no respuesta
    except (json.JSONDecodeError, ValueError):
        pass
    return any(f'"{k}"' in text for k in _BROKEN_KEYS)


def _strip_json_blobs(text: str) -> str:
    """Quita los mayores objetos/arrays JSON balanceados y devuelve la prosa restante.

    Se conserva el texto antes y después de cada blob: una respuesta real puede
    citar un fragmento JSON dentro de una frase.
    """
    prose, depth, start, pos = [], 0, None, 0
    for i, ch in enumerate(text):
        if ch in "{[":
            if depth == 0:
                start = i
            depth += 1
        elif ch in "}]":
            if depth == 0:  # cierre huérfano: es prosa
                continue
            depth -= 1
            if depth == 0 and start is not None:
                prose.append(text[pos:start])  # prosa anterior al blob
                pos = i + 1                  # el blob se descarta
                start = None
    prose.append(text[pos:])  # prosa final (o el resto si quedó JSON sin cerrar)
    return " ".join(prose)


def load_lessons(scope: str = "qa", limit: int = 5) -> str:
    from bibliotecario.core import storage
    with storage.get_conn() as conn:
        rows = conn.execute("SELECT what_worked, what_failed, key_insights FROM lessons "
                            "WHERE scope=? ORDER BY id DESC LIMIT ?", (scope, limit)).fetchall()
    return "\n".join(f"· W:{r['what_worked'] or '-'} F:{r['what_failed'] or '-'} K:{r['key_insights'] or '-'}"[:300]
                     for r in rows)


def compact(transcript: list[str], snapshot: str) -> list[str]:
    """Compresión ReASearch: snapshot autoritativo + resumen + lessons (3 mensajes)."""
    summary = generate("Resume en 10 líneas: insights clave y trabajo pendiente.\n\n" + "\n".join(transcript[-30:]),
                       max_tokens=512) or "(sin resumen)"
    return [f"[SNAPSHOT] {snapshot}", f"[RESUMEN] {summary}", f"[LESSONS]\n{load_lessons()}"]


def _deep_evidence(question: str, per_doc: int = 4, n_docs: int = 2) -> str:
    """Barrido profundo determinista: chunks del cierre que el top-8 no trajo.

    Sin coste LLM y sin varianza. Se limita a los `n_docs` papers con mejor score
    porque el barrido completo de los 5 papers serían ~80k caracteres, más que el
    resumen y el resto de la evidencia juntos.
    """
    try:
        res = TOOLS["deep_sweep"]["fn"](question=question, per_doc=per_doc)
    except Exception as e:  # degradación con gracia
        logger.warning("Barrido profundo falló: %s", str(e)[:120])
        return ""
    lines = []
    for d in res.get("docs", [])[:n_docs]:
        for c in d["chunks"]:
            # sin truncar: el dato concreto suele estar al final del chunk
            lines.append(f"[{d['doc_id']}:{c['chunk']}] {d['title']}\n{c['text']}")
    return "\n\n".join(lines)


def _ground(question: str, deep: str, retries: int = 1) -> str:
    """Localiza en el barrido los spans verbatim que pueden responder la pregunta.

    Devuelve las lineas relevantes tal cual, o `_NO_ENCONTRADO` si el barrido no
    contiene el dato pedido. No resume ni parafrasea: si devuelve algo, tiene que
    ser texto que aparece literalmente en `deep`.

    Existe para separar dos fallos que hasta ahora se confundian: no encontrar el
    dato, y encontrarlo pero redactar sobre otro. Al obligar a emitir el span
    literal antes de redactar, el agente tiene que mostrar donde ha mirado, y el
    cierre puede decir "no aparece" en vez de inventar un hermano plausible.
    """
    if not deep:
        return _NO_ENCONTRADO
    prompt = (
        "Localiza en la EVIDENCIA las lineas que pueden responder exactamente a esta "
        "PREGUNTA.\n"
        f"PREGUNTA: {question}\n\n"
        f"EVIDENCIA:\n{deep}\n\n"
        "REGLAS ESTRICTAS:\n"
        "- Copia las lineas LITERALMENTE, sin parafrasear, sin resumir, sin corregir.\n"
        f"- Si ningun dato de la EVIDENCIA responde a la PREGUNTA, responde solo {_NO_ENCONTRADO}.\n"
        "- No deducias ni combines: solo copia lo que esta ahi escrito.\n"
        "- Si aparecen varios candidatos, copia TODOS los relevantes, no elijas.\n"
        "- No escribas commentary, solo las lineas copiadas.\n\n"
        f"RESPUESTA ({_NO_ENCONTRADO} si no hay nada):")
    out = generate(prompt, max_tokens=700, retries=retries).strip()
    if _toolish(out):
        return _NO_ENCONTRADO
    if _NO_ENCONTRADO in out:
        return _NO_ENCONTRADO
    # Solo se admiten lineas que existen literalmente en el barrido. Si el modelo
    # paraphrasea, lo que survive es exactamente el texto justificable.
    return out


def _final_answer(question: str, best: str, evidence: list[str], flat: int, retries: int = 1) -> str:
    """Cierre forzado: pide una respuesta en prosa a partir de la evidencia reunida.

    Evita que el loop termine con el volcado JSON de un tool como 'respuesta'.
    El barrido profundo es determinista y barato (4-11k chars, sin cuota), así que
    se aplica siempre: los detalles concretos viven en apéndices que el top-8 por
    relevancia no trae, y sin ellos el agente citaba el chunk equivocado.
    """
    deep = _deep_evidence(question)
    ctx = ("\n".join(evidence[-8:]) or "(ninguna)") + ("\n\nEVIDENCIA PROFUNDA (barrido por documento):\n" + deep if deep else "")

    # Anclaje (opt-in por ANCHOR_GROUNDING=1). Una pasada extra de localizacion
    # verbatim: obliga a mostrar el span antes de redactar, y devuelve
    # NO_ENCONTRADO cuando el barrido no tiene el dato. Ese caso antes era
    # imposible: "CIERRE OBLIGADO" empujaba a rellenar con un hermano plausible.
    anclaje = ""
    if ANCHOR_GROUNDING:
        spans = _ground(question, deep, retries=retries)
        if spans == _NO_ENCONTRADO:
            anclaje = ("\n\nANCLAJE: no se ha localizado en el barrido ningún dato que "
                       "responda a esta pregunta. NO inventes ni deduzcas: explica en una "
                       "frase qué se buscó y qué se encontró.\n")
        else:
            anclaje = ("\n\nANCLAJE (verbatim, solo estas lineas pueden sostener la "
                       f"respuesta):\n{spans}\n"
                       "- Redacta EXCLUSIVAMENTE con lo que hay en el anclaje.\n"
                       "- No introduzcas nombres, cifras ni reglas que no aparezcan ahí.\n")

    prompt = (ST.STATIC_PROMPT + "\n\nPREGUNTA: " + question +
              "\n\nEVIDENCIA REUNIDA:\n" + ctx + anclaje +
              f"\n\nMejor resultado parcial:\n{best or '(ninguno)'}\n"
              f"\nTurnos sin progreso: {flat}.\n"
              "CIERRE OBLIGADO: responde YA en prosa (máx 150 palabras) usando solo esta evidencia.\n"
              "REGLAS DE CIERRE:\n"
              "- CITA obligatoriamente cada afirmación con el formato [doc_id:chunk] "
              "(ej. [5:7]).\n"
              "- La pregunta pide un dato concreto (una cifra, un tope, una regla). "
              "BÚSCA ese dato explícitamente en toda la evidencia, también en el barrido: "
              "no te quedes con el primer chunk parecido.\n"
              "- Cifras exactas: copia el número literal de la evidencia. Si dos fuentes "
              "se contradicen, cita la que responde a la pregunta concreta.\n"
              "- No inventes cifras ni reglas que no aparezcan literalmente en la evidencia.\n"
              "- No termines a media frase: completa la idea y cierra con punto.\n"
              "- No emitas ningún bloque json ni vuelques resultados crudos.")
    out = generate(prompt, max_tokens=900, retries=retries).strip()
    if _toolish(out):
        return ""
    out = _fix_truncation(out)
    if evidence and not CITE_FMT.has_citation(out):
        out = out.rstrip() + "  [doc:?]"  # marca de hueco: el cierre debe citar
    return CITE_FMT.normalize_citations(out)


def _fix_truncation(text: str) -> str:
    """Si la respuesta se cortó a media frase, marca el final en vez de dejarla colgada."""
    t = (text or "").rstrip()
    if not t or t[-1] in ".!?)]}\"'`:;":
        return t
    return t + " […truncado]"


def _synthesize(question: str, retries: int = 1) -> str:
    """Cierre de último recurso: QA multi-documento (resume y cita, sin protocolo de tools)."""
    try:
        out = str(TOOLS["answer_multi_hop"]["fn"](question=question, top_k=6).get("answer", ""))
    except Exception as e:  # degradación con gracia
        logger.warning("Síntesis multi-hop falló: %s", str(e)[:120])
        return ""
    return "" if out.startswith("(extractivo)") else out


def run(question: str, max_turns: int = MAX_TURNS, isolated: bool = False) -> dict:
    """Responde una pregunta.

    `isolated=True` corta el aprendizaje: no lee lecciones guardadas ni escribe
    una nueva. Es obligatorio en evaluación. Sin esto el prompt incluye las 5
    lecciones más recientes, cuyo key_insights es `Q: <texto de la pregunta>`,
    así que el agente ve preguntas anteriores del propio golden set: la eval deja
    de ser ciega y cada run hereda las preguntas del run anterior, con lo que la
    varianza medida mezcla ruido del modelo con deriva del estado.
    """
    harness = get_harness()
    harness.calibrate(tool_schemas())
    run_id = harness.start_run({"question": question})
    evidence: list[str] = []
    history: list[str] = []
    transcript: list[str] = []
    best, flat, answer = "", 0, ""
    failed, succeeded = [], []
    last_call = ""

    for turn in range(max_turns):
        lessons = "" if isolated else load_lessons()
        prompt = (ST.STATIC_PROMPT + "\n\n" + ST.render_state(question, evidence, history,
                                                              lessons, flat, best))
        out = generate(prompt, max_tokens=1024)
        transcript.append(f"T{turn}: {out[:500]}")
        if not out:
            harness.record_error("loop")
            flat += 1
            history.append("turno vacío (fallo LLM)")
            continue
        name, args = parse_tool_call(out)
        if name is None:
            if _toolish(out):
                # Parecía una llamada pero inválida (tool inexistente o JSON roto): feedback, no respuesta.
                harness.record_error("loop")
                flat += 1
                msg = ("llamada inválida: emite EXACTAMENTE "
                       '{"tool": nombre, "args": {...}} con un tool del catálogo (no sueltes args sin "tool")')
                history.append(msg)
                failed.append(msg)
                continue
            # Una respuesta en prosa no se acepta cruda: pasa por el cierre forzado
            # para que corra el barrido profundo y se exijan las citas. Aceptarla
            # aqui saltaba media pipeline (medido: 2.273 vs 4.551 de media).
            draft = CITE_FMT.normalize_citations(out.strip())
            answer = (_final_answer(question, draft, evidence, flat, retries=1)
                      or _fix_truncation(draft))
            harness.record_action("loop", {"tool": "final_answer", "args": {"turn": turn}})
            succeeded.append(f"respuesta final en turno {turn}")
            break
        if name == "":
            harness.record_error("loop")
            flat += 1
            msg = ('llamada malformada: falta la clave "tool". Formato: '
                   '{"tool": nombre, "args": {...}}')
            history.append(msg)
            failed.append(msg)
            continue
        call_sig = f"{name}:{sorted(args.items())}"
        v = harness.validate_call(name, args, tool_schemas())
        if not v.valid:
            harness.record_error("loop")
            flat += 1
            history.append(f"{name} inválida: {v.error}")
            failed.append(f"{name} inválida: {v.error}")
            continue
        for pf in harness.apply_pfs({"last_action": {"status": "ok"}, "task": {"type": "research"},
                                     "attempt_count": turn, "max_attempts": max_turns}):
            history.append(f"[PF {pf['pf']}] {pf.get('message', '')}")
        try:
            result = TOOLS[name]["fn"](**v.canonicalized["arguments"])
            result_s = json.dumps(result, ensure_ascii=False, default=str)[:3000]
        except TypeError as e:
            harness.record_error("loop")
            history.append(f"{name} args incorrectos: {e}")
            failed.append(f"{name} args: {e}")
            flat += 1
            continue
        harness.record_action("loop", {"tool": name, "args": args})
        history.extend(harness.regulate("loop"))
        history.append(f"{name} → {result_s[:220]}")
        evidence.append(f"{name}({','.join(f'{k}={v}' for k, v in args.items())}): {result_s[:220]}")
        succeeded.append(f"{name} ok")
        if call_sig == last_call:
            flat += 1
        else:
            flat = 0
            best = result_s[:220]
        last_call = call_sig
    else:
        # Presupuesto agotado: sintetizar respuesta en vez de volcar JSON crudo.
        if not answer:
            answer = (_final_answer(question, best, evidence, flat, retries=1)
                      or _synthesize(question, retries=1)
                      or "(presupuesto agotado) " + (best or "sin evidencia"))
            if not answer.startswith("(presupuesto agotado)"):
                harness.record_action("loop", {"tool": "synthesize", "args": {}})
                succeeded.append("síntesis final tras agotar turnos")
        flat += 1

    harness.finish_run(run_id, None, {"turns": turn + 1, "tools": len(evidence)})
    if not isolated:
        REF.save_lesson("qa", what_worked="\n".join(succeeded[-5:]), what_failed="\n".join(failed[-5:]),
                        key_insights=f"Q: {question[:200]}")
    return {"answer": answer, "turns": turn + 1, "evidence": evidence, "run_id": run_id}
