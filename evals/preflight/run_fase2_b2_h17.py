"""HITO17 §1.B — corrida oficial B-2 etapa 2 con la enmienda Opción B.

Gates U1-U7 ratificados en `evals/HITO17_PLAN.md` §2 (2026-10-22, ANTES
de implementar y de medir). Diferencias respecto a `run_fase2_b2.py` (H16):

- **Prefiltro no-LLM (Opción B)**: un caso cuyos frames son TODOS de
  color plano no llama al juez (0 llamadas) y sale con todos los ítems
  en 0 — U2 pasa **por construcción**. Informe por caso en `prefiltro`.
- **Gate U7**: trampa sintética — imagen con sprites pintados vs el mismo
  fondo plano sin sprites. El juez CRUDO (sin prefiltro, PROMPT_B2
  congelado, temp 0) debe puntuar `Score_B2(con) ≥ 0.5` y
  `Score_B2(vacío) = 0.0`; un juez caucho falla la segunda.
- **Salida**: `evals/results/result_fase2_b2_h17.json` (la de H16
  `result_fase2_b2.json` es evidencia intocable y no se pisa).

Umbrales U1-U6 idénticos a H16 (reusados de `run_fase2_b2`). Coste:
≤10 llamadas: default(≤2)+default2(≤2)+idle(≤2)+negro(0)+U7 con(≤2)+
U7 vacío(≤2) = 10 en el peor caso.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import juez_b2
import prefiltro_b2
import run_fase2_b2 as base

OUT_JSON = base.ROOT / "evals" / "results" / "result_fase2_b2_h17.json"
GATES_H17 = (*base.GATES_ESPERADOS, "U7")
U7_CON_MIN = 0.5
U7_VACIO_MAX = 0.0


def gate_u7(e_con: dict, e_vacio: dict) -> tuple[bool, str]:
    """U7: trampa sintética — el juez crudo ve con ≥0.5 y vacío = 0.0."""
    if e_con.get("error") or e_vacio.get("error"):
        return False, (f"trampa con error: con={e_con.get('error')} · "
                       f"vacio={e_vacio.get('error')}")
    c = e_con.get("Score_B2")
    v = e_vacio.get("Score_B2")
    ok = (c is not None and v is not None
          and c >= U7_CON_MIN and v <= U7_VACIO_MAX)
    return ok, (f"Score_B2(con)={c} (≥{U7_CON_MIN}) · "
                f"Score_B2(vacio)={v} (≤{U7_VACIO_MAX})")


def frames_trampa(destino: Path) -> tuple[Path, Path]:
    """Trampa U7 determinista (sin RNG): fondo plano + sprites vs fondo solo."""
    destino.mkdir(parents=True, exist_ok=True)
    fondo = (32, 32, 64)
    con = destino / "trampa_con.png"
    sin = destino / "trampa_vacio.png"
    for p, sprites in ((sin, False), (con, True)):
        im = Image.new("RGB", (1280, 720), fondo)
        if sprites:
            d = ImageDraw.Draw(im)
            d.rectangle([160, 620, 1120, 720], fill=(90, 70, 50))
            d.rectangle([160, 560, 1120, 620], fill=(140, 140, 150))
            d.rectangle([560, 430, 640, 560], fill=(70, 130, 240))
            d.ellipse([860, 380, 924, 444], fill=(250, 208, 44))
        im.save(p)
    return con, sin


def _armar(nombre: str, r: dict, rubrica: dict, frames: list[Path],
           secs: float) -> dict:
    cats = juez_b2.agregar(r, rubrica)
    return {"caso": nombre, "frames": len(frames), "secs": secs,
            "intentos": r.get("intentos"),
            "items": {k: v["score"] for k, v in r["items"].items()},
            "justificaciones": {k: v["justificacion"]
                                for k, v in r["items"].items()},
            "usage": r.get("usage") or {}, **cats}


def _eval(nombre: str, rubrica: dict, frames: list[Path],
          llamadas: list[int], tokens: list[int],
          *, prefiltrar: bool = True) -> dict:
    """Como base._eval, pero con el prefiltro Opción B (y U7 sin él)."""
    t0 = time.time()
    if prefiltrar:
        pf = prefiltro_b2.analizar(frames)
        if pf["sin_contenido"]:
            r = prefiltro_b2.anular(rubrica, pf["motivo"])
            llamadas.append(0)
            tokens.append(0)
            caso = _armar(nombre, r, rubrica, frames,
                          round(time.time() - t0, 1))
            caso["prefiltro"] = pf
            return caso
    else:
        pf = {"aplicado": False, "sin_contenido": False}
    r = juez_b2.evaluar(rubrica, frames)
    llamadas.append(int(r.get("intentos") or 1))
    usage = r.get("usage") or {}
    tokens.append(int(usage.get("total_tokens", 0) or 0))
    secs = round(time.time() - t0, 1)
    if r.get("error"):
        caso = {"caso": nombre, "error": r["error"],
                "intentos": r.get("intentos"),
                "frames": len(frames), "secs": secs, "usage": usage}
    else:
        caso = _armar(nombre, r, rubrica, frames, secs)
    caso["prefiltro"] = pf
    return caso


def _gate_u5(rubrica_path: str) -> tuple[bool, str]:
    """U5: ρ solo bajo evals/ (nunca EG) y sin apariciones en el workspace."""
    ruta = Path(rubrica_path).resolve()
    ruta_ok = str(ruta).startswith(str(base.ROOT.resolve())) and \
        base.REPO_EGS not in str(ruta)
    hits_ws = base.buscar_ids(base.WORKSPACE)
    with tempfile.TemporaryDirectory(prefix="b2_rub_") as td:
        copia = Path(td) / "ws"
        shutil.copytree(base.WORKSPACE, copia, dirs_exist_ok=True)
        hits_copia = base.buscar_ids(copia)
    u5_ok = ruta_ok and not hits_ws and not hits_copia
    return u5_ok, (f"ρ en {ruta} (fuera de EG: {ruta_ok}) · "
                   f"workspace hits={hits_ws or 0} · copia "
                   f"hits={hits_copia or 0}")


def _final(registro: dict, gates: dict, llamadas: list[int],
           tokens: list[int]) -> int:
    OUT_JSON.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    todos = base.gates_todos_ok(gates, GATES_H17)
    print("\n" + "=" * 66)
    print("HITO17 B-2 etapa 2 (Opcion B) — UMBRALES")
    print("=" * 66)
    for k in sorted(gates):
        g = gates[k]
        print(f"  {k}  {'OK    ' if g['ok'] else 'FALLA '} {g['detalle']}")
    print(f"  llamadas={sum(llamadas)} · tokens={sum(tokens)} · "
          f"Score_final={registro.get('Score_final')}")
    print(f"  → {'CUMPLE' if todos else 'NO CUMPLE'} · "
          f"{OUT_JSON}")
    print("=" * 66)
    return 0 if todos else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(base.RESULTS / "b2_etapa2"))
    ap.add_argument("--display", choices=["xfvb", "system"],
                    default="xfvb")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rubrica = juez_b2.cargar_rubrica(base.TAREA)
    rub_t = juez_b2.cargar_rubrica("grounding-trampa")
    gates: dict[str, dict] = {}
    llamadas: list[int] = []
    tokens: list[int] = []
    registro: dict = {"hito": 17, "tarea": base.TAREA,
                      "enmienda": "B — prefiltro no-LLM (HITO17_PLAN.md §1.B)",
                      "juez": juez_b2.JUDGE_MODEL_B2,
                      "temperatura": juez_b2.TEMPERATURE,
                      "rubrica": str(juez_b2.RUBRICAS / f"{base.TAREA}.json")}

    # ---- U5: ρ oculta
    u5_ok, d5 = _gate_u5(registro["rubrica"])
    gates["U5"] = {"ok": u5_ok, "detalle": d5}
    print(f"U5 ρ oculta: {'OK' if u5_ok else 'FALLA'} — {d5}")

    # ---- U6: BUILD + M_B1 (B-1 v2)
    try:
        b1, filas = base._json_suite_runner()
    except SystemExit as e:
        gates["U6"] = {"ok": False, "detalle": f"B-1: {e}"}
        print(gates["U6"]["detalle"])
        return _final(registro, gates, llamadas, tokens)
    registro.update(b1)
    registro["b1_fila"] = filas[0]
    gates["U6"] = {"ok": True,
                   "detalle": f"B-1: BUILD={b1['BUILD']} "
                              f"M_B1={b1['M_B1']}"}
    print(f"U6 B-1: BUILD={b1['BUILD']} M_B1={b1['M_B1']}")

    # ---- frames (reusa los del H15/H16 cuando existen)
    print("frames: default …", flush=True)
    frames_def = base._frames_default(out_dir, args.display)
    print(f"  default {len(frames_def)} · idle …", flush=True)
    frames_idle = base._frames_idle(out_dir, args.display)
    print(f"  idle {len(frames_idle)} · negro …", flush=True)
    frames_neg = base._frames_negro(out_dir / "negro")
    print(f"  negro {len(frames_neg)} · trampa U7 …", flush=True)
    tr_con, tr_sin = frames_trampa(out_dir / "sintetico")
    print("  trampa: con (sprites) + vacio (fondo plano)")

    # ---- evaluaciones (prefiltro en los casos de tarea; U7 crudo)
    e_def1 = _eval("default", rubrica, frames_def, llamadas, tokens)
    e_def2 = _eval("default2", rubrica, frames_def, llamadas, tokens)
    e_negro = _eval("negro", rubrica, frames_neg, llamadas, tokens)
    e_idle = _eval("idle", rubrica, frames_idle, llamadas, tokens)
    e_con = _eval("trampa_con", rub_t, [tr_con], llamadas, tokens,
                  prefiltrar=False)
    e_vacio = _eval("trampa_vacio", rub_t, [tr_sin], llamadas, tokens,
                    prefiltrar=False)
    registro["evaluaciones"] = {
        "default": e_def1, "default2": e_def2, "negro": e_negro,
        "idle": e_idle, "trampa_con": e_con, "trampa_vacio": e_vacio}

    # ---- gates
    ok1, d1 = base.gate_u1(e_def1, len(rubrica["items"]))
    gates["U1"] = {"ok": ok1, "detalle": d1}

    ok2, d2 = base.gate_u2(e_negro, rubrica)
    if e_negro.get("prefiltro", {}).get("sin_contenido"):
        d2 += " · prefiltro activo (anulacion por construccion)"
    gates["U2"] = {"ok": ok2, "detalle": d2}

    ok3, d3 = base.gate_u3(e_def1, e_def2)
    gates["U3"] = {"ok": ok3, "detalle": d3}

    ok4, d4 = base.gate_u4(e_def1, e_idle)
    gates["U4"] = {"ok": ok4, "detalle": d4}

    ok7, d7 = gate_u7(e_con, e_vacio)
    gates["U7"] = {"ok": ok7, "detalle": d7}

    llam = sum(llamadas)
    ok6_coste = llam <= base.LLAMADAS_MAX
    ok6 = (b1["BUILD"] == 1.0 and ok6_coste)
    gates["U6"] = {
        "ok": ok6,
        "detalle": gates["U6"]["detalle"] +
                   f" · llamadas={llam}/{base.LLAMADAS_MAX}" + (
                       "" if ok6_coste else " EXCEDIDO") +
                   " · suite+ruff aparte"}

    # ---- score final (D2: exige TODOS los gates U1-U7)
    registro["Score_final"] = base.calcular_score_final(
        gates, b1, e_def1, GATES_H17)
    registro["llamadas"] = llam
    registro["tokens_total"] = sum(tokens)
    registro["gates"] = gates

    return _final(registro, gates, llamadas, tokens)


if __name__ == "__main__":
    raise SystemExit(main())
