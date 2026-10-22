"""5c — calibración del juez contra defectos **conocidos** de un blueprint real.

Por qué: el juez es la herramienta con la que se van a puntuar los blueprints
del Hito 2. Si no coge un error que ya sabemos que existe y que está documentado
(H1-H5), la métrica miente: da notas altas a documentos malos y el A/B de P2/P1'
no puede distinguir nada.

Los dos casos son los defectos reales de `data/agents/task-coevolve/BLUEPRINT.md`,
verificados a mano en el Hito 1:

- **H1 módulos inventados**: el blueprint nombra «History Profiler» y
  «Adaptive Harness Execution Engine». Ninguno existe en el paper: los
  procedimientos sembrados desde la fuente son cuatro — Hájek full-set
  estimation, S-max final selection, anchored difference estimation,
  variance-weighted task selection.
- **H4 promesa contradicha**: el blueprint promete «manteniendo garantías
  estadísticas de precisión». El informe descartó el ciclo con datos: gana solo
  en el mejor de los casos a rho=0.5, persigue un cambio de 0.043 que ya está
  por debajo del ruido medido (0.05). Decisión: no se gasta.

La referencia de cada pregunta es **lo que la fuente dice**, no la opinión. Si
el juez no castiga al blueprint contra eso, no sirve para medir.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from judge import judge

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "data" / "agents" / "task-coevolve" / "BLUEPRINT.md"

# Lo que el paper sostiene, de donde se sembró el grafo (procedural_graph).
REF_PAPER = (
    "El paper Task-CoEvolve propone reducir el suite de validación mediante selección "
    "adaptativa de tareas. Los mecanismos descritos son exactamente cuatro: "
    "variance-weighted task selection, anchored difference estimation, "
    "Hájek full-set estimation y S-max final selection. "
    "El paper NO describe ningún módulo llamado 'History Profiler' ni ningún "
    "'Adaptive Harness Execution Engine': esos nombres no aparecen en la fuente."
)

REF_REPORT = (
    "El informe de evaluación (REPORT_COEVOLVE.md) descarta el ciclo en vivo con datos: "
    "el estimador es correcto e insesgado, pero contra el baseline de no hacer nada solo "
    "gana en el mejor de los casos y a rho=0.5, persiguiendo un cambio de 0.043 que ya "
    "está por debajo del ruido medido (0.05). Sería pagar 1.45 M de tokens para medir ruido. "
    "Decisión: no se gasta. No se afirma en ningún sitio que se mantengan "
    "garantías estadísticas de precisión en producción."
)


def _section(text: str, start: str, end: str | None = None) -> str:
    i = text.find(start)
    if i < 0:
        return text[:1200]
    j = text.find(end, i) if end else -1
    return text[i:j if j > 0 else i + 1500]


def main() -> int:
    if not BLUEPRINT.exists():
        print("no hay blueprint; nothing to calibrate")
        return 0
    bp = BLUEPRINT.read_text(encoding="utf-8")

    # El fragmento con los módulos, tal cual el blueprint los lista.
    modules = _section(bp, "Arquitectura de Módulos", "## 2")
    claim = _section(bp, "Blueprint de Implementación", "---")

    cases = [
        ("Q1 módulos inventados (H1)",
         ("¿El blueprint se limita a los módulos y mecanismos que existen en el paper, "
          "o nombra componentes que la fuente no describe? Mira especialmente los "
          "nombres de los módulos del diagrama."),
         REF_PAPER, modules),
        ("Q4 promesa contradicha (H4)",
         ("¿El blueprint afirma mantener garantías estadísticas de precisión? Comprueba "
          "si esa promesa se sostiene con la evidencia de evaluación disponible."),
         REF_REPORT, claim),
    ]

    print("=" * 70)
    print("5c — calibración del juez contra defectos conocidos")
    print(f"juez: {__import__('judge').JUDGE_MODEL} @ {__import__('judge').JUDGE_PROVIDER}")
    print("=" * 70)

    results = []
    for name, question, reference, answer in cases:
        r = judge(question, reference, answer)
        results.append((name, r))
        print(f"\n--- {name}")
        if r.get("error"):
            print(f"    ERROR: {r['error']}")
            continue
        print(f"    score={r['score']}  {r['verdict']}")

    print("\n" + "=" * 70)
    print("Criterio: el juez debe castigar (score <= 3) los dos defectos conocidos.")
    print("=" * 70)
    ok = 0
    for name, r in results:
        s = r.get("score")
        caught = s is not None and s <= 3
        ok += caught
        print(f"  [{'COGE' if caught else 'PASA'}] {name}  score={s}")

    print(f"\n{ok}/{len(results)} defectos cogidos por el juez.")
    (ROOT / "evals" / "results" / "result_judge_calib.json").write_text(
        json.dumps([{"case": n, **r} for n, r in results], ensure_ascii=False, indent=2),
        encoding="utf-8")
    print("guardado en evals/results/result_judge_calib.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
