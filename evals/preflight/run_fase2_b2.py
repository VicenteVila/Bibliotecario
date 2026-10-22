"""HITO16 §1.3 — corrida oficial B-2 etapa 2 (umbrales U1-U6).

Fases (coste: ≤10 llamadas gemini-3.1-flash-lite; el resto 0):

  U5  ρ oculta: ruta de ρ bajo evals/ (nunca EG) + grep de ids `B2-*` en el
      workspace y en una copia temporal → 0 hits.
  U6  BUILD y M_B1 con el scorer B-1 v2 sobre la tarea platformer-juego.
  frames: default (Hito 15 o re-captura) · idle (script idle + --dur-ms) ·
      negro (ffmpeg lavfi, control anti-caucho).
  U1  default → JSON estricto del juez.
  U3  default 2.ª corrida → estabilidad (ΔScore_B2 ≤ 0.10, Δcat ≤ 0.15).
  U2  negro → ítems de presencia = 0 y Score_B2 ≤ 0.30.
  U4  orden → Score_B2(default) − Score_B2(idle) ≥ 0.10.

Persiste evals/result_fase2_b2.json. Exit 0 solo si U1-U6 cumplen todos.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import juez_b2

ROOT = HERE.parents[1]
REPO_EGS = "/mnt/c/EG"
OUT_JSON = ROOT / "evals" / "result_fase2_b2.json"
RESULTS = HERE / "results"
FRAMES_H15 = RESULTS / "b2_etapa1" / "cap1" / "frames"
WORKSPACE = Path("/mnt/c/EG/workspace/current")
GODOT = Path("/mnt/c/EG/.tools/godot")
TAREA = "platformer-juego"
# umbrales §2 (ratificados antes de medir)
U2_SCORE_MAX = 0.30
U3_SCORE_DELTA = 0.10
U3_CAT_DELTA = 0.15
U4_ORDEN_MIN = 0.10
LLAMADAS_MAX = 10
PREFIJO_IDS = (b"B2-D-", b"B2-V-", b"B2-A-")
EXTS_TEXTO = (".gd", ".tscn", ".cfg", ".json", ".md", ".txt", ".tres",
              ".import", ".gdshader", ".yaml", ".yml")


def buscar_ids(dir_raiz: Path) -> list[str]:
    """U5: apariciones de ids de ρ en un árbol (workspace o copia)."""
    hits: list[str] = []
    for p in sorted(dir_raiz.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in EXTS_TEXTO:
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        for pre in PREFIJO_IDS:
            n = data.count(pre)
            if n:
                hits.append(f"{p.relative_to(dir_raiz)}: {pre.decode()}×{n}")
    return hits


def gate_u1(e: dict, n_esperado: int) -> tuple[bool, str]:
    """U1: JSON estricto ya parseado — ids completos, scores, justif, ≤2."""
    if e.get("error"):
        return False, f"error: {e['error']}"
    items = e.get("items") or {}
    just = e.get("justificaciones") or {}
    ok_scores = all(v in (0, 0.5, 1) for v in items.values())
    intentos = int(e.get("intentos") or 9)
    ok = (len(items) == n_esperado and len(just) == n_esperado
          and ok_scores and intentos <= 2)
    return ok, (f"{len(items)}/{n_esperado} ítems · "
                f"scores∈{{0,0.5,1}}={ok_scores} · "
                f"justif={len(just)}/{n_esperado} · "
                f"intentos={intentos}/2")


def gate_u2(e: dict, rubrica: dict) -> tuple[bool, str]:
    """U2: control negro — presencia=0 y Score_B2 ≤ umbral."""
    if e.get("error"):
        return False, f"error: {e['error']}"
    items = e.get("items") or {}
    pres = [it["id"] for it in rubrica["items"] if it.get("presencia")]
    malos = [i for i in pres if items.get(i) != 0]
    sb2 = e.get("Score_B2")
    ok = (not malos and sb2 is not None and sb2 <= U2_SCORE_MAX)
    return ok, (f"presencia=0: {len(pres) - len(malos)}/{len(pres)}"
                f"{'' if not malos else f' (≠0: {malos})'} · "
                f"Score_B2_negro={sb2} (≤{U2_SCORE_MAX})")


def gate_u3(res1: dict | None, res2: dict | None) -> tuple[bool, str]:
    if not res1 or not res2 or res1.get("error") or res2.get("error"):
        return False, "falta una de las dos corridas de default"
    d_score = abs(res1["Score_B2"] - res2["Score_B2"])
    d_cats = {c: round(abs(res1[c] - res2[c]), 4)
              for c in ("D", "V", "A")}
    ok = d_score <= U3_SCORE_DELTA and all(
        v <= U3_CAT_DELTA for v in d_cats.values())
    return ok, (f"ΔScore_B2={d_score} (≤{U3_SCORE_DELTA}) · "
                f"Δcategorías={d_cats} (≤{U3_CAT_DELTA} c/u)")


def gate_u4(res_default: dict | None,
            res_idle: dict | None) -> tuple[bool, str]:
    if not res_default or not res_idle or res_default.get("error") \
            or res_idle.get("error"):
        return False, "falta default o idle"
    delta = round(res_default["Score_B2"] - res_idle["Score_B2"], 4)
    return delta >= U4_ORDEN_MIN, (
        f"Score_B2(default)={res_default['Score_B2']} − "
        f"Score_B2(idle)={res_idle['Score_B2']} = {delta} "
        f"(≥{U4_ORDEN_MIN})")


def _json_suite_runner() -> tuple[dict, list]:
    """U6: B-1 v2 sobre la única tarea → {BUILD, M_B1} + fila cruda."""
    cmd = [sys.executable, str(HERE / "suite_runner_v2.py"), TAREA,
           "--workspace", str(WORKSPACE), "--json"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600,
                       check=False)
    out = p.stdout or ""
    lineas = out.splitlines()
    inicio = next((i for i, l in enumerate(lineas) if l == "["), None)
    if inicio is None:
        raise SystemExit(
            f"sin JSON del suite_runner (exit={p.returncode}): "
            f"{(p.stderr or out)[-800:]}")
    filas = json.loads("\n".join(lineas[inicio:]))
    if not filas:
        raise SystemExit("suite_runner sin filas")
    f = filas[0]
    build = 1.0 if f.get("build_ok") else 0.0
    m_b1 = (f["m_pass"] / f["m_total"]) if f.get("m_total") else 0.0
    return {"BUILD": build, "M_B1": round(m_b1, 4)}, filas


def _frames_negro(destino: Path) -> list[Path]:
    """Control anti-caucho: 14 frames negros 1280×720 a 2 fps."""
    destino.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f",
         "lavfi", "-i", "color=c=black:s=1280x720:r=2:d=7", "-frames:v",
         "14", str(destino / "step_%03d.png")],
        capture_output=True, text=True, check=False)
    if p.returncode != 0:
        raise SystemExit(f"ffmpeg negro falló: {(p.stderr or '')[:400]}")
    frames = sorted(destino.glob("step_*.png"))
    if len(frames) < 10:
        raise SystemExit(f"control negro: {len(frames)} frames < 10")
    return frames


def _frames_default(out_dir: Path, display: str) -> list[Path]:
    """Reutiliza el replay del Hito 15; si falta, lo reproduce."""
    if FRAMES_H15.exists():
        frames = sorted(FRAMES_H15.glob("step_*.png"))
        if len(frames) >= 10:
            return frames
    destino = out_dir / "default"
    subprocess.run([sys.executable, str(HERE / "replay_pi.py"), "ambas",
                    "--script", "default", "--out", str(destino),
                    "--display", display], check=False, timeout=600)
    frames = sorted((destino / "frames").glob("step_*.png"))
    if len(frames) < 10:
        raise SystemExit(f"default: {len(frames)} frames < 10")
    return frames


def _frames_idle(out_dir: Path, display: str) -> list[Path]:
    destino = out_dir / "idle"
    if not (destino / "demo_pi.json").exists():
        p = subprocess.run([sys.executable, str(HERE / "replay_pi.py"),
                            "captura", "--script", "idle", "--out",
                            str(destino), "--display", display],
                           capture_output=True, text=True, timeout=600,
                           check=False)
        if p.returncode != 0:
            raise SystemExit(f"captura idle falló: {p.stdout[-600:]}"
                             f"{p.stderr[-400:]}")
    p = subprocess.run([sys.executable, str(HERE / "replay_pi.py"),
                        "replay", "--pi", str(destino / "demo_pi.json"),
                        "--out", str(destino), "--display", display,
                        "--dur-ms", "10000", "--pi-vacia"],
                       capture_output=True, text=True, timeout=600,
                       check=False)
    if p.returncode != 0:
        raise SystemExit(f"replay idle falló: {p.stdout[-600:]}"
                         f"{p.stderr[-400:]}")
    frames = sorted((destino / "frames").glob("step_*.png"))
    if len(frames) < 10:
        raise SystemExit(f"idle: {len(frames)} frames < 10")
    return frames


def _eval(nombre: str, rubrica: dict, frames: list[Path],
          llamadas: list[int], tokens: list[int]) -> dict:
    t0 = time.time()
    r = juez_b2.evaluar(rubrica, frames)
    llamadas.append(int(r.get("intentos") or 1))
    usage = r.get("usage") or {}
    tokens.append(int(usage.get("total_tokens", 0) or 0))
    if r.get("error"):
        return {"caso": nombre, "error": r["error"],
                "intentos": r.get("intentos"),
                "frames": len(frames), "secs": round(time.time() - t0, 1),
                "usage": usage}
    cats = juez_b2.agregar(r, rubrica)
    return {"caso": nombre, "frames": len(frames),
            "secs": round(time.time() - t0, 1),
            "intentos": r.get("intentos"),
            "items": {k: v["score"] for k, v in r["items"].items()},
            "justificaciones": {k: v["justificacion"]
                                for k, v in r["items"].items()},
            "usage": usage, **cats}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(RESULTS / "b2_etapa2"))
    ap.add_argument("--display", choices=["xfvb", "system"],
                    default="xfvb")
    args = ap.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rubrica = juez_b2.cargar_rubrica(TAREA)
    gates: dict[str, dict] = {}
    llamadas: list[int] = []
    tokens: list[int] = []
    registro: dict = {"hito": 16, "tarea": TAREA,
                      "juez": juez_b2.JUDGE_MODEL_B2,
                      "temperatura": juez_b2.TEMPERATURE,
                      "rubrica": str(juez_b2.RUBRICAS / f"{TAREA}.json")}

    # ---- U5: ρ oculta
    ruta = Path(registro["rubrica"]).resolve()
    ruta_ok = str(ruta).startswith(str(ROOT.resolve())) and \
        REPO_EGS not in str(ruta)
    hits_ws = buscar_ids(WORKSPACE)
    with tempfile.TemporaryDirectory(prefix="b2_rub_") as td:
        copia = Path(td) / "ws"
        shutil.copytree(WORKSPACE, copia, dirs_exist_ok=True)
        hits_copia = buscar_ids(copia)
    u5_ok = ruta_ok and not hits_ws and not hits_copia
    gates["U5"] = {"ok": u5_ok,
                   "detalle": f"ρ en {ruta} (fuera de EG: {ruta_ok}) · "
                              f"workspace hits={hits_ws or 0} · copia "
                              f"hits={hits_copia or 0}"}
    print(f"U5 ρ oculta: {'OK' if u5_ok else 'FALLA'} — "
          f"{gates['U5']['detalle']}")

    # ---- U6: BUILD + M_B1 (B-1 v2)
    try:
        b1, filas = _json_suite_runner()
    except SystemExit as e:
        gates["U6"] = {"ok": False, "detalle": f"B-1: {e}"}
        print(gates["U6"]["detalle"])
        _final(registro, gates, llamadas, tokens)
        return 1
    registro.update(b1)
    registro["b1_fila"] = filas[0]
    gates["U6"] = {"ok": True,
                   "detalle": f"B-1: BUILD={b1['BUILD']} "
                              f"M_B1={b1['M_B1']}"}
    print(f"U6 B-1: BUILD={b1['BUILD']} M_B1={b1['M_B1']}")

    # ---- frames
    print("frames: default …", flush=True)
    frames_def = _frames_default(out_dir, args.display)
    print(f"  default {len(frames_def)} · idle …", flush=True)
    frames_idle = _frames_idle(out_dir, args.display)
    print(f"  idle {len(frames_idle)} · negro …", flush=True)
    frames_neg = _frames_negro(out_dir / "negro")
    print(f"  negro {len(frames_neg)}")

    # ---- evaluaciones (4 lógicas, ≤10 llamadas)
    e_def1 = _eval("default", rubrica, frames_def, llamadas, tokens)
    e_def2 = _eval("default2", rubrica, frames_def, llamadas, tokens)
    e_negro = _eval("negro", rubrica, frames_neg, llamadas, tokens)
    e_idle = _eval("idle", rubrica, frames_idle, llamadas, tokens)
    registro["evaluaciones"] = {"default": e_def1, "default2": e_def2,
                                "negro": e_negro, "idle": e_idle}

    # ---- gates
    ok1, d1 = gate_u1(e_def1, len(rubrica["items"]))
    gates["U1"] = {"ok": ok1, "detalle": d1}

    ok2, d2 = gate_u2(e_negro, rubrica)
    gates["U2"] = {"ok": ok2, "detalle": d2}

    ok3, d3 = gate_u3(e_def1, e_def2)
    gates["U3"] = {"ok": ok3, "detalle": d3}

    ok4, d4 = gate_u4(e_def1, e_idle)
    gates["U4"] = {"ok": ok4, "detalle": d4}

    llam = sum(llamadas)
    ok6_coste = llam <= LLAMADAS_MAX
    ok6 = (b1["BUILD"] == 1.0 and ok6_coste)
    gates["U6"] = {
        "ok": ok6,
        "detalle": gates["U6"]["detalle"] +
                   f" · llamadas={llam}/{LLAMADAS_MAX}" + (
                       "" if ok6_coste else " EXCEDIDO") +
                   " · suite+ruff aparte"}

    # ---- score final (dato; exige todos los gates para publicarlo)
    score_final = None
    if not e_def1.get("error"):
        score_final = juez_b2.score_completo(
            b1["BUILD"], b1["M_B1"], e_def1.get("Score_B2", 0.0))
    registro["Score_final"] = score_final
    registro["llamadas"] = llam
    registro["tokens_total"] = sum(tokens)
    registro["gates"] = gates

    return _final(registro, gates, llamadas, tokens)


def _final(registro: dict, gates: dict, llamadas: list[int],
           tokens: list[int]) -> int:
    OUT_JSON.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    todos = all(g.get("ok") for g in gates.values())
    print("\n" + "=" * 66)
    print("HITO16 B-2 etapa 2 — UMBRALES")
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


if __name__ == "__main__":
    raise SystemExit(main())
