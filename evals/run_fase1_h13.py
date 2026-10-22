"""Hito 6 — cierre de H1, intento 3: «reparación que no degenere» (brazo `H13`).

Declaración previa en `evals/HITO6_PLAN.md` (2026-10-17, escrita ANTES de
este archivo y ANTES de medir; umbrales H5'/G1/G2/C1' a ratificar por el
dueño antes de la corrida oficial).

Qué hace, por cada uno de los 5 arneses (TCE incluido):

1. **Ronda 0 — juicio fresco de la base** (filas `H1R` si existen, si no
   `H1` — el mismo estado pre-intento-2 de HITO5; ninguna fila H12 se
   reutiliza ni se toca), con el MISMO instrumento de H1/H12:
   `gemini-3.1-flash-lite` @ Google, temp 0, prompt de `eval_q1_r4r5`.
2. Si aprueba, el arnés queda cerrado; si suspende, **unidad de reparación**
   HITO6 §1: (A) mecánico determinista 0 tokens — `normalize_pointers`,
   `demote_unsupported`, marcar huérfanas — y (B) reparación LLM **con
   validación de salida**: V1 longitud (>= 50% de la base), V2 encabezados
   base (misma definición que G2), V3 citas resueltas >= base (G1 en el
   bucle). Un rechazo = reintento con los fallos concretos en el prompt;
   dos rechazos = arnés fallo con causa registrada (el texto rechazado no se
   juzga ni toca disco). Vacío o «(» sigue siendo error de infraestructura:
   aborta y se re-ejecuta.
3. Juicio de la nueva ronda. Hasta **3 rondas** de reparación (runs 1..3);
   tres fallos seguidos = arnés fallo (sin ronda 4).

Escrituras idempotentes: blueprints/estado mecánico en
`evals/results/result_fase1_h13.json` (filas `arm="H13"`, `round`), juicios en el
compartido `evals/results/result_q1_r4r5.json` (`arm="H13"`, `run=round` — las filas
`H1`/`H1R`/`H12` no se tocan). Re-ejecutar el script retoma por el último
juicio.

Uso (env del juez obligatoria: sin ella se aborta, para que el instrumento
nunca cambie en silencio):

    JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... Q1_API_KEY=... \
      .venv/bin/python evals/run_fase1_h13.py
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
    MIN_FRACCION,
    encabezados,
    mech_repair,
    validate_structure,
)
from bibliotecario.agent.tools import (
    BLUEPRINT_MAX_TOKENS,
    _cited_chunks,
    _source_for,
    generate,
    verify_and_mark,
)
from bibliotecario.knowledge import procedural as P
from bibliotecario.knowledge.study import normalize_pointers

ROOT = Path(__file__).resolve().parents[1]
H1 = ROOT / "evals" / "results" / "result_fase1_h1.json"
H1R = ROOT / "evals" / "results" / "result_fase1_h1r.json"
OUT = ROOT / "evals" / "results" / "result_fase1_h13.json"
JUICIOS = ROOT / "evals" / "results" / "result_q1_r4r5.json"
ARM = "H13"
MAX_ROUNDS = 3  # HITO6 §3: base + hasta 3 rondas; no hay ronda 4.
MAX_INTENTOS = 2  # HITO6 §1.B: 1 reintento de validación; 2.º = arnés fallo.

_PROMPT = """Estás reparando un blueprint del sistema Bibliotecario.

Un revisor automático (el mismo que aprueba o suspende este blueprint) señaló
estas frases CONCRETAS como fallos:

R4 — atribuye a la fuente cosas que la fuente no dice:
{r4}

R5 — rellena detalles que la fuente no especifica:
{r5}

DETECCIÓN MECÁNICA (frases con término técnico sin ancla, sin puntero o con
puntero que no resuelve — verificador local, sin juez; el marcado mecánico
determinista YA está aplicado en el texto de abajo, respétalo):
{mec}

FUENTE (lo ÚNICO que el blueprint puede atribuir al paper; los punteros
[doc:id:chunk] tienen que apuntar a trozos que estén aquí):
{fuente}

BASE OBLIGATORIA — tu salida se RECHAZA automáticamente si rompe esto:
- Encabezados ## literales que DEBEN aparecer (texto exacto, sin renombrar):
{encabezados_base}
- Longitud mínima: {min_len} caracteres (50% de la base; no resumas ni
  devuelvas un fragmento).
- No pierdas las citas [doc:id:chunk] que ya resuelven.

{rechazo}
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
3. Conserva la estructura, TODOS los encabezados ## de la BASE, la
   bibliografía, las citas que ya funcionan y las declaraciones de silencio
   existentes. No inventes módulos, umbrales ni métricas nuevas. No añadas
   nada que no sea corrección de lo señalado.

Devuelve SOLO el blueprint completo corregido, en markdown."""

_RECHAZO = """Tu intento ANTERIOR fue RECHAZADO por la validación automática:
{fallos}
Devuelve el blueprint COMPLETO corregido, entero — no un fragmento.

"""


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
    """Base del intento 3: MISMA definición que HITO5 — H1R si existe, si no
    H1. Nunca el estado dañado de H12 (HITO6 §2)."""
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
                  t0: float, rechazos: int = 0,
                  mec_prev: dict | None = None) -> dict:
    fila = {"arm": ARM, "technique": tech, "round": rnd, "ok": True,
            "secs": round(time.time() - t0, 1), "blueprint": bp,
            "doc_id": doc_id, "dir": base.get("dir"), "rechazos": rechazos,
            "mec_prev": mec_prev or {}, "mech": _mech(doc_id, bp),
            "checks": score(bp, corpus), "encabezados": encabezados(bp)}
    _sustituir(rows, tech, rnd, fila)
    return fila


def _guardar_rechazo(rows: list[dict], tech: str, rnd: int,
                     doc_id: int | None, base: dict, fallos: list[str],
                     texto: str | None, t0: float) -> dict:
    """Registro del 2.º rechazo (HITO6 §1.B): el arnés falla con causa.

    El texto rechazado se guarda solo como evidencia de la corrida: no se
    juzga, no se copia a BLUEPRINT.md y su `blueprint` es None para que
    ninguna tabla lo confunda con un estado aceptado.
    """
    fila = {"arm": ARM, "technique": tech, "round": rnd, "ok": False,
            "causa": "validacion_rechazada", "fallos": fallos,
            "texto_rechazado": texto, "secs": round(time.time() - t0, 1),
            "doc_id": doc_id, "dir": base.get("dir"), "blueprint": None}
    _sustituir(rows, tech, rnd, fila)
    return fila


def _sustituir(rows: list[dict], tech: str, rnd: int, fila: dict) -> None:
    viejas = [r for r in rows if not (r.get("arm") == ARM
                                      and r.get("technique") == tech
                                      and r.get("round") == rnd)]
    rows[:] = viejas + [fila]
    _escribir(OUT, rows)


def _resumen(rows: list[dict], juicios: list[dict]) -> dict:
    """Tabla final: último juicio por arnés + G1/G2/V1 (HITO6 §2)."""
    print("\n" + "=" * 70)
    print(f"Resumen {ARM} — H1 intento 3 (último juicio por arnés)")
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
        rechazos = [r for r in rows if r.get("arm") == ARM
                    and r.get("technique") == tech and r.get("ok") is False]
        if rechazos:
            c1 = False
        h5 += h5_ok
        g1 += ok_g1
        g2 += ok_g2
        c1 = c1 and (ok_v1 if base and fin else False)
        v = "" if h5_ok else "  <-- NO r4/r5"
        causa = f" [FALLO {rechazos[-1].get('causa')}]" if rechazos else ""
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
    print(f"  C1'  V1 + sin rechazos + suite  {'si' if c1 else 'NO'} "
          f"(suite de tests: correr aparte)")
    cumple = h5 == n and g1 == n and g2 == n and c1
    print(f"\n  VEREDICTO {'CUMPLE' if cumple else 'NO CUMPLE'} "
          f"(HITO6 §2: H5' y G1 y G2 y C1' — la suite se confirma con pytest)")
    return {"h5": h5, "g1": g1, "g2": g2, "c1": c1, "cumple": cumple}


def main() -> int:
    # Instrumento declarado (HITO6 §2): sin env explícito NO se corre, para
    # que el juez no pueda cambiar en silencio por el default del módulo.
    falta = [k for k in ("JUDGE_MODEL", "Q1_BASE_URL", "Q1_API_KEY")
             if not os.environ.get(k)]
    if falta:
        print(f"FALTA env del juez declarado: {', '.join(falta)}")
        print("Uso: JUDGE_MODEL=gemini-3.1-flash-lite Q1_BASE_URL=... "
              "Q1_API_KEY=... .venv/bin/python evals/run_fase1_h13.py")
        return 1
    print(f"Instrumento: {os.environ['JUDGE_MODEL']} (temp del juez: "
          f"{os.environ.get('Q1_TEMPERATURE', '0')})")

    rows = [r for r in _leer(OUT) if r.get("arm") == ARM]
    juicios = _leer(JUICIOS)
    # Un fallo de parseo no es evaluación (mismo criterio que eval_q1_r4r5):
    # se purga de memoria y se vuelve a juzgar al re-ejecutar.
    juicios = [j for j in juicios if not (j.get("arm") == ARM and j.get("error"))]
    corpus = _corpus()

    n_juicios = n_repar = n_rechazos = 0
    print("=" * 70)
    print(f"Hito 6 — H1 intento 3 ({ARM}) · base + <= {MAX_ROUNDS} rondas · "
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
        base_res = score(bp, corpus)["citas_resueltas"]
        min_len = int(len(bp.strip()) * MIN_FRACCION)
        base_enc = encabezados(bp)
        base_enc_txt = ("\n".join(f"- «{h}»" for h in base_enc)
                        or "- (el blueprint base no tiene encabezados ##)")
        for rnd in range(MAX_ROUNDS + 1):
            if rnd == 0:
                t0 = time.time()
                _guardar_fila(rows, tech, 0, bp, doc_id, base, corpus, t0)
            else:
                f = _fila(rows, tech, rnd)
                if f is None:
                    print(f"  [{ARM}] {tech} ... ERROR sin blueprint de "
                          f"ronda {rnd}")
                    return 1
                if f.get("ok") is False:
                    print(f"  [{ARM}] {tech} ... arnés FALLO en ronda {rnd}: "
                          f"{f.get('causa')} — {f.get('fallos')}")
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
                print(f"  [{ARM}] {tech} ... reparación de ronda {rnd + 1} "
                      f"ya hecha, salto")
                continue
            if nxt and nxt.get("ok") is False:
                print(f"  [{ARM}] {tech} ... ronda {rnd + 1} ya registró "
                      f"rechazo doble, arnés en fallo")
                break

            # --- unidad de reparación HITO6 §1 -----------------------------
            print(f"  [{ARM}] {tech} ronda {rnd} ... reparando (A mec + B LLM "
                  f"validado):")
            t1 = time.time()
            # A: mecánico determinista, 0 tokens (normalizar para poder cargar
            # los chunks del texto ya canónico — la normalización es idempotente)
            bp_n, n_norm = normalize_pointers(bp)
            chunks = _cited_chunks(doc_id, bp_n)
            bp_m, stats_m = mech_repair(bp_n, chunks)
            viols_m = (verify_and_mark({"blueprint": bp_m, "doc_id": doc_id})
                       .get("violaciones") or [])
            print(f"    A: {stats_m['violaciones']} violaciones ("
                  f"{stats_m['punteros_quitados']} punteros quitados, "
                  f"{stats_m['marcados_termino']} marcados, "
                  f"{stats_m['huerfanas_marcadas']} huérfanas marcadas, "
                  f"{n_norm} punteros normalizados)")
            # B: LLM con validación de salida (hasta MAX_INTENTOS intentos)
            aceptado = None
            fallos: list[str] = []
            draft_previo: str | None = None
            for intento in range(1, MAX_INTENTOS + 1):
                rechazo = ""
                if intento > 1:
                    rechazo = _RECHAZO.format(
                        fallos="\n".join(f"- {x}" for x in fallos))
                prompt = _PROMPT.format(
                    r4=_frases(j.get("r4_fabricaciones")),
                    r5=_frases(j.get("r5_rellenados")),
                    mec=_mec(viols_m),
                    fuente=fuente[:9000],
                    encabezados_base=base_enc_txt,
                    min_len=min_len,
                    rechazo=rechazo,
                    blueprint=bp_m[:9000],
                )
                nuevo = (generate(prompt, max_tokens=BLUEPRINT_MAX_TOKENS) or "").strip()
                n_repar += 1
                if not nuevo or nuevo.startswith("("):
                    # Criterio intacto de HITO5: no es evaluación, es fallo
                    # de llamada — no se registra ronda y se re-ejecuta.
                    print("    ERROR reparacion vacia o de emergencia (sin LLM)")
                    print("  -> re-ejecuta el script (no se registra ronda)")
                    return 1
                draft_previo = nuevo
                fallos = validate_structure(base_bp=bp, draft_bp=nuevo)
                res_n = score(nuevo, corpus)
                if res_n["citas_resueltas"] < base_res:
                    fallos.append(f"V3: citas resueltas "
                                  f"{res_n['citas_resueltas']} < base {base_res}")
                if not fallos:
                    aceptado = nuevo
                    break
                n_rechazos += 1
                print(f"    B: RECHAZO intento {intento}/{MAX_INTENTOS}: "
                      f"{'; '.join(fallos)}")

            if aceptado is None:
                # HITO6 §1.B: 2 rechazos = arnés fallo con causa; el texto
                # rechazado no se juzga ni toca BLUEPRINT.md.
                _guardar_rechazo(rows, tech, rnd + 1, doc_id, base,
                                 fallos, draft_previo, t1)
                print(f"  [{ARM}] {tech} ... arnés FALLO: validación "
                      f"rechazada en 2 intentos")
                continue
            _guardar_fila(rows, tech, rnd + 1, aceptado, doc_id, base, corpus,
                          t1, rechazos=intento - 1, mec_prev=stats_m)
            d = base.get("dir")
            if d and Path(d).exists():
                (Path(d) / "BLUEPRINT.md").write_text(
                    f"# {tech}\n\nObjetivo: {GOAL}\n\n{aceptado}\n",
                    encoding="utf-8")
            print(f"    B: aceptado en intento {intento} "
                  f"({time.time() - t1:.0f}s, BLUEPRINT.md actualizado)")

    res = _resumen(rows, juicios)
    print(f"\n  coste de esta ejecución: {n_juicios} juicios + {n_repar} "
          f"reparaciones generate() ({n_rechazos} rechazos de validación)")
    print(f"  -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
