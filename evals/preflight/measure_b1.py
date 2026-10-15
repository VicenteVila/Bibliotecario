#!/usr/bin/env python3
"""
Primera medición pequeña B-1 v2 — protocolo declarado en
BENCHMARK_SPEC.md §5.2.2.d (2026-10-15). One-off.

Uso:
  measure_b1.py --task <id>       # una tarea: 1 generación + hasta 2 reparaciones
  measure_b1.py --aggregate       # resumen de measure_b1_results.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

os.environ["LLM_PROVIDERS"] = "groq"
os.environ.setdefault("GROQ_MODEL", "openai/gpt-oss-120b")

ROOT = Path("/mnt/c/Bibliotecario")
WS_BASE = Path("/tmp/opencode/measure_ws")
RESULTS = Path("/tmp/opencode/measure_b1_results.jsonl")
RUNNER = ROOT / "evals/preflight/suite_runner_v2.py"
MAX_TOKENS = 7000  # serie 2b: request ≈ 800+7000 < TPM 8000
MAX_REPAIRS = 2

CRIB = """\
CRIB DE SINTAXIS GODOT 4 (respétalo al pie de la letra):
GDScript:
- Sin backticks. @onready / @export (nunca los keywords de Godot 3).
- Alineación: constantes globales HORIZONTAL_ALIGNMENT_CENTER /
  VERTICAL_ALIGNMENT_CENTER (NO HorizontalAlignment.CENTER ni .ALIGN_CENTER).
- Señales: nodo.senal.connect(_metodo). Sin yield: usa await.
- UI: position (no rect_position); Label.text; autowrap_mode (no el bool autowrap).
- Sin funciones nombradas anidadas: inlinea el await o usa var f = func():
- Cada Area2D necesita un CollisionShape2D para recibir input.
.tscn (formato Godot 4, NO el de Godot 3):
- [ext_resource] SIEMPRE antes del primer [node].
- Recursos embebidos en bloque propio [sub_resource type="X" id="N"] con sus
  propiedades en líneas siguientes — NUNCA inline "X { ... }".
- RectangleShape2D usa size=(no extents=). shape=ExtResource(...)/SubResource(...).
- Control usa anchors/offset_* (NO margin_*, NO size= en Button).
- Camera2D sin current=. project.godot: viewport_width/viewport_height.
"""

FORMATO = """\
Devuelve el juego COMPLETO en el formato exacto:
###FILE: project.godot###
<contenido>
###FILE: main.tscn###
<contenido>
###FILE: main.gd###
<contenido>
Sin explicaciones fuera de los bloques. El juego debe PARSEAR con
godot --headless --check-only sin ningún SCRIPT ERROR.
"""

PROMPT_BASE = (
    "Eres un generador de juegos Godot 4. Genera el juego completo descrito.\n\n"
    + CRIB + "\n" + FORMATO + "\nINSTRUCCIÓN DE LA TAREA:\n"
)


def cargar_texto_tarea(task_id: str) -> str:
    import yaml

    data = yaml.safe_load((ROOT / "evals/game_tasks_expanded.yaml").read_text(encoding="utf-8"))
    return next(t["task"] for t in data["suite"] if t["id"] == task_id)


def extraer_ficheros(respuesta: str) -> dict[str, str]:
    pat = re.compile(r"###FILE:\s*([^\s#]+?)\s*###\s*\n(.*?)(?=\n###FILE:|\Z)", re.S)
    return {m.group(1).lstrip("/"): m.group(2).strip() + "\n" for m in pat.finditer(respuesta)}


def escribir_workspace(ws: Path, ficheros: dict[str, str]) -> None:
    if ws.exists():
        import shutil

        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    for rel, contenido in ficheros.items():
        destino = ws / rel
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")


def leer_workspace(ws: Path) -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in ws.iterdir() if p.is_file()}


def correr_suite(task_id: str, ws: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(RUNNER), task_id, "--workspace", str(ws)],
        capture_output=True, text=True, timeout=300, cwd=str(ROOT),
    )
    salida = proc.stdout + ("\n" + proc.stderr if proc.stderr else "")
    m = re.search(r"M = (\d+)/(\d+)", salida)
    score = re.search(r"Score=\s*([\d.]+)", salida)
    return {
        "m": f"{m.group(1)}/{m.group(2)}" if m else "?",
        "score": float(score.group(1)) if score else 0.0,
        "fails": re.findall(r"\[FAIL\] (\S+)", salida),
        "fallan": (re.search(r"fallan: (.+)", salida).group(1).strip()
                   if re.search(r"fallan: (.+)", salida) else ""),
        "script_errors": [ln.strip()[:160] for ln in salida.splitlines() if "SCRIPT ERROR" in ln][:3],
        "build_ok": "BUILD=ok" in salida or "BUILD = ok" in salida,
    }


def llamar(generate, prompt: str) -> str:
    """Serie 2b: cooldown 70 s tras CADA llamada (ventana TPM deslizante);
    413/respuesta vacía → 1 reintento tras el cooldown."""
    for intento in (1, 2):
        respuesta = generate(prompt, max_tokens=MAX_TOKENS)
        time.sleep(70)  # cooldown declarado tras toda llamada
        if respuesta and respuesta.strip():
            return respuesta
        if intento == 1:
            print("   respuesta vacía o 413 — reintento tras cooldown de 70 s")
    return ""


def medir_tarea(task_id: str) -> None:
    sys.path.insert(0, str(ROOT))
    from bibliotecario.core.llm import generate, usage_totals

    texto = cargar_texto_tarea(task_id)
    ws = WS_BASE / task_id
    ws.mkdir(parents=True, exist_ok=True)
    registros = []

    for intento in range(1, MAX_REPAIRS + 2):  # 1 gen + máx 2 reparaciones
        print(f"\n=== {task_id} · llamada {intento} ===")
        if intento == 1:
            prompt = PROMPT_BASE + texto
        else:
            actual = leer_workspace(ws)
            bloque = "".join(f"###FILE: {n}###\n{c}\n" for n, c in sorted(actual.items()))
            evidencia = registros[-1]["suite"]
            ev_lineas = []
            if evidencia.get("fallan"):
                ev_lineas.append("checks fallando: " + evidencia["fallan"])
            ev_lineas.extend(evidencia.get("script_errors") or evidencia.get("fails") or ["sin datos"])
            ev_lineas = ev_lineas[:4]
            prompt = (
                PROMPT_BASE + texto +
                "\nPROYECTO ACTUAL (falla la suite, corrígelo COMPLETO):\n" + bloque +
                "\nEVIDENCIA DEL MOTOR:\n" + "\n".join(ev_lineas) +
                "\nReescribe los tres ficheros corregidos completos en ###FILE###.\n"
            )
        t0 = time.time()
        respuesta = llamar(generate, prompt)
        dt = time.time() - t0
        ficheros = extraer_ficheros(respuesta) if respuesta else {}
        reg = {"task": task_id, "intento": intento, "llm_s": round(dt, 1),
               "ficheros": sorted(ficheros), "respuesta_vacia": not bool(ficheros)}
        print(f"   {dt:.0f}s · ficheros: {sorted(ficheros)}")
        if not ficheros:
            reg["suite"] = {"score": 0.0, "m": "?", "fails": ["_sin_ficheros"],
                            "script_errors": [], "build_ok": False}
            registros.append(reg)
            RESULTS.open("a", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False) + "\n")
            break
        escribir_workspace(ws, ficheros)
        suite = correr_suite(task_id, ws)
        reg["suite"] = suite
        registros.append(reg)
        RESULTS.open("a", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False) + "\n")
        print(f"   M={suite['m']} Score={suite['score']} fallan={suite['fallan'] or '-'}")
        if suite["build_ok"] and not suite["fallan"] and not suite["fails"]:
            print("   PASSED")
            break

    reg_u = {"task": task_id, "usage": usage_totals()}
    RESULTS.open("a", encoding="utf-8").write(json.dumps(reg_u, ensure_ascii=False) + "\n")
    print("usage:", usage_totals())


def agregar() -> None:
    por_tarea: dict[str, list[float]] = {}
    limpios: dict[str, int] = {}
    reparaciones: dict[str, int] = {}
    tokens = {"calls": 0, "total_tokens": 0}
    for linea in RESULTS.read_text(encoding="utf-8").splitlines():
        r = json.loads(linea)
        if "usage" in r:
            tokens["calls"] += r["usage"].get("calls", 0)
            tokens["total_tokens"] += r["usage"].get("total_tokens", 0)
            continue
        tid = r["task"]
        por_tarea.setdefault(tid, []).append(r["suite"]["score"])
        if r["intento"] == 1:
            limpios[tid] = 0 if r["suite"]["fails"] else 1
        if r["intento"] > 1:
            reparaciones[tid] = reparaciones.get(tid, 0) + 1
    print("\n=== BASELINE B-1 v2 (primera medición pequeña) ===")
    print(f"{'tarea':<32} {'scores':<22} {'media':>7} {'máx':>7}")
    medias = []
    for tid, scores in sorted(por_tarea.items()):
        media = sum(scores) / len(scores)
        medias.append(media)
        print(f"{tid:<32} {str(scores):<22} {media:>7.2f} {max(scores):>7.2f}")
    if medias:
        print(f"\nGLOBAL (media de medias): {sum(medias)/len(medias):.2f}  "
              f"tareas={len(medias)}  sintaxis limpia 1er intento: "
              f"{sum(limpios.values())}/{len(limpios)}  reparaciones usadas: {sum(reparaciones.values())}")
    print(f"tokens LLM: {tokens}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task")
    ap.add_argument("--aggregate", action="store_true")
    ap.add_argument("--out", default="/tmp/opencode/measure_b1_results.jsonl")
    args = ap.parse_args()
    global RESULTS
    RESULTS = Path(args.out)
    if args.aggregate:
        agregar()
        return 0
    if not args.task:
        ap.error("falta --task o --aggregate")
    medir_tarea(args.task)
    return 0


if __name__ == "__main__":
    sys.exit(main())
