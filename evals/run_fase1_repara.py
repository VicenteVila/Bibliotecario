"""Hito 3, Fase 1 — Reparación R1 declarada en HITO3_PLAN.md (2026-10-16).

Para cada arnés suspendido en H1 (`r4_ok=false` o `r5_ok=false` con el juez
`gemini-3.1-flash-lite`): una sola vuelta de reparación con evidencia — las
frases concretas que el juez señaló + la fuente — pidiendo corregir **solo**
lo señalado (R6 o cita correcta), sin reescribir el resto. Después se
re-juzga con el mismo instrumento (filas `arm="H1R"`).

Tope: 1 vuelta por arnés. Si algo sigue suspendido, H1 queda definitivamente
NO CUMPLE — no hay segunda tirada (R2).

Uso (con la rotación por defecto del agente, como la generación):

    .venv/bin/python evals/run_fase1_repara.py
    JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... Q1_API_KEY=... \
      .venv/bin/python evals/eval_q1_r4r5.py --arm=H1R --file=evals/results/result_fase1_h1r.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_q1_r4r5 import _source
from run_dimension_d import TECNICAS

from bibliotecario.agent.tools import BLUEPRINT_MAX_TOKENS, generate

ROOT = Path(__file__).resolve().parents[1]
H1 = ROOT / "evals" / "results" / "result_fase1_h1.json"
H1J = ROOT / "evals" / "results" / "result_q1_r4r5.json"
OUT = ROOT / "evals" / "results" / "result_fase1_h1r.json"
ARM = "H1R"

_PROMPT = """Estás reparando un blueprint del sistema Bibliotecario.

Un revisor automático (el mismo que aprueba o suspende este blueprint) señaló
estas frases CONCRETAS como fallos de atribución:

R4 — atribuye a la fuente cosas que la fuente no dice:
{r4}

R5 — rellena detalles que la fuente no especifica:
{r5}

FUENTE (lo ÚNICO que el blueprint puede atribuir al paper; los punteros
[doc:id:chunk] tienen que apuntar a trozos que estén aquí):
{fuente}

BLUEPRINT ACTUAL:
{blueprint}

Corrige SOLO las frases señaladas, una por una: si la fuente lo sostiene,
reescríbela con cita literal + puntero [doc:id:chunk] correcto; si no la
sostiene, quítala o márcala «(propuesta del blueprint)». NO reescribas el
resto del documento: conserva la estructura, la bibliografía, las citas que
ya funcionan y las declaraciones de silencio. No inventes umbrales, métricas
ni componentes nuevos. No añadas nada que no sea corrección de lo señalado.

Devuelve SOLO el blueprint completo corregido, en markdown."""


def _frases(items: list[str]) -> str:
    if not items:
        return "- (ninguna)"
    return "\n".join(f"- «{x}»" for x in items)


def main() -> int:
    gen = {r["technique"]: r for r in json.loads(H1.read_text(encoding="utf-8"))
           if r.get("arm") == "H1" and r.get("ok")}
    juicio = {d["technique"]: d for d in json.loads(H1J.read_text(encoding="utf-8"))
              if d.get("arm") == "H1" and not d.get("error")}
    prev: list[dict] = []
    if OUT.exists():
        prev = json.loads(OUT.read_text(encoding="utf-8"))
    hecho = {r["technique"] for r in prev if r.get("ok")}

    print("=" * 70)
    print("Fase 1 — Reparación R1 (1 vuelta, tope declarado)")
    print("=" * 70)
    fallos = 0
    for tech in TECNICAS:
        j = juicio.get(tech)
        if not j or (j.get("r4_ok") and j.get("r5_ok")):
            print(f"  [R1] {tech} ... aprueba sin reparar, salto")
            continue
        if tech in hecho:
            print(f"  [R1] {tech} ... ya reparada, salto")
            continue
        g = gen.get(tech)
        if not g:
            print(f"  [R1] {tech} ... sin fila H1, no hay que reparar")
            continue
        print(f"  [R1] {tech} ...", end=" ", flush=True)
        t = time.time()
        try:
            fuente = _source(tech)
            prompt = _PROMPT.format(
                r4=_frases(j.get("r4_fabricaciones") or []),
                r5=_frases(j.get("r5_rellenados") or []),
                fuente=fuente[:9000],
                blueprint=(g.get("blueprint") or "")[:9000],
            )
            nuevo = (generate(prompt, max_tokens=BLUEPRINT_MAX_TOKENS) or "").strip()
        except Exception as e:
            fallos += 1
            prev.append({"arm": ARM, "technique": tech, "run": 0, "ok": False,
                         "error": f"{type(e).__name__}: {e}"})
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"ERROR {type(e).__name__}: {e}")
            continue
        ok = bool(nuevo) and not nuevo.startswith("(")
        fila: dict = {"arm": ARM, "technique": tech, "run": 0, "ok": ok,
                      "secs": round(time.time() - t, 1), "blueprint": nuevo,
                      "reparada": True,
                      "r4_fallaba": not j.get("r4_ok"),
                      "r5_fallaba": not j.get("r5_ok"),
                      "dir": g.get("dir")}
        if ok:
            d = Path(g["dir"])
            if d.exists():
                (d / "BLUEPRINT.md").write_text(
                    f"# {tech}\n\nObjetivo: validar mi agente antes de cada release\n\n{nuevo}\n",
                    encoding="utf-8")
                fila["blueprint_md_escrito"] = True
            print(f"ok {fila['secs']}s  (BLUEPRINT.md del arnes actualizado)")
        else:
            fallos += 1
            fila["error"] = "reparacion vacia o de emergencia (sin LLM)"
            print(f"ERROR {fila['error']}")
        prev.append(fila)
        OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")

    print("\n" + "=" * 70)
    ok = [r for r in prev if r.get("arm") == ARM and r.get("ok")]
    print(f"Reparaciones R1 ok: {len(ok)}/{len(TECNICAS) - 1} (TCE no se toca)")
    print("=" * 70)
    if fallos:
        print(f"  {fallos} reparaciones fallidas — re-ejecuta el script "
              f"(no se juzgan las fallidas)")
        return 1
    print("  Siguiente: juez sobre arm=H1R (ver cabecera del fichero)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
