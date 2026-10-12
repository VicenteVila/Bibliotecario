"""Q1 — R4 y R5 sobre blueprints reales, con el paper delante (§2.E, §3.2).

R4 (no atribuir lo que la fuente no dice) y R5 (declarar los silencios) **no
son mecánicas**: no se pueden comprobar con regex. Por eso van con el juez, que
ya está calibrado contra los defectos conocidos de Task-CoEvolve (5c: 2/2
cogidos, score 2 en ambos).

La referencia es **el texto de la fuente**, no una opinión: los chunks de la
técnica, que es lo único que el blueprint podía consultar. Si el juez acusa al
blueprint de atribuir algo que no está ahí, es un falso positivo que se puede
revisar contra el propio chunk.

A diferencia de `judge()` de evaluación, aquí no se trunca la respuesta a 1500
chars: un blueprint de verdad mide 4-6k y R4/R5 viven en todo el documento,
sobre todo en la bibliografía del final.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bibliotecario.agent.tools import _source_for
from bibliotecario.core.llm import _endpoint, _openai_compat_usage
from bibliotecario.knowledge import procedural as P

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "evals" / "result_blueprint_ab.json"
OUT = ROOT / "evals" / "result_q1_r4r5.json"

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "openai/gpt-oss-20b")
JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "nvidia")
# gpt-oss-20b razona en prosa ANTES del JSON. Con 1400 se cortaba a mitad del
# razonamiento (medido: tres fallos seguidos); con 2600 seguía cortándose en 9
# de 15. Se sube el tope **y** se reduce la carga: pedir TODAS las
# fabricaciones le obliga a enumerar, que es lo que se come los tokens.
# Mismo bug que el del juez de score (judge.py, JUDGE_MAX_TOKENS).
MAX_TOKENS = int(os.environ.get("Q1_MAX_TOKENS", "3600"))

PROMPT = """Eres un revisor estricto de rigor de citación sobre artículos científicos.

Recibes la FUENTE (texto real del paper) y un BLUEPRINT escrito a partir de ella.

R4 — No atribuir a la fuente lo que la fuente no dice.
R5 — Declarar los silencios. Si la fuente no especifica un detalle y el
     blueprint lo rellena como si lo supiera, es un fallo. Si dice
     «el paper no especifica…», eso CUMPLE R5.

**Responde directamente con el JSON, sin razonamiento previo.** Da como mucho
3 ejemplos en cada lista; no enumeres todos.

{"r4_ok": <true|false>, "r4_fabricaciones": ["<ejemplo>", ...],
 "r5_ok": <true|false>, "r5_rellenados": ["<ejemplo>", ...],
 "verdict": "<una frase>"}"""


def _parse(raw: str) -> dict | None:
    if not raw:
        return None
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    for cand in (clean, clean[clean.find("{"):clean.rfind("}") + 1] if "{" in clean else ""):
        if not cand:
            continue
        try:
            o = json.loads(cand)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(o.get("r4_ok"), bool) and isinstance(o.get("r5_ok"), bool):
            return {
                "r4_ok": o["r4_ok"],
                "r4_fabricaciones": [str(x)[:200] for x in (o.get("r4_fabricaciones") or [])][:8],
                "r5_ok": o["r5_ok"],
                "r5_rellenados": [str(x)[:200] for x in (o.get("r5_rellenados") or [])][:8],
                "verdict": str(o.get("verdict", ""))[:300],
            }
    return None


def q1(source: str, blueprint: str, model: str | None = None) -> dict:
    base_url, key = _endpoint(JUDGE_PROVIDER)
    if not key:
        return {"error": f"sin key para {JUDGE_PROVIDER}"}
    body = (PROMPT + f"\n\nFUENTE:\n{source[:9000]}\n\nBLUEPRINT:\n{blueprint[:9000]}")
    model = model or JUDGE_MODEL
    try:
        raw, _ = _openai_compat_usage(base_url, key, model, body,
                                      max_tokens=MAX_TOKENS, temperature=0.2)
    except Exception as e:
        return {"error": str(e)[:200]}
    got = _parse(raw)
    return got or {"error": f"no parseable: {(raw or '')[:120]}"}


def _source(technique: str) -> str:
    procs = P.list_procedures(technique=technique)
    _, src = _source_for(technique, procs, max_chunks=8, max_chars=9000)
    return src


def main() -> int:
    if not AB.exists():
        print("no hay result_blueprint_ab.json; corre antes el A/B")
        return 1
    arm = "C"
    for a in sys.argv[1:]:
        if a.startswith("--arm="):
            arm = a.split("=", 1)[1]

    rows = [r for r in json.loads(AB.read_text(encoding="utf-8"))
            if r["arm"] == arm and r.get("ok") and r.get("blueprint", "").strip()]
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    seen = {(d["technique"], d["run"]) for d in done if d.get("arm") == arm}

    print("=" * 70)
    print(f"Q1 — R4/R5 sobre brazo {arm}  ·  juez {JUDGE_MODEL} @ {JUDGE_PROVIDER}")
    print(f"blueprints: {len(rows)}   ya evaluados: {len(seen)}")
    print("=" * 70)

    srcs: dict[str, str] = {}
    for r in rows:
        if (r["technique"], r["run"]) in seen:
            continue
        if r["technique"] not in srcs:
            srcs[r["technique"]] = _source(r["technique"])
        print(f"  {r['technique']} run {r['run']} ...", end=" ", flush=True)
        res = q1(srcs[r["technique"]], r["blueprint"])
        done.append({"arm": arm, "technique": r["technique"], "run": r["run"], **res})
        OUT.write_text(json.dumps(done, ensure_ascii=False, indent=2), encoding="utf-8")
        if res.get("error"):
            print(f"ERROR {res['error']}")
        else:
            print(f"R4={'OK' if res['r4_ok'] else 'FALLA'}({len(res['r4_fabricaciones'])}) "
                  f"R5={'OK' if res['r5_ok'] else 'FALLA'}({len(res['r5_rellenados'])})")

    _summary(done, arm)
    return 0


def _summary(done: list[dict], arm: str) -> None:
    rows = [d for d in done if d["arm"] == arm and not d.get("error")]
    print("\n" + "=" * 70)
    print(f"Resumen R4/R5 — brazo {arm}  (n={len(rows)})")
    print("=" * 70)
    if not rows:
        return
    r4 = sum(1 for d in rows if d["r4_ok"])
    r5 = sum(1 for d in rows if d["r5_ok"])
    fab = sum(len(d["r4_fabricaciones"]) for d in rows) / len(rows)
    rel = sum(len(d["r5_rellenados"]) for d in rows) / len(rows)
    print(f"  R4 cumple (no atribuye lo que la fuente no dice)  {r4}/{len(rows)}")
    print(f"  R5 cumple (declara los silencios)                 {r5}/{len(rows)}")
    print(f"  fabricaciones atribuidas / blueprint              {fab:5.2f}")
    print(f"  detalles rellenados / blueprint                   {rel:5.2f}")
    worst = sorted(rows, key=lambda d: (d["r4_ok"], -len(d["r4_fabricaciones"])))[:3]
    print("\n  Peores en R4:")
    for d in worst:
        mark = "OK " if d["r4_ok"] else "MAL"
        print(f"    [{mark}] {d['technique']} run{d['run']}: {d['verdict'][:90]}")


if __name__ == "__main__":
    raise SystemExit(main())
