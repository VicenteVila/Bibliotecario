"""Loop ReASearch sobre Gemini: protocolo ReAct en texto + harness siempre activo.

- Harness habilitado por defecto (corrige use_harness=False del origen).
- PFs cableados al loop (corrige /pfs y /pf_run no registrados).
- Runs persistidos (corrige cero persistencia); trayectorias alimentan al refiner (F4).
- Protocolo de tools en texto (```json) en vez de function-calling nativo: robusto a largo plazo.
"""
from __future__ import annotations

import json
import logging
import re

from bibliotecario.agent import state as ST
from bibliotecario.agent.tools import TOOLS, tool_schemas
from bibliotecario.core.llm import generate
from bibliotecario.harness.runtime import get_harness
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
    return any(("tool" in o or any(k in o for k in ("query", "top_k", "top_m", "technique")))
               for o in _bare_objects(text))


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


def _final_answer(question: str, best: str, evidence: list[str], flat: int, retries: int = 1) -> str:
    """Cierre forzado: pide una respuesta en prosa a partir de la evidencia reunida.

    Evita que el loop termine con el volcado JSON de un tool como 'respuesta'.
    """
    prompt = (ST.STATIC_PROMPT + "\n\nPREGUNTA: " + question +
              "\n\nEVIDENCIA REUNIDA:\n" + ("\n".join(evidence[-8:]) or "(ninguna)") +
              f"\n\nMejor resultado parcial:\n{best or '(ninguno)'}\n"
              f"\nTurnos sin progreso: {flat}.\n"
              "CIERRE OBLIGADO: responde YA en prosa (máx 150 palabras) usando solo esta evidencia y "
              "citando [doc:chunk]. No emitas ningún bloque json ni vuelques resultados crudos.")
    out = generate(prompt, max_tokens=512, retries=retries).strip()
    if _toolish(out):
        return ""
    return out


def _synthesize(question: str, retries: int = 1) -> str:
    """Cierre de último recurso: QA multi-documento (resume y cita, sin protocolo de tools)."""
    try:
        out = str(TOOLS["answer_multi_hop"]["fn"](question=question, top_k=6).get("answer", ""))
    except Exception as e:  # degradación con gracia
        logger.warning("Síntesis multi-hop falló: %s", str(e)[:120])
        return ""
    return "" if out.startswith("(extractivo)") else out


def run(question: str, max_turns: int = MAX_TURNS) -> dict:
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
        prompt = (ST.STATIC_PROMPT + "\n\n" + ST.render_state(question, evidence, history,
                                                              load_lessons(), flat, best))
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
            answer = out.strip()
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
        call_sig = f"{name}:{sorted(args)}"
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
    REF.save_lesson("qa", what_worked="\n".join(succeeded[-5:]), what_failed="\n".join(failed[-5:]),
                    key_insights=f"Q: {question[:200]}")
    return {"answer": answer, "turns": turn + 1, "evidence": evidence, "run_id": run_id}
