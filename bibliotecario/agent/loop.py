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


def parse_tool_call(text: str) -> tuple[str | None, dict]:
    m = TOOL_BLOCK.search(text)
    if not m:
        return None, {}
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None, {}
    name = obj.get("tool")
    args = obj.get("args", {})
    if name not in TOOLS or not isinstance(args, dict):
        return None, {}
    return name, args


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
            if TOOL_BLOCK.search(out):
                # Parecía una llamada pero inválida (tool inexistente o JSON roto): feedback, no respuesta.
                harness.record_error("loop")
                flat += 1
                msg = "llamada inválida: usa exactamente " + '{"tool": nombre, "args": {...}} con un tool del catálogo'
                history.append(msg)
                failed.append(msg)
                continue
            answer = out.strip()
            succeeded.append(f"respuesta final en turno {turn}")
            break
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
        answer = answer or "(presupuesto agotado) " + (best or "sin evidencia")

    harness.finish_run(run_id, None, {"turns": turn + 1, "tools": len(evidence)})
    REF.save_lesson("qa", what_worked="\n".join(succeeded[-5:]), what_failed="\n".join(failed[-5:]),
                    key_insights=f"Q: {question[:200]}")
    return {"answer": answer, "turns": turn + 1, "evidence": evidence, "run_id": run_id}
