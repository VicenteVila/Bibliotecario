"""Fase 2 — re-puntuar R4 sobre los blueprints YA medidos, con el juez calibrado.

Antes de gastar un solo `generate()`, hay que saber cuánto del 4/15 era modelo
y cuánto era el juez. La calibración (dec. 10) encontró tres falsos positivos
verificados —`λ_t=0.125`, `Rbest`, `lessons.md` están en la fuente— así que el
número antiguo no se puede usar para comparar contra nada.

Este script **no genera nada**: toma las mismas 40 acusaciones que el juez
original sacó del brazo C y las pasa por el pipeline calibrado
(`calibrate_r4.classify`). Si la cifra por blueprint sube, la subida es del
juez, no del modelo, y hay que decirlo así.

R4 por blueprint = 0 acusaciones que sigan siendo FAIL tras calibrar.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from calibrate_r4 import _contexto_blueprints, classify

ROOT = Path(__file__).resolve().parents[1]
Q1 = ROOT / "evals" / "result_q1_r4r5.json"
OUT = ROOT / "evals" / "result_r4_rescore.json"

TECH = {"PEARL": 1, "Procedural Graphs": 2, "Task-CoEvolve": 3,
        "ReASearch": 4, "WikiSkill": 5}


def main() -> int:
    arm = "C"
    out_path = OUT
    for a in sys.argv[1:]:
        if a.startswith("--arm="):
            arm = a.split("=", 1)[1]
        elif a.startswith("--out="):
            # Cada brazo con su fichero: el del A/B no debe pisarse al medir
            # brazos nuevos (R5).
            out_path = Path(a.split("=", 1)[1])
    if not Q1.exists():
        print("no hay result_q1_r4r5.json")
        return 1

    rows = [x for x in json.loads(Q1.read_text(encoding="utf-8"))
            if x["arm"] == arm and not x.get("error")]
    blues = _contexto_blueprints()

    print("=" * 74)
    print(f"Fase 2 — re-puntuo R4 del brazo {arm} con el pipeline calibrado")
    print(f"acusaciones originales: {sum(len(r['r4_fabricaciones']) for r in rows)}")
    print("=" * 74)

    out: list[dict] = []
    for x in rows:
        doc = TECH[x["technique"]]
        antes = len(x["r4_fabricaciones"])
        via: dict[str, int] = {}
        restantes: list[dict] = []
        for claim in x["r4_fabricaciones"]:
            r = classify({"claim": claim, "doc_id": doc}, blues)
            via[r["via"]] = via.get(r["via"], 0) + 1
            if r["decision"] == "FAIL":
                restantes.append({"claim": claim, "via": r["via"]})
        nuevo_ok = not restantes
        out.append({"arm": arm, "technique": x["technique"], "run": x["run"],
                    "r4_ok_antes": x["r4_ok"], "r4_ok_ahora": nuevo_ok,
                    "acusaciones_antes": antes, "acusaciones_ahora": len(restantes),
                    "via": via, "restantes": restantes})
        print(f"  {x['technique']:22s} r{x['run']}  "
              f"{'OK ' if x['r4_ok'] else 'MAL'}->{'OK' if nuevo_ok else 'MAL'}  "
              f"{antes}->{len(restantes)} acusaciones   {via}")

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    antes_ok = sum(1 for r in out if r["r4_ok_antes"])
    ahora_ok = sum(1 for r in out if r["r4_ok_ahora"])
    print("\n" + "=" * 74)
    print(f"R4 brazo {arm}:  antes {antes_ok}/{len(out)}   ahora {ahora_ok}/{len(out)}")
    print("umbral: >= 8/15")
    cambió = [r for r in out if r["r4_ok_antes"] != r["r4_ok_ahora"]]
    if cambió:
        print("\nBlueprints que cambian de veredicto:")
        for r in cambió:
            print(f"  {r['technique']} r{r['run']}: "
                  f"{'MAL -> OK' if r['r4_ok_ahora'] else 'OK -> MAL'}")
    else:
        print("\nNingun blueprint cambia de veredicto: la mejora no era del juez.")
    print("=" * 74)
    print("\nLECTURA HONESTA: este numero NO es una mejora del modelo. Es la")
    print("misma generacion con un juez mejor. Sirve como linea base para el")
    print("brazo E, no como cierre de R4.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
