"""HITO18 §1 — corrida oficial B-2 etapa 2 híbrida (métrica + juez V/A).

Gates U1-U7 ratificados en `evals/HITO18_PLAN.md` §2 (2026-10-22, ANTES
de implementar y de medir). Diferencias respecto a H17:

- **U4′ determinista**: la sensibilidad se mide con `M_mov` (frame-diff
  en grises, `movimiento_b2.py`) — default ≥ 0.20, Δ(default−idle) ≥ 0.15,
  idle ≤ 0.15. **Sin llamadas al juez**; invulnerable a 503.
- **El juez solo puntúa V/A** (los ítems D se piden y registran pero no
  puntúan): `Score_B2 = 0.50·S_mov + 0.25·V + 0.25·A` con
  `S_mov = clamp(M_mov(default)/0.50, 0, 1)`. La fórmula externa
  `BUILD × (0.15·M_B1 + Score_B2)` no cambia.
- **Idle ya no llama al juez** (solo captura/replay para U4′) y el
  negro sigue anulado por el prefiltro Opción B (0 llamadas) →
  presupuesto **≤8**: default(≤2)+default2(≤2)+U7a con(≤2)+vacío(≤2).
- **U7a** = trampa del juez de H17 (con ≥0.5 / vacío = 0);
  **U7b** = trampa de la métrica (sprite en movimiento ≥0.20 vs su
  gemela estática ≤0.05), determinista, sin LLM.

Salida: `evals/results/result_fase2_b2_h18.json` (H16/H17 intactos).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import juez_b2
import movimiento_b2 as mov
import run_fase2_b2 as base
import run_fase2_b2_h17 as h17

OUT_JSON = base.ROOT / "evals" / "results" / "result_fase2_b2_h18.json"
GATES_H18 = ("U1", "U2", "U3", "U4", "U5", "U6", "U7a", "U7b")
LLAMADAS_MAX = 8


def gate_u3h(e1: dict, e2: dict, s1: float, s2: float) -> tuple[bool, str]:
    """U3: estabilidad del Score_B2 híbrido y de las categorías V/A."""
    if e1.get("error") or e2.get("error"):
        return False, "falta una de las dos corridas de default"
    d_score = abs(s1 - s2)
    d_va = {c: round(abs(e1[c] - e2[c]), 4) for c in ("V", "A")}
    ok = (d_score <= base.U3_SCORE_DELTA
          and all(v <= base.U3_CAT_DELTA for v in d_va.values()))
    return ok, (f"ΔScore_B2_hib={d_score} (≤{base.U3_SCORE_DELTA}) · "
                f"ΔV/A={d_va} (≤{base.U3_CAT_DELTA} c/u)")


def _final(registro: dict, gates: dict, llamadas: list[int],
           tokens: list[int]) -> int:
    OUT_JSON.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    todos = base.gates_todos_ok(gates, GATES_H18)
    print("\n" + "=" * 66)
    print("HITO18 B-2 etapa 2 (hibrido) — UMBRALES")
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
    registro: dict = {
        "hito": 18, "tarea": base.TAREA,
        "enmienda": "hibrida M_mov + juez V/A (HITO18_PLAN.md §1)",
        "juez": juez_b2.JUDGE_MODEL_B2,
        "temperatura": juez_b2.TEMPERATURE,
        "rubrica": str(juez_b2.RUBRICAS / f"{base.TAREA}.json"),
        "formula_b2": "0.50·S_mov + 0.25·V + 0.25·A "
                      "(S_mov=clamp(M_mov/0.50,0,1))"}

    # ---- U5: ρ oculta
    u5_ok, d5 = h17._gate_u5(registro["rubrica"])
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
    print(f"U6 B-1: BUILD={b1['BUILD']} M_B1={b1['M_B1']}")

    # ---- frames
    print("frames: default …", flush=True)
    frames_def = base._frames_default(out_dir, args.display)
    print(f"  default {len(frames_def)} · idle …", flush=True)
    frames_idle = base._frames_idle(out_dir, args.display)
    print(f"  idle {len(frames_idle)} · negro …", flush=True)
    frames_neg = base._frames_negro(out_dir / "negro")
    print(f"  negro {len(frames_neg)} · trampas U7a/U7b …", flush=True)
    tr_con, tr_sin = h17.frames_trampa(out_dir / "sintetico")
    mov_seq, est_seq = mov.trampas_mov(out_dir / "sintetico_mov")
    print("  listas")

    # ---- M_mov (determinista, sin LLM)
    m_def = mov.m_mov(frames_def)
    m_idle = mov.m_mov(frames_idle)
    s_def = mov.s_mov(m_def)
    m_u7b_mov = mov.m_mov(mov_seq)
    m_u7b_est = mov.m_mov(est_seq)
    registro["movimiento"] = {
        "M_mov_default": m_def, "M_mov_idle": m_idle, "S_mov": s_def,
        "M_mov_ref": mov.M_MOV_REF,
        "U7b": {"mov": m_u7b_mov, "estatico": m_u7b_est}}
    print(f"M_mov: default={m_def} idle={m_idle} S_mov={s_def} · "
          f"U7b mov={m_u7b_mov} est={m_u7b_est}")

    # ---- evaluaciones (juez solo en default/default2 y U7a)
    e_def1 = h17._eval("default", rubrica, frames_def, llamadas, tokens)
    e_def2 = h17._eval("default2", rubrica, frames_def, llamadas, tokens)
    e_negro = h17._eval("negro", rubrica, frames_neg, llamadas, tokens)
    e_con = h17._eval("trampa_con", rub_t, [tr_con], llamadas, tokens,
                      prefiltrar=False)
    e_vacio = h17._eval("trampa_vacio", rub_t, [tr_sin], llamadas, tokens,
                        prefiltrar=False)
    registro["evaluaciones"] = {
        "default": e_def1, "default2": e_def2, "negro": e_negro,
        "trampa_con": e_con, "trampa_vacio": e_vacio}

    # ---- Score_B2 híbrido (V/A del juez + S_mov determinista)
    def _hib(e: dict) -> float | None:
        if e.get("error"):
            return None
        return mov.score_b2_hibrido(s_def, e["V"], e["A"])

    s1, s2 = _hib(e_def1), _hib(e_def2)
    registro["Score_B2"] = s1
    if e_negro.get("prefiltro", {}).get("sin_contenido"):
        registro["Score_B2_negro"] = 0.0

    # ---- gates
    ok1, d1 = base.gate_u1(e_def1, len(rubrica["items"]))
    gates["U1"] = {"ok": ok1, "detalle": d1}

    ok2, d2 = base.gate_u2(e_negro, rubrica)
    if e_negro.get("prefiltro", {}).get("sin_contenido"):
        d2 += " · prefiltro activo (anulacion por construccion)"
    gates["U2"] = {"ok": ok2, "detalle": d2}

    if s1 is None or s2 is None:
        gates["U3"] = {"ok": False, "detalle": "default/default2 con error"}
    else:
        ok3, d3 = gate_u3h(e_def1, e_def2, s1, s2)
        gates["U3"] = {"ok": ok3, "detalle": d3}

    ok4, d4 = mov.gate_u4p(m_def, m_idle)
    gates["U4"] = {"ok": ok4, "detalle": d4}

    ok7a, d7a = h17.gate_u7(e_con, e_vacio)
    gates["U7a"] = {"ok": ok7a, "detalle": d7a}

    ok7b, d7b = mov.gate_u7b(m_u7b_mov, m_u7b_est)
    gates["U7b"] = {"ok": ok7b, "detalle": d7b}

    llam = sum(llamadas)
    ok6_coste = llam <= LLAMADAS_MAX
    ok6 = (b1["BUILD"] == 1.0 and ok6_coste)
    gates["U6"] = {
        "ok": ok6,
        "detalle": f"B-1: BUILD={b1['BUILD']} M_B1={b1['M_B1']}"
                   f" · llamadas={llam}/{LLAMADAS_MAX}" + (
                       "" if ok6_coste else " EXCEDIDO") +
                   " · suite+ruff aparte"}

    # ---- score final (D2: exige U1-U7 todos OK; Score_B2 = híbrido)
    e_score = {**e_def1, "Score_B2": s1 if s1 is not None else 0.0}
    registro["Score_final"] = base.calcular_score_final(
        gates, b1, e_score, GATES_H18)
    registro["llamadas"] = llam
    registro["tokens_total"] = sum(tokens)
    registro["gates"] = gates

    return _final(registro, gates, llamadas, tokens)


if __name__ == "__main__":
    raise SystemExit(main())
