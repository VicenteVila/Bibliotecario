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
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bibliotecario.agent.tools import _source_for
from bibliotecario.core.llm import _endpoint, _openai_compat_usage
from bibliotecario.knowledge import procedural as P

ROOT = Path(__file__).resolve().parents[1]
AB = ROOT / "evals" / "results" / "result_blueprint_ab.json"
OUT = ROOT / "evals" / "results" / "result_q1_r4r5.json"

JUDGE_MODEL = os.environ.get("JUDGE_MODEL", "openai/gpt-oss-20b")
JUDGE_PROVIDER = os.environ.get("JUDGE_PROVIDER", "nvidia")
# gpt-oss-20b razona en prosa ANTES del JSON. Con 1400 se cortaba a mitad del
# razonamiento (medido: tres fallos seguidos); con 2600 seguía cortándose en 9
# de 15. Se sube el tope **y** se reduce la carga: pedir TODAS las
# fabricaciones le obliga a enumerar, que es lo que se come los tokens.
# Mismo bug que el del juez de score (judge.py, JUDGE_MAX_TOKENS).
MAX_TOKENS = int(os.environ.get("Q1_MAX_TOKENS", "3600"))

# dec. 16 — el juez corría a temperature=0.2 y eso bastaba para que **el mismo
# blueprint** cambiara de veredicto entre dos juicios: medido, 52% de flips en
# R5 y 33% en R4 (§8.8). La mitad de la varianza era muestreo, no criterio.
# Se baja a 0 antes de re-medir.
JUDGE_TEMPERATURE = float(os.environ.get("Q1_TEMPERATURE", "0"))

# HITO13 §1.A — enmienda 2 (fuente completa): cap de la FUENTE en el cuerpo
# del prompt. Durante H1-H18 y E12 fue 9000 (0,86%-10,4% del paper según la
# técnica): los veredictos R4/R5 resultaron función de ese sliver (E12: 0/4
# con falsos positivos). 160000 > la fuente más larga (138.667) — sin
# truncación. PROMPT, blueprint[:9000], modelo y temp intactos.
FUENTE_MAX = int(os.environ.get("Q1_FUENTE_MAX", "160000"))
# Corta del BLUEPRINT en el prompt del juez. El default 9000 fue congelado
# con los brazos históricos: E mide ≤6736 chars y nunca lo alcanzó, pero P
# (nemotron-ultra) escribe 7-12k y 10/15 blueprints se cortaban — el juez no
# veía la cola (Bibliografía, declaraciones de silencio), que es donde vive
# R5. Medido al cerrar POSICIONAL_PLAN.md §5 (2026-10-21); para P se juzga
# con Q1_BP_MAX=16000 (vista completa, comparable porque E nunca se truncó).
BP_MAX = int(os.environ.get("Q1_BP_MAX", "9000"))

PROMPT = """Eres un revisor estricto de rigor de citación sobre artículos científicos.

Recibes la FUENTE (texto real del paper) y un BLUEPRINT escrito a partir de ella.

R4 — No atribuir a la fuente lo que la fuente no dice.
R5 — Declarar los silencios. Si la fuente no especifica un detalle y el
     blueprint lo rellena como si lo supiera, es un fallo. Si dice
     «el paper no especifica…», eso CUMPLE R5.

**Tu ÚNICA salida es el objeto JSON de abajo.** Sin prosa antes, sin prosa
después, sin ```markdown, sin explicación. El razonamiento se come los tokens
y el JSON se corta a mitad; eso ya ha pasado.

**El veredicto se decide sobre TODO el blueprint, no sobre la lista de
ejemplos.** Da exactamente UN ejemplo por lista si hay fallo, o la lista
vacía si no lo hay. No enumeres todos: la lista es prueba, no el juicio.

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
    # dec. 18: el endpoint puede fijarse por env para correr contra un
    # proveedor que _endpoint() no conoce (Cerebras, Mistral…), sin tocar el
    # pipeline compartido de bibliotecario.core.llm.
    base_url = os.environ.get("Q1_BASE_URL") or ""
    custom = bool(base_url)
    if base_url:
        key = os.environ.get("Q1_API_KEY") or ""
    else:
        base_url, key = _endpoint(JUDGE_PROVIDER)
    if not key:
        return {"error": f"sin key para {JUDGE_PROVIDER}"}
    body = (PROMPT + f"\n\nFUENTE:\n{source[:FUENTE_MAX]}"
            f"\n\nBLUEPRINT:\n{blueprint[:BP_MAX]}")
    model = model or JUDGE_MODEL
    # no_think mete `chat_template_kwargs` en el payload. Solo lo usa el camino
    # de NVIDIA, que es con el que se midió §8.10 — así esa medición sigue
    # siendo comparable. Groq y Cerebras lo rechazan con HTTP 400
    # «property 'chat_template_kwargs' is unsupported».
    solo_nvidia = not custom and JUDGE_PROVIDER == "nvidia"
    # Reintentos: Groq/Gemini devuelven 429 al saturar y eso NO es un fallo de
    # parseo. Pero un 429 **repetido** significa cuota agotada, y reintentarlo
    # seis veces solo quema el presupuesto diario sin ninguna posibilidad de
    # éxito. Se limita a 2 y se rinde: un 429 persistente aborta la corrida en
    # lugar de vaciarla.
    ult = ""
    for intento in range(3):
        try:
            raw, _ = _openai_compat_usage(base_url, key, model, body,
                                          max_tokens=MAX_TOKENS,
                                          temperature=JUDGE_TEMPERATURE,
                                          no_think=solo_nvidia)
        except Exception as e:
            ult = str(e)[:200]
            if ("429" in ult or "rate" in ult.lower()
                    or "HTTP 5" in ult or "timed out" in ult.lower()):
                time.sleep(min(60, 5 * 2 ** intento))
                continue
            return {"error": ult}
        got = _parse(raw)
        if got:
            return got
        # JSON incomprensible: lo reintenta también, que es barato y el
        # criterio de la dec. 18 exige 0 fallos de parseo.
        ult = f"no parseable: {(raw or '')[:120]}"
        time.sleep(2)
    return {"error": ult}


def _source(technique: str) -> str:
    procs = P.list_procedures(technique=technique)
    _, src = _source_for(technique, procs, max_chunks=8, max_chars=9000)
    return src


def main() -> int:
    arm = "C"
    src = AB
    for a in sys.argv[1:]:
        if a.startswith("--arm="):
            arm = a.split("=", 1)[1]
        elif a.startswith("--file="):
            # Brazos evaluados fuera del A/B (ruta 5) viven en su propio
            # fichero: mezclarlos en result_blueprint_ab.json los haría
            # desaparecer al re-correr el runner.
            src = Path(a.split("=", 1)[1])
    if not src.exists():
        print(f"no hay {src}; corre antes la generacion")
        return 1

    rows = [r for r in json.loads(src.read_text(encoding="utf-8"))
            if r["arm"] == arm and r.get("ok") and r.get("blueprint", "").strip()]
    done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    # Un fallo de parseo NO es una evaluación: se purga, no se marca como
    # hecha, o el resumen se quedaría con n=8 sobre 15 sin que nadie lo viera.
    done = [d for d in done if not (d.get("arm") == arm and d.get("error"))]
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
