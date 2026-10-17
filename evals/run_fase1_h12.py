"""Hito 5 — cierre de H1, intento 2 (brazo `H12`).

Declaración previa en `evals/HITO5_PLAN.md` (2026-10-17, escrita ANTES de
este archivo y ANTES de medir; umbrales H5/G1/G2/C1 a ratificar por el dueño
antes de la corrida oficial).

Qué hace, por cada uno de los 5 arneses (TCE incluido):

1. **Ronda 0 — juicio base** del estado actual (TCE desde su fila `H1`; las
   otras cuatro desde `H1R`), con el MISMO instrumento de H1:
   `gemini-3.1-flash-lite` @ Google, temp 0, prompt de `eval_q1_r4r5`.
2. Si aprueba, el arnés queda cerrado; si suspende, **reparación** con la
   evidencia completa de HITO5 §1.4 — frases del juez + violaciones mecánicas
   (`verify_and_mark`, con huérfanas Hito 5) + la fuente — con barrido
   documental y marca R6.
3. Juicio de la nueva ronda. Hasta **3 rondas** de reparación (runs 1..3);
   tres fallos seguidos = arnés fallo (sin ronda 4).

Escrituras idempotentes: blueprints/estado mecánico en
`evals/result_fase1_h12.json` (filas `arm="H12"`, `round`), juicios en el
compartido `evals/result_q1_r4r5.json` (`arm="H12"`, `run=round` — las filas
`H1`/`H1R` no se tocan). Re-ejecutar el script retoma por el último juicio.

Uso (env del juez obligatoria: sin ella se aborta, para que el instrumento
nunca cambie en silencio):

    JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... Q1_API_KEY=... \
      .venv/bin/python evals/run_fase1_h12.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from eval_q1_r4r5 import q1
from run_blueprint_ab import _corpus, score
from run_dimension_d import GOAL, TECNICAS

from bibliotecario.agent.tools import (
    BLUEPRINT_MAX_TOKENS,
    _source_for,
    generate,
    verify_and_mark,
)
from bibliotecario.knowledge import procedural as P

ROOT = Path(__file__).resolve().parents[1]
H1 = ROOT / "evals" / "result_fase1_h1.json"
H1R = ROOT / "evals" / "result_fase1_h1r.json"
OUT = ROOT / "evals" / "result_fase1_h12.json"
JUICIOS = ROOT / "evals" / "result_q1_r4r5.json"
ARM = "H12"
MAX_ROUNDS = 3  # HITO5 §2: base + hasta 3 rondas; no hay ronda 4.

_PROMPT = """Estás reparando un blueprint del sistema Bibliotecario.

Un revisor automático (el mismo que aprueba o suspende este blueprint) señaló
estas frases CONCRETAS como fallos:

R4 — atribuye a la fuente cosas que la fuente no dice:
{r4}

R5 — rellena detalles que la fuente no especifica:
{r5}

DETECCIÓN MECÁNICA (frases con término técnico sin ancla, sin puntero o con
puntero que no resuelve — verificador local, sin juez):
{mec}

FUENTE (lo ÚNICO que el blueprint puede atribuir al paper; los punteros
[doc:id:chunk] tienen que apuntar a trozos que estén aquí):
{fuente}

BLUEPRINT ACTUAL:
{blueprint}

Corrige el documento COMPLETO, no solo los ejemplos listados: el veredicto se
decide sobre todo el texto. Recorre cada punto, en orden:

1. Toda cifra, umbral, protocolo, recomendación, módulo o dependencia que no
   esté literal en la FUENTE se marca «(propuesta del blueprint)» EN SU
   PROPIA LÍNEA (R6) o se quita. Si es un hueco del paper, decláralo:
   «el paper no especifica …». No dejes NINGÚN detalle rellenado sin marcar.
2. Cada frase señalada que lleve puntero [doc:id:chunk]: si la FUENTE lo
   sostiene, reescríbela con cita literal + puntero al chunk correcto; si no
   la sostiene, quita el puntero y márcala (R6).
3. Conserva la estructura, los encabezados, la bibliografía, las citas que ya
   funcionan y las declaraciones de silencio existentes. No inventes módulos,
   umbrales ni métricas nuevas. No añadas nada que no sea corrección de lo
   señalado.

Devuelve SOLO el blueprint completo corregido, en markdown."""


def _leer(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []


def _escribir(path: Path, rows: list[dict], indent: int = 1) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=indent),
                    encoding="utf-8")


def _frases(items: list[str] | None) -> str:
    if not items:
        return "- (ninguna)"
    return "\n".join(f"- «{x}»" for x in items)


def _mec(viols: list[dict] | None) -> str:
    if not viols:
        return "- (ninguna)"
    lines = []
    for v in viols[:15]:
        if v.get("tipo") == "huerfana":
            lines.append(f"- (huérfana: sin puntero ni marca R6) «{v.get('frase', '')}»")
        elif v.get("tipo") == "termino_ausente":
            lines.append(f"- «{v.get('termino')}» no aparece en el chunk "
                         f"[{v.get('chunk')}] que la frase cita: «{v.get('frase', '')}»")
        else:
            lines.append(f"- «{v.get('frase', '')}» apunta a [{v.get('chunk')}], "
                         f"que no existe.")
    return "\n".join(lines)


def _base(tech: str) -> dict | None:
    """Estado actual del arnés: H1R si hubo reparación, si no la fila H1."""
    h1r = {r["technique"]: r for r in _leer(H1R)
           if r.get("arm") == "H1R" and r.get("ok")}
    h1 = {r["technique"]: r for r in _leer(H1)
          if r.get("arm") == "H1" and r.get("ok")}
    return h1r.get(tech) or h1.get(tech)


def _fuente_y_doc(tech: str) -> tuple[int | None, str]:
    """Mismos argumentos que `_source` de eval_q1_r4r5: mismo texto de fuente
    para el juez que para la reparación."""
    procs = P.list_procedures(technique=tech)
    return _source_for(tech, procs, max_chunks=8, max_chars=9000)


def _mech(doc_id: int | None, bp: str) -> dict:
    r = verify_and_mark({"blueprint": bp, "doc_id": doc_id})
    viols = r.get("violaciones") or []
    tipos: dict[str, int] = {}
    for v in viols:
        tipos[v["tipo"]] = tipos.get(v["tipo"], 0) + 1
    return {"violaciones": len(viols), "huerfanas": tipos.get("huerfana", 0),
            "tipos": tipos, "verificado": r.get("verificado"),
            "sin_punteros": r.get("sin_punteros", False)}


def _encabezados(bp: str) -> list[str]:
    return re.findall(r"^##\s+(.+)$", bp, re.MULTILINE)


def _fila(rows: list[dict], tech: str, rnd: int) -> dict | None:
    cands = [r for r in rows if r.get("arm") == ARM
             and r.get("technique") == tech and r.get("round") == rnd]
    return cands[-1] if cands else None


def _juicio(juicios: list[dict], tech: str, run: int) -> dict | None:
    cands = [j for j in juicios if j.get("arm") == ARM
             and j.get("technique") == tech and j.get("run") == run]
    return cands[-1] if cands else None


def _guardar_fila(rows: list[dict], tech: str, rnd: int, bp: str,
                  doc_id: int | None, base: dict, corpus: dict,
                  t0: float) -> dict:
    fila = {"arm": ARM, "technique": tech, "round": rnd, "ok": True,
            "secs": round(time.time() - t0, 1), "blueprint": bp,
            "doc_id": doc_id, "dir": base.get("dir"),
            "mech": _mech(doc_id, bp), "checks": score(bp, corpus),
            "encabezados": _encabezados(bp)}
    viejas = [r for r in rows if not (r.get("arm") == ARM
                                      and r.get("technique") == tech
                                      and r.get("round") == rnd)]
    rows[:] = viejas + [fila]
    _escribir(OUT, rows)
    return fila


def _resumen(rows: list[dict], juicios: list[dict]) -> dict:
    """Tabla final: por arnés su último juicio y las guardas G1/G2 (HITO5 §2)."""
    print("\n" + "=" * 70)
    print(f"Resumen {ARM} — H1 intento 2 (último juicio por arnés)")
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
        # G1/G2 solo tienen sentido con fila base y final; si faltan, no cumple.
        ok_g1 = ok_g2 = False
        if base and fin:
            ok_g1 = fin["checks"]["citas_resueltas"] >= base["checks"]["citas_resueltas"]
            ok_g2 = set(base["encabezados"]) <= set(fin["encabezados"])
            if not (fin["blueprint"].strip()) or fin["blueprint"].lstrip().startswith("("):
                c1 = False
        h5 += h5_ok
        g1 += ok_g1
        g2 += ok_g2
        v = "" if h5_ok else "  <-- NO r4/r5"
        print(f"  [{'OK' if h5_ok else 'NO'}] {tech}: ronda {run} "
              f"R4={'si' if (j and j.get('r4_ok')) else 'no'} "
              f"R5={'si' if (j and j.get('r5_ok')) else 'no'} · "
              f"resueltas {base['checks']['citas_resueltas'] if base else '?'}->"
              f"{fin['checks']['citas_resueltas'] if fin else '?'} "
              f"(G1 {'si' if ok_g1 else 'no'}) · "
              f"encabezados (G2 {'si' if ok_g2 else 'no'}){v}")
    n = len(TECNICAS)
    print("-" * 70)
    print(f"  H5  5/5 r4_ok y r5_ok          {h5}/{n}")
    print(f"  G1  resueltas finales >= base  {g1}/{n}")
    print(f"  G2  encabezados conservados    {g2}/{n}")
    print(f"  C1  blueprints no vacíos       {'si' if c1 else 'NO'} "
          f"(suite de tests: correr aparte)")
    cumple = h5 == n and g1 == n and g2 == n and c1
    print(f"\n  VEREDICTO {'CUMPLE' if cumple else 'NO CUMPLE'} "
          f"(HITO5 §2: H5 y G1 y G2 y C1 — la suite C1 se confirma con pytest)")
    return {"h5": h5, "g1": g1, "g2": g2, "c1": c1, "cumple": cumple}


def main() -> int:
    # Instrumento declarado (HITO5 §3): sin env explícito NO se corre, para
    # que el juez no pueda cambiar en silencio por el default del módulo.
    falta = [k for k in ("JUDGE_MODEL", "Q1_BASE_URL", "Q1_API_KEY")
             if not os.environ.get(k)]
    if falta:
        print(f"FALTA env del juez declarado: {', '.join(falta)}")
        print("Uso: JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... "
              "Q1_API_KEY=... .venv/bin/python evals/run_fase1_h12.py")
        return 1
    print(f"Instrumento: {os.environ['JUDGE_MODEL']} (temp del juez: "
          f"{os.environ.get('Q1_TEMPERATURE', '0')})")

    rows = [r for r in _leer(OUT) if r.get("arm") == ARM]
    juicios = _leer(JUICIOS)
    # Un fallo de parseo no es evaluación (mismo criterio que eval_q1_r4r5):
    # se purga de memoria y se vuelve a juzgar al re-ejecutar.
    juicios = [j for j in juicios if not (j.get("arm") == ARM and j.get("error"))]
    corpus = _corpus()

    n_juicios = n_repar = 0
    print("=" * 70)
    print(f"Hito 5 — H1 intento 2 ({ARM}) · base + <= {MAX_ROUNDS} rondas · "
          f"n={len(TECNICAS)}")
    print("=" * 70)

    for tech in TECNICAS:
        base = _base(tech)
        if not base or not (base.get("blueprint") or "").strip():
            print(f"  [{ARM}] {tech} ... ERROR sin fila base (H1/H1R)")
            return 1
        doc_id, fuente = _fuente_y_doc(tech)
        if not fuente:
            print(f"  [{ARM}] {tech} ... ERROR sin chunks de la técnica "
                  f"(no se puede juzgar ni reparar sin fuente)")
            return 1
        bp = base["blueprint"]
        for rnd in range(MAX_ROUNDS + 1):
            if rnd == 0:
                t0 = time.time()
                _guardar_fila(rows, tech, 0, bp, doc_id, base, corpus, t0)
            else:
                f = _fila(rows, tech, rnd)
                if not f or not f.get("ok") or not (f.get("blueprint") or "").strip():
                    print(f"  [{ARM}] {tech} ... ERROR sin blueprint de ronda {rnd}")
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
                print(f"  [{ARM}] {tech} ... reparación de ronda {rnd + 1} "
                      f"ya hecha, salto")
                continue

            print(f"  [{ARM}] {tech} ronda {rnd} ... reparando ", end="", flush=True)
            t1 = time.time()
            viols = (verify_and_mark({"blueprint": bp, "doc_id": doc_id})
                     .get("violaciones") or [])
            prompt = _PROMPT.format(
                r4=_frases(j.get("r4_fabricaciones")),
                r5=_frases(j.get("r5_rellenados")),
                mec=_mec(viols),
                fuente=fuente[:9000],
                blueprint=bp[:9000],
            )
            nuevo = (generate(prompt, max_tokens=BLUEPRINT_MAX_TOKENS) or "").strip()
            n_repar += 1
            if not nuevo or nuevo.startswith("("):
                print("ERROR reparacion vacia o de emergencia (sin LLM)")
                print("  -> re-ejecuta el script (no se registra ronda)")
                return 1
            _guardar_fila(rows, tech, rnd + 1, nuevo, doc_id, base, corpus, t1)
            d = base.get("dir")
            if d and Path(d).exists():
                (Path(d) / "BLUEPRINT.md").write_text(
                    f"# {tech}\n\nObjetivo: {GOAL}\n\n{nuevo}\n",
                    encoding="utf-8")
            print(f"ok {time.time() - t1:.0f}s (BLUEPRINT.md actualizado)")

    res = _resumen(rows, juicios)
    print(f"\n  coste de esta ejecución: {n_juicios} juicios + {n_repar} "
          f"reparaciones generate()")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
