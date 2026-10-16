"""Hito 3, Fase 3 — H3: los PFs disparan de verdad con estado real del loop.

Declaración previa en `evals/HITO3_PLAN.md` (§ Fase 3, escrita ANTES de
medir): 10 runs reales de `loop.run(question, isolated=True)` sobre
`golden_qa.jsonl` (questions 1-10). Sin juez: H3 no mide calidad.

- **criterio:** al menos un PF built-in se ejecuta en la ruta productiva,
  con estado que llegue del loop real.
- **umbral intacto:** ≥ 1 PF fire por cada 10 runs medidas; y **0** runs
  donde el estado de entrada sea idéntico al de alguna de las 10 anteriores
  (fingerprint del `pf_states` completo de la run).
- **coste:** ~10 runs × ~4 turnos = ~40 llamadas al LLM en rotación free
  tier. No hay forma barata de medirlo: el estado real solo existe corriendo
  el bucle real.

El estado de los PFs salió fabricado hasta la Fase 3 (`loop.py`): `status`
siempre "ok" y `task.type` siempre "research", así que RetryPF, FallbackPF y
ValidateBeforeActPF no podían casar nunca (hallazgo 4: meta-evolución nunca
dispara). La reparación (misma fase) hace que el estado salga del
recorrido; aquí se mide el efecto.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evals" / "result_fase3_h3.json"
GOLDEN = ROOT / "evals" / "golden_qa.jsonl"
ARM = "H3"


def _fingerprints(states_list: list[list[dict]]) -> list[str]:
    out = []
    for states in states_list:
        blob = json.dumps(states, ensure_ascii=False, sort_keys=True)
        out.append(hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="runs (declarado: 10)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--max-turns", type=int, default=4,
                    help="techo de turnos por run (declarado: 4, como P1')")
    args = ap.parse_args()

    from bibliotecario.agent import loop as LOOP
    from bibliotecario.harness import runtime as RT

    preguntas = [json.loads(l) for l in GOLDEN.read_text(encoding="utf-8").splitlines() if l.strip()]
    preguntas = preguntas[: args.n]

    print("=" * 74)
    print(f"H3 — PFs con estado real (n={len(preguntas)} runs, max_turns={args.max_turns})")
    print("=" * 74)

    filas: list[dict] = []
    for i, g in enumerate(preguntas):
        RT.reset_harness()
        import bibliotecario.harness.pfs as PFS
        PFS._registry = None  # registry limpio por run: los contadores no se mezclan

        t = time.time()
        r = LOOP.run(g["question"], max_turns=args.max_turns, isolated=True)
        fila = {"arm": ARM, "run": i, "id": g["id"], "ok": True,
                "secs": round(time.time() - t, 1), "turns": r["turns"],
                "pf_fires": r.get("pf_fires") or [],
                "pf_n": len(r.get("pf_fires") or []),
                "pf_states": r.get("pf_states") or []}
        filas.append(fila)
        nombres = [f["pf"] for f in fila["pf_fires"]]
        print(f"  [{i}] {g['id']:16} turns={r['turns']:2}  fires={fila['pf_n']}  "
              f"{nombres if nombres else ''}")

    fps = _fingerprints([f.get("pf_states") or [] for f in filas])
    # 0 runs cuyo estado sea idéntico al de alguna de las ANTERIORES 10
    # (con n=10: ninguna repetición dentro de la serie).
    vistos: dict[str, int] = {}
    repetidas = 0
    for i, fp in enumerate(fps):
        if fp in vistos:
            repetidas += 1
            print(f"  [!] run {i} con estado idéntico al run {vistos[fp]}")
        else:
            vistos[fp] = i
        filas[i]["estado_fp"] = fp

    total_fires = sum(f["pf_n"] for f in filas)
    runs_con_fire = sum(1 for f in filas if f["pf_n"] > 0)
    print("-" * 74)
    print(f"  PF fires totales        : {total_fires} en {len(filas)} runs")
    print(f"  runs con >=1 fire       : {runs_con_fire}/{len(filas)}")
    print(f"  estados repetidos       : {repetidas} (umbral: 0)")

    cumple_fires = total_fires >= 1
    cumple_estado = repetidas == 0
    cerrada = cumple_fires and cumple_estado
    print("-" * 74)
    print(f"  >=1 fire / 10 runs      : {'CUMPLE' if cumple_fires else 'NO CUMPLE'}")
    print(f"  0 estados repetidos     : {'CUMPLE' if cumple_estado else 'NO CUMPLE'}")
    print(f"  H3: {'CUMPLE' if cerrada else 'NO CUMPLE'}")

    Path(args.out).write_text(
        json.dumps({"criterio": "H3 (HITO3_PLAN §5)", "umbral": ">=1 fire/10 runs y 0 estados repetidos",
                    "n": len(filas), "fires": total_fires, "runs_con_fire": runs_con_fire,
                    "estados_repetidos": repetidas, "h3": cerrada, "filas": filas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\n  -> {args.out}")
    return 0 if cerrada else 1


if __name__ == "__main__":
    raise SystemExit(main())
