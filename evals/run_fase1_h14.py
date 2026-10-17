"""Hito 7 — cierre de H1, intento 4: «reparación solo por edición» (brazo `H14`).

Declaración previa en `evals/HITO7_PLAN.md` (2026-10-17, escrita ANTES de
este archivo y ANTES de medir; umbrales H5'/G1/G2/C1' a ratificar por el
dueño antes de la corrida oficial).

Qué hace, por cada uno de los 5 arneses:

1. **Ronda 0 — guardado + juicio fresco de la base §1**: el mejor estado
   juzgado y aprobado conocido (los textos de `H13` que aprueban) o, si no,
   `H1R`/`H1` — nunca un artefacto suspendido de H13. Instrumento intacto:
   `gemini-3.1-flash-lite` @ Google, temp 0, prompt de `eval_q1_r4r5`.
2. **M4** en ronda 0: si el `BLUEPRINT.md` en disco existe y mide < 50% de
   la base, se restaura con la base (hoy: solo ReASearch, el stub de H12).
3. Si aprueba, el arnés queda cerrado. Si no, **unidad de reparación
   HITO7 §1**: M1 localizador LLM pequeño (frases del juez → `N -> M | eco`,
   validado mecánicamente con1 reintento) + M2 marcado determinista de las
   líneas validadas. **Cero `generate()` de reescritura de blueprint** (M3):
   sin regeneración no hay truncos ni pérdida de encabezados posibles.
4. Juicio de la nueva ronda. Hasta **3 rondas** de reparación (runs 1..3);
   tres fallos seguidos = arnés fallo (sin ronda 4). Presupuesto global
   declarado: ≤ 12 localizadores; agotados, causa
   `presupuesto_localizador_agotado`.

Escrituras idempotentes: filas `arm="H14"` en
`evals/result_fase1_h14.json` y juicios `arm="H14", run=ronda` en
`evals/result_q1_r4r5.json` (H1, H1R, H12, H13 sin tocar). Re-ejecutar el
script retoma por el último juicio.

Uso (env del juez obligatoria: sin ella se aborta):

    JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... Q1_API_KEY=... \
      .venv/bin/python evals/run_fase1_h14.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_q1_r4r5 import q1
from run_blueprint_ab import _corpus, score
from run_dimension_d import GOAL, TECNICAS

from bibliotecario.agent.attribution import (
    encabezados,
    localizador_prompt,
    localizador_reintento,
    marcar_lineas,
    parse_localizador,
    validate_structure,
)
from bibliotecario.agent.tools import (
    _source_for,
    generate,
)
from bibliotecario.knowledge import procedural as P

ROOT = Path(__file__).resolve().parents[1]
H1 = ROOT / "evals" / "result_fase1_h1.json"
H1R = ROOT / "evals" / "result_fase1_h1r.json"
H13 = ROOT / "evals" / "result_fase1_h13.json"
OUT = ROOT / "evals" / "result_fase1_h14.json"
JUICIOS = ROOT / "evals" / "result_q1_r4r5.json"
ARM = "H14"
MAX_ROUNDS = 3        # HITO7 §3: base + hasta 3 rondas; no hay ronda 4.
MAX_LOC = 12          # HITO7 §3: presupuesto global de localizadores.
LOC_MAX_TOKENS = 600  # salida estricta: solo «N -> M | eco» por frase.


def _leer(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _escribir(path: Path, rows: list[dict], indent: int = 1) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=indent),
                    encoding="utf-8")


def _frases(j: dict) -> list[str]:
    return list(j.get("r4_fabricaciones") or []) + list(j.get("r5_rellenados") or [])


def _base(tech: str) -> dict | None:
    """Base HITO7 §1: mejor estado juzgado y aprobado conocido.

    Los textos de H13 cuyo juicio aprobó (r4 y r5), si no H1R, si no H1.
    Nunca un artefacto suspendido del intento 3.
    """
    h13 = {r["technique"]: r for r in _leer(H13)
           if r.get("arm") == "H13" and r.get("ok") and (r.get("blueprint") or "").strip()}
    aprobados = {j["technique"]: j["run"] for j in _leer(JUICIOS)
                 if j.get("arm") == "H13" and j.get("r4_ok") and j.get("r5_ok")}
    run = aprobados.get(tech)
    if run is not None and tech in h13:
        fila = [r for r in _leer(H13) if r.get("arm") == "H13"
                and r.get("technique") == tech and r.get("round") == run
                and r.get("ok")]
        if fila:
            return fila[-1]
    h1r = {r["technique"]: r for r in _leer(H1R)
           if r.get("arm") == "H1R" and r.get("ok")}
    h1 = {r["technique"]: r for r in _leer(H1)
          if r.get("arm") == "H1" and r.get("ok")}
    return h1r.get(tech) or h1.get(tech)


def _fuente_y_doc(tech: str) -> tuple[int | None, str]:
    """Mismos argumentos que `_source` de eval_q1_r4r5 (el juez los necesita)."""
    procs = P.list_procedures(technique=tech)
    return _source_for(tech, procs, max_chunks=8, max_chars=9000)


def _fila(rows: list[dict], tech: str, rnd: int) -> dict | None:
    cands = [r for r in rows if r.get("arm") == ARM
             and r.get("technique") == tech and r.get("round") == rnd]
    return cands[-1] if cands else None


def _juicio(juicios: list[dict], tech: str, run: int) -> dict | None:
    cands = [j for j in juicios if j.get("arm") == ARM
             and j.get("technique") == tech and j.get("run") == run]
    return cands[-1] if cands else None


def _sustituir(rows: list[dict], tech: str, rnd: int, fila: dict) -> None:
    viejas = [r for r in rows if not (r.get("arm") == ARM
                                      and r.get("technique") == tech
                                      and r.get("round") == rnd)]
    rows[:] = viejas + [fila]
    _escribir(OUT, rows)


def _guardar_fila(rows: list[dict], tech: str, rnd: int, bp: str,
                  doc_id: int | None, base: dict, corpus: dict,
                  t0: float, loc: dict | None = None) -> dict:
    fila = {"arm": ARM, "technique": tech, "round": rnd, "ok": True,
            "secs": round(time.time() - t0, 1), "blueprint": bp,
            "doc_id": doc_id, "dir": base.get("dir"), "loc": loc or {},
            "checks": score(bp, corpus), "encabezados": encabezados(bp)}
    _sustituir(rows, tech, rnd, fila)
    return fila


def _guardar_fallo(rows: list[dict], tech: str, rnd: int, causa: str,
                   doc_id: int | None, base: dict, evidencia: dict | None,
                   t0: float) -> dict:
    """Registro de fallo declarado (HITO7 §3): sin maquillar, sin juez sobre
    nada que no exista, sin escritura a disco."""
    fila = {"arm": ARM, "technique": tech, "round": rnd, "ok": False,
            "causa": causa, "evidencia": evidencia or {},
            "secs": round(time.time() - t0, 1),
            "doc_id": doc_id, "dir": base.get("dir"), "blueprint": None}
    _sustituir(rows, tech, rnd, fila)
    return fila


def _sanear_disco(base: dict, tech: str, bp: str) -> str | None:
    """M4 (HITO7 §1): disco < 50% de la base → restaurado con la base."""
    d = base.get("dir")
    if not d:
        return None
    path = Path(d) / "BLUEPRINT.md"
    if not path.exists() or len(path.read_text(encoding="utf-8").strip()) \
            >= int(len(bp.strip()) * 0.5):
        return None
    path.write_text(f"# {tech}\n\nObjetivo: {GOAL}\n\n{bp}\n",
                    encoding="utf-8")
    return str(path)


def _resumen(rows: list[dict], juicios: list[dict]) -> dict:
    """Tabla final: último juicio por arnés + G1/G2/V1 (HITO7 §2)."""
    print("\n" + "=" * 70)
    print(f"Resumen {ARM} — H1 intento 4 (último juicio por arnés)")
    print("=" * 70)
    h5 = g1 = g2 = 0
    c1 = True
    for tech in TECNICAS:
        runs = sorted({j["run"] for j in juicios if j.get("arm") == ARM
                       and j.get("technique") == tech})
        if not runs:
            print(f"  [ -- ] {tech}: sin juicio")
            continue
        run = runs[-1]
        j = _juicio(juicios, tech, run)
        fin = _fila(rows, tech, run)
        base = _fila(rows, tech, 0)
        h5_ok = bool(j and j.get("r4_ok") and j.get("r5_ok") and fin)
        ok_g1 = ok_g2 = ok_v1 = False
        if base and fin:
            ok_g1 = (fin["checks"]["citas_resueltas"]
                     >= base["checks"]["citas_resueltas"])
            fallos = validate_structure(base["blueprint"], fin["blueprint"])
            ok_g2 = not any(f.startswith("V2") for f in fallos)
            ok_v1 = not any(f.startswith("V1") for f in fallos)
        fallos_fila = [r for r in rows if r.get("arm") == ARM
                       and r.get("technique") == tech and r.get("ok") is False]
        if fallos_fila:
            c1 = False
        h5 += h5_ok
        g1 += ok_g1
        g2 += ok_g2
        c1 = c1 and (ok_v1 if base and fin else False)
        v = "" if h5_ok else "  <-- NO r4/r5"
        causa = (f" [FALLO {fallos_fila[-1].get('causa')}]"
                 if fallos_fila else "")
        print(f"  [{'OK' if h5_ok else 'NO'}] {tech}: ronda {run} "
              f"R4={'si' if (j and j.get('r4_ok')) else 'no'} "
              f"R5={'si' if (j and j.get('r5_ok')) else 'no'} · "
              f"resueltas {base['checks']['citas_resueltas'] if base else '?'}->"
              f"{fin['checks']['citas_resueltas'] if fin else '?'} "
              f"(G1 {'si' if ok_g1 else 'no'}) · "
              f"encabezados (G2 {'si' if ok_g2 else 'no'}) · "
              f"V1 longitud {'si' if ok_v1 else 'NO'}{causa}{v}")
    n = len(TECNICAS)
    print("-" * 70)
    print(f"  H5' 5/5 r4_ok y r5_ok          {h5}/{n}")
    print(f"  G1   resueltas finales >= base  {g1}/{n}")
    print(f"  G2   encabezados conservados    {g2}/{n}")
    print(f"  C1'  V1 + sin fallos + suite    {'si' if c1 else 'NO'} "
          f"(suite de tests: correr aparte)")
    cumple = h5 == n and g1 == n and g2 == n and c1
    print(f"\n  VEREDICTO {'CUMPLE' if cumple else 'NO CUMPLE'} "
          f"(HITO7 §2: H5' y G1 y G2 y C1' — la suite se confirma con pytest)")
    return {"h5": h5, "g1": g1, "g2": g2, "c1": c1, "cumple": cumple}


def main() -> int:
    falta = [k for k in ("JUDGE_MODEL", "Q1_BASE_URL", "Q1_API_KEY")
             if not os.environ.get(k)]
    if falta:
        print(f"FALTA env del juez declarado: {', '.join(falta)}")
        print("Uso: JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... "
              "Q1_API_KEY=... .venv/bin/python evals/run_fase1_h14.py")
        return 1
    print(f"Instrumento: {os.environ['JUDGE_MODEL']} (temp del juez: "
          f"{os.environ.get('Q1_TEMPERATURE', '0')})")

    rows = [r for r in _leer(OUT) if r.get("arm") == ARM]
    juicios = _leer(JUICIOS)
    juicios = [j for j in juicios if not (j.get("arm") == ARM and j.get("error"))]
    corpus = _corpus()

    n_juicios = n_loc = 0
    print("=" * 70)
    print(f"Hito 7 — H1 intento 4 ({ARM}) · base + <= {MAX_ROUNDS} rondas · "
          f"n={len(TECNICAS)} · presupuesto localizadores={MAX_LOC}")
    print("=" * 70)

    for tech in TECNICAS:
        base = _base(tech)
        if not base or not (base.get("blueprint") or "").strip():
            print(f"  [{ARM}] {tech} ... ERROR sin fila base (H13/H1R/H1)")
            return 1
        doc_id, fuente = _fuente_y_doc(tech)
        if not fuente:
            print(f"  [{ARM}] {tech} ... ERROR sin chunks de la técnica "
                  f"(el juez no puede juzgar sin fuente)")
            return 1
        bp = base["blueprint"]
        for rnd in range(MAX_ROUNDS + 1):
            if rnd == 0:
                t0 = time.time()
                san = _sanear_disco(base, tech, bp)
                if san:
                    print(f"  [{ARM}] {tech} ... M4 disco saneado (<50% "
                          f"de la base): {san}")
                _guardar_fila(rows, tech, 0, bp, doc_id, base, corpus, t0)
            else:
                f = _fila(rows, tech, rnd)
                if f is None:
                    print(f"  [{ARM}] {tech} ... ERROR sin estado de "
                          f"ronda {rnd}")
                    return 1
                if f.get("ok") is False:
                    print(f"  [{ARM}] {tech} ... arnés FALLO en ronda {rnd}: "
                          f"{f.get('causa')}")
                    break
                if not (f.get("blueprint") or "").strip():
                    print(f"  [{ARM}] {tech} ... ERROR blueprint vacío "
                          f"de ronda {rnd}")
                    return 1
                bp = f["blueprint"]

            j = _juicio(juicios, tech, rnd)
            if j is None:
                print(f"  [{ARM}] {tech} ronda {rnd} ... juzgando ", end="", flush=True)
                t0 = time.time()
                res = q1(fuente, bp)
                n_juicios += 1
                res.update({"arm": ARM, "technique": tech, "run": rnd,
                            "secs": round(time.time() - t0, 1)})
                juicios.append(res)
                _escribir(JUICIOS, juicios, indent=2)
                if res.get("error"):
                    print(f"ERROR {res['error']}")
                    print("  -> re-ejecuta el script (el juicio fallido se repite)")
                    return 1
                j = res
                print(f"R4={'OK' if res['r4_ok'] else 'FALLA'} "
                      f"R5={'OK' if res['r5_ok'] else 'FALLA'} "
                      f"({time.time() - t0:.0f}s)")
            else:
                print(f"  [{ARM}] {tech} ronda {rnd} ... juicio ya registrado, salto")

            if j and j.get("r4_ok") and j.get("r5_ok"):
                print(f"  [{ARM}] {tech} ... APRUEBA en ronda {rnd}")
                break
            if rnd == MAX_ROUNDS:
                print(f"  [{ARM}] {tech} ... NO APRUEBA tras {MAX_ROUNDS} "
                      f"reparaciones (fin de arnés)")
                break

            nxt = _fila(rows, tech, rnd + 1)
            if nxt and nxt.get("ok") and (nxt.get("blueprint") or "").strip():
                print(f"  [{ARM}] {tech} ... marcado de ronda {rnd + 1} "
                      f"ya hecho, salto")
                continue
            if nxt and nxt.get("ok") is False:
                print(f"  [{ARM}] {tech} ... ronda {rnd + 1} ya registró "
                      f"fallo, arnés en fallo")
                break

            # --- unidad de reparación HITO7 §1: M1 localizador + M2 marcado
            t1 = time.time()
            frases = _frases(j)
            if not frases:
                _guardar_fallo(rows, tech, rnd + 1, "sin_frases_del_juez",
                               doc_id, base,
                               {"r4_ok": j.get("r4_ok"), "r5_ok": j.get("r5_ok")},
                               t1)
                print(f"  [{ARM}] {tech} ... FALLO: el juez suspendió sin "
                      f"listar frases (registrado)")
                continue
            if n_loc >= MAX_LOC:
                _guardar_fallo(rows, tech, rnd + 1,
                               "presupuesto_localizador_agotado", doc_id,
                               base, {"frases": frases[:10]}, t1)
                print(f"  [{ARM}] {tech} ... FALLO: presupuesto de "
                      f"localizadores agotado ({MAX_LOC})")
                continue

            print(f"  [{ARM}] {tech} ronda {rnd} ... M1 localizando "
                  f"{len(frases)} frases")
            prompt = localizador_prompt(frases, bp)
            parse = None
            for intento in (1, 2):
                salida = (generate(prompt, max_tokens=LOC_MAX_TOKENS) or "").strip()
                n_loc += 1
                if not salida or salida.startswith("("):
                    print("    ERROR localizador vacio o de emergencia (sin LLM)")
                    print("  -> re-ejecuta el script (no se registra ronda)")
                    return 1
                parse = parse_localizador(salida, bp, len(frases))
                if not parse["invalidas"]:
                    break
                print(f"    M1: RECHAZO intento {intento}/2: "
                      f"{'; '.join(parse['invalidas'][:5])}")
                prompt = localizador_reintento(prompt, parse["invalidas"])
            bp_m, stats = marcar_lineas(bp, parse["validas"])
            loc_info = {"frases": len(frases), "validas": len(parse["validas"]),
                        "no_localizadas": parse["no_localizadas"],
                        "invalidas": parse["invalidas"],
                        "marcadas": stats["marcadas"],
                        "omitidas": stats["omitidas"],
                        "intento_final": intento}
            print(f"    M2: {stats['marcadas']} líneas marcadas "
                  f"({len(parse['no_localizadas'])} frases sin localizar, "
                  f"{len(parse['invalidas'])} entradas inválidas)")
            _guardar_fila(rows, tech, rnd + 1, bp_m, doc_id, base, corpus,
                          t1, loc=loc_info)
            d = base.get("dir")
            if d and Path(d).exists():
                (Path(d) / "BLUEPRINT.md").write_text(
                    f"# {tech}\n\nObjetivo: {GOAL}\n\n{bp_m}\n",
                    encoding="utf-8")
            print(f"    ok {time.time() - t1:.0f}s (sin reescritura; "
                  f"BLUEPRINT.md actualizado)")

    res = _resumen(rows, juicios)
    print(f"\n  coste de esta ejecución: {n_juicios} juicios + {n_loc} "
          f"localizadores (0 reescrituras)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
