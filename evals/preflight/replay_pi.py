"""HITO15 §1.4 — pipeline B-2 etapa 1: captura de demos Π y replay.

Dos fases, ambas con copia temporal del workspace de ReaGame (ReaGame no
se modifica) y ventana 1280×720 bajo Xvfb :99 (fallback declarado al
DISPLAY del sistema, riesgo (a) del plan):

  A · captura  — copia + autoloads (pi_capture/pi_actor) + `_pi_script.json`
                 → godot ventana → `_pi.json` (timestamp por tick, T2).
  B · replay   — copia fresca → xdotool (XTEST) inyecta Π en sus t_ms →
                 ffmpeg x11grab -r 2 → replay.mp4 + frames/step_*.png (T3).

Uso:
    .venv/bin/python evals/preflight/replay_pi.py ambas \\
        --script default --out evals/preflight/results/b2_etapa1
    .venv/bin/python evals/preflight/replay_pi.py replay \\
        --pi evals/preflight/results/b2_etapa1/demo_pi.json --out ...
Opciones: --display xfvb|system · --workspace <ruta>
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pi_schema

GODOT_CANDIDATES = [
    Path("/mnt/c/EG/.tools/godot"),
    Path("/mnt/c/EG/.tools/godot4"),
]
DEFAULT_WORKSPACE = Path("/mnt/c/EG/workspace/current")
PI_SCRIPTS = HERE / "pi_scripts"
DEFAULT_OUT = HERE / "results" / "b2_etapa1"

ANCHO, ALTO = 1280, 720
XVFB_TIMEOUT_S = 5.0
VENTANA_TIMEOUT_S = 40.0
MOTOR_TIMEOUT_S = 180.0   # §2: ≤2 timeouts de 180 s por ejecución
COLA_S = 3.0              # vídeo = duración(Π) + cola
DESPACIO_RESFRESCO = 0.7   # espera a ffmpeg antes de t0


def _godot() -> Path:
    for p in GODOT_CANDIDATES:
        if p.exists():
            return p
    w = shutil.which("godot")
    if w:
        return Path(w)
    raise SystemExit("Godot no encontrado (GODOT_CANDIDATES ni PATH)")


def _xdotool() -> tuple[list[str], dict[str, str]]:
    """(base argv, env) — resuelve el xdotool local de `~/opt` si no hay PATH."""
    env = dict(os.environ)
    cand = shutil.which("xdotool")
    if cand:
        return [cand], env
    local = Path.home() / "opt" / "xdotool" / "usr" / "bin" / "xdotool"
    if local.exists():
        lib = local.parent.parent / "lib" / "x86_64-linux-gnu"
        if lib.is_dir():
            env["LD_LIBRARY_PATH"] = str(lib) + (
                ":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH")
                else "")
        return [str(local), ], env
    raise SystemExit(
        "xdotool no encontrado (PATH ni ~/opt/xdotool). Instálalo con "
        "`sudo apt install xdotool` o extrae los .deb como en HITO15 §0.")


def _tcp_listo(puerto: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect(("127.0.0.1", puerto))
        except OSError:
            return False
    return True


def _arrancar_xvfb() -> tuple[int, str, subprocess.Popen | None]:
    """Devuelve (display_num, display_str, proc|None). proc None = system.

    WSLg monta /tmp/.X11-unix como tmpfs ro → el socket unix es imposible;
    se arranca con `-listen tcp` y se usa `localhost:N` (puerto 6000+N).
    Si el socket unix aparece (entornos normales), se prefiere `:N`.
    """
    for n in (99, 98, 97):
        sock = Path(f"/tmp/.X11-unix/X{n}")
        if sock.exists() or _tcp_listo(6000 + n):
            continue
        break
    else:
        n = 96
    disp = f":{n}"
    proc = subprocess.Popen(
        ["Xvfb", disp, "-screen", "0", f"{ANCHO}x{ALTO}x24", "-ac",
         "-listen", "tcp"], stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < XVFB_TIMEOUT_S:
        if Path(f"/tmp/.X11-unix/X{n}").exists():
            return n, disp, proc
        if _tcp_listo(6000 + n):
            return n, f"localhost:{n}", proc
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    proc.terminate()
    raise SystemExit("Xvfb no arrancó en 5 s")


def _copia_workspace(workspace: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="b2_"))
    for item in workspace.iterdir():
        dst = tmp / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dst)
    return tmp


def _inyectar_autoloads(project: Path) -> None:
    texto = project.read_text(encoding="utf-8")
    if 'PiCapture="' in texto:
        return
    lineas = ('PiCapture="*res://pi_capture.gd"\n'
              'PiActor="*res://pi_actor.gd"\n')
    if "[autoload]" in texto:
        i = texto.index("[autoload]") + len("[autoload]")
        resto = texto[i:]
        fin = resto.find("\n[")
        j = i + (fin + 1 if fin != -1 else len(resto))
        texto = texto[:j] + lineas + texto[j:]
    else:
        texto = texto.rstrip("\n") + "\n\n[autoload]\n" + lineas
    project.write_text(texto, encoding="utf-8")


def _nombre_proyecto(project: Path) -> str:
    m = re.search(r'^name="([^"]+)"', project.read_text(encoding="utf-8"),
                  re.MULTILINE)
    return m.group(1) if m else "Godot"


def _env_display(disp: str) -> dict[str, str]:
    env = dict(os.environ)
    env["DISPLAY"] = disp
    env.setdefault("SDL_VIDEODRIVER", "x11")
    return env


def _leer_nombre(pid: int, nombre: str, argv_x: list[str],
                 env_x: dict[str, str]) -> str | None:
    """Espera la ventana del juego y devuelve su id (o None)."""
    t0 = time.time()
    ultimo = ""
    while time.time() - t0 < VENTANA_TIMEOUT_S:
        for args in (["search", "--onlyvisible", "--pid", str(pid)],
                     ["search", "--onlyvisible", "--name", nombre],
                     ["search", "--onlyvisible", "--class", "godot"]):
            r = subprocess.run(argv_x + args, capture_output=True, text=True,
                               env=env_x, check=False)
            ids = [x for x in r.stdout.split() if x.strip()]
            if ids:
                return ids[-1]
            if r.stderr.strip():
                ultimo = r.stderr.strip()
        if subprocess.run(argv_x + ["--version"], capture_output=True,
                          env=env_x, check=False).returncode != 0:
            raise SystemExit("xdotool dejó de responder: " + ultimo)
        time.sleep(0.5)
    return None


# ---------------------------------------------------------------- fase A


def fase_captura(script: str, workspace: Path, out: Path,
                 display: str) -> dict:
    src = PI_SCRIPTS / f"{script}.json"
    if not src.exists():
        raise SystemExit(f"script Π inexistente: {src}")
    tmp = _copia_workspace(workspace)
    _inyectar_autoloads(tmp / "project.godot")
    shutil.copy2(HERE / "pi_capture.gd", tmp / "pi_capture.gd")
    shutil.copy2(HERE / "pi_actor.gd", tmp / "pi_actor.gd")
    shutil.copy2(src, tmp / "_pi_script.json")

    _disp, disp_str, xvfb = (None, None, None)
    if display == "xfvb":
        _disp, disp_str, xvfb = _arrancar_xvfb()
    else:
        disp_str = os.environ.get("DISPLAY", ":0")
    rep: dict = {"fase": "captura", "script": script, "display": disp_str,
                 "workspace": str(workspace)}
    try:
        env = _env_display(disp_str)
        cmd = [_godot(), "--path", str(tmp), "--resolution",
               f"{ANCHO}x{ALTO}", "--position", "0,0"]
        t0 = time.time()
        proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        try:
            salida, _ = proc.communicate(timeout=MOTOR_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            proc.kill()
            salida, _ = proc.communicate()
            rep["timeout"] = True
        rep["motor_secs"] = round(time.time() - t0, 1)
        rep["motor_exit"] = proc.returncode
        pi_file = tmp / "_pi.json"
        if not pi_file.exists():
            rep["ok"] = False
            rep["error"] = "sin _pi.json (el actor no terminó)"
            rep["salida"] = (salida or "")[-4000:]
            return rep
        doc = json.loads(pi_file.read_text(encoding="utf-8"))
        errs = pi_schema.validar_pi(doc)
        out.mkdir(parents=True, exist_ok=True)
        destino = out / "demo_pi.json"
        destino.write_text(json.dumps(doc, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        rep.update({"ok": not errs, "errores_schema": errs,
                    "eventos": len(doc.get("events") or []),
                    "duracion_ms": pi_schema.duracion_ms(doc),
                    "demo": str(destino)})
        if errs:
            rep["salida"] = (salida or "")[-4000:]
        return rep
    finally:
        if xvfb is not None:
            xvfb.terminate()


# ---------------------------------------------------------------- fase B


def fase_replay(pi_file: Path, workspace: Path, out: Path,
                display: str) -> dict:
    doc = json.loads(pi_file.read_text(encoding="utf-8"))
    errs = pi_schema.validar_pi(doc)
    plan = pi_schema.pi_a_xdotool(doc)
    dur = pi_schema.duracion_ms(doc) / 1000.0
    argv_x, env_x_base = _xdotool()
    rep: dict = {"fase": "replay", "pi": str(pi_file), "eventos": len(plan),
                 "duracion_ms": pi_schema.duracion_ms(doc),
                 "errores_schema": errs}
    if errs:
        rep["ok"] = False
        return rep

    tmp = _copia_workspace(workspace)
    nombre = _nombre_proyecto(tmp / "project.godot")
    disp_str, xvfb = None, None
    if display == "xfvb":
        _, disp_str, xvfb = _arrancar_xvfb()
    else:
        disp_str = os.environ.get("DISPLAY", ":0")
    rep["display"] = disp_str
    env_x = _env_display(disp_str)
    for k, v in env_x_base.items():
        if k in ("LD_LIBRARY_PATH",):
            env_x[k] = v

    out.mkdir(parents=True, exist_ok=True)
    mp4 = out / "replay.mp4"
    frames_dir = out / "frames"
    motor = None
    ffmpeg = None
    try:
        motor = subprocess.Popen([_godot(), "--path", str(tmp),
                                  "--resolution", f"{ANCHO}x{ALTO}",
                                  "--position", "0,0"],
                                 env=_env_display(disp_str),
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        wid = _leer_nombre(motor.pid, nombre, argv_x, env_x)
        if wid is None:
            rep["ok"] = False
            rep["error"] = "ventana del juego no encontrada (40 s)"
            return rep
        rep["wid"] = wid
        geom = subprocess.run(argv_x + ["getwindowgeometry", wid],
                              capture_output=True, text=True, env=env_x,
                              check=False)
        rep["geometria"] = geom.stdout.strip()
        # foco: sin WM (Xvfb) no hay EWMH activate — windowfocus directo
        subprocess.run(argv_x + ["windowraise", wid], capture_output=True,
                       env=env_x, check=False)
        subprocess.run(argv_x + ["windowfocus", "--sync", wid],
                       capture_output=True, env=env_x, check=False)

        n = int(dur * 1000) + int(COLA_S * 1000)
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-f", "x11grab", "-framerate", "2", "-video_size",
             f"{ANCHO}x{ALTO}", "-i", f"{disp_str}.0", "-t",
             f"{n / 1000.0:.3f}", str(mp4)],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE, env=env_x)
        time.sleep(DESPACIO_RESFRESCO)

        t0 = time.monotonic()
        for t_ms, args in plan:
            falta = t0 + t_ms / 1000.0 - time.monotonic()
            if falta > 0:
                time.sleep(falta)
            r = subprocess.run(argv_x + args, capture_output=True,
                               text=True, env=env_x, check=False)
            if r.returncode != 0:
                rep.setdefault("fallo_xdotool", []).append(
                    {"t_ms": t_ms, "args": args,
                     "err": (r.stderr or "").strip()[:200]})
        cola_total = t0 + dur + 1.2 - time.monotonic()
        if cola_total > 0:
            time.sleep(cola_total)
        ffmpeg.wait(timeout=60)
        rep["ffmpeg_exit"] = ffmpeg.returncode

        if frames_dir.exists():
            shutil.rmtree(frames_dir)
        frames_dir.mkdir(parents=True)
        ex = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i",
             str(mp4), str(frames_dir / "step_%03d.png")],
            capture_output=True, text=True, check=False)
        if ex.returncode != 0:
            rep["ok"] = False
            rep["error"] = "extracción de frames fallida"
            rep["stderr"] = (ex.stderr or "")[-2000:]
            return rep

        frames = sorted(frames_dir.glob("step_*.png"))
        negros, luminancias = _clasificar_frames(frames)
        rep.update({"ok": bool(frames) and len(frames) >= 10
                    and not negros,
                    "frames": len(frames),
                    "frames_negros": negros,
                    "luminancia_media": round(
                        sum(luminancias) / len(luminancias), 2)
                    if luminancias else None,
                    "mp4": str(mp4), "frames_dir": str(frames_dir)})
        return rep
    finally:
        if ffmpeg is not None and ffmpeg.poll() is None:
            ffmpeg.kill()
        if motor is not None and motor.poll() is None:
            motor.send_signal(signal.SIGTERM)
            try:
                motor.wait(timeout=10)
            except subprocess.TimeoutExpired:
                motor.kill()
        if xvfb is not None:
            xvfb.terminate()


def _clasificar_frames(frames: list[Path]) -> tuple[int, list[float]]:
    """(n_negros, luminancias_medias) — negro = media ≤2/255."""
    from PIL import Image
    negros = 0
    medias: list[float] = []
    for p in frames:
        with Image.open(p) as im:
            g = im.convert("L")
            h = g.histogram()
            total = sum(h)
            media = sum(i * c for i, c in enumerate(h)) / max(total, 1)
        medias.append(media)
        if media <= 2.0:
            negros += 1
    return negros, medias


# ---------------------------------------------------------------- main


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("fase", choices=["captura", "replay", "ambas"])
    ap.add_argument("--script", default="default")
    ap.add_argument("--pi", default=None, help="Π para fase replay")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--display", choices=["xfvb", "system"],
                    default="xfvb")
    ap.add_argument("--workspace", default=str(DEFAULT_WORKSPACE))
    args = ap.parse_args()

    out = Path(args.out)
    workspace = Path(args.workspace)
    if not (workspace / "project.godot").exists():
        raise SystemExit(f"workspace sin project.godot: {workspace}")
    out.mkdir(parents=True, exist_ok=True)
    informes: list[dict] = []

    if args.fase in ("captura", "ambas"):
        print(f"[B2] captura script={args.script} ...", flush=True)
        r = fase_captura(args.script, workspace, out, args.display)
        informes.append(r)
        print(f"  -> ok={r.get('ok')} eventos={r.get('eventos')} "
              f"dur={r.get('duracion_ms')}ms schema={r.get('errores_schema')}")
        if not r.get("ok"):
            _escribir(out, informes)
            return 1

    if args.fase in ("replay", "ambas"):
        pi_file = Path(args.pi) if args.pi else out / "demo_pi.json"
        if not pi_file.exists():
            raise SystemExit(f"Π inexistente: {pi_file}")
        print(f"[B2] replay {pi_file} ...", flush=True)
        r = fase_replay(pi_file, workspace, out, args.display)
        informes.append(r)
        print(f"  -> ok={r.get('ok')} frames={r.get('frames')} "
              f"negros={r.get('frames_negros')} "
              f"lum={r.get('luminancia_media')} "
              f"fallos_xd={len(r.get('fallo_xdotool') or [])}")

    _escribir(out, informes)
    return 0 if all(i.get("ok") for i in informes) else 1


def _escribir(out: Path, informes: list[dict]) -> None:
    path = out / "report_b2.json"
    previo = []
    if path.exists():
        try:
            previo = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            previo = []
    path.write_text(json.dumps(previo + informes, ensure_ascii=False,
                               indent=2), encoding="utf-8")
    print(f"[B2] informe → {path}")


if __name__ == "__main__":
    sys.exit(main())
