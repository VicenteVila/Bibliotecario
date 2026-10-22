"""HITO18 — tests puros de la métrica M_mov, el score híbrido y U7b.

Sin red, sin motor, sin juez: Pillow escribe secuencias sintéticas en
tmp y los gates se alimentan con números ratificados en H18 §2.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals" / "preflight"
for _p in (str(ROOT), str(PREFLIGHT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import movimiento_b2 as mov
import run_fase2_b2 as base
import run_fase2_b2_h18 as h18


def _seq(destino: Path, colores: list[tuple]) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    frames = []
    for i, c in enumerate(colores):
        p = destino / f"step_{i:03d}.png"
        Image.new("RGB", (64, 36), c).save(p)
        frames.append(p)
    return frames


def test_m_mov_estatico_es_cero(tmp_path):
    frames = _seq(tmp_path / "e", [(0, 0, 0)] * 5)
    assert mov.m_mov(frames) == 0.0


def test_m_mov_alterno_es_maximo(tmp_path):
    frames = _seq(tmp_path / "a", [(0, 0, 0), (255, 255, 255)] * 3)
    assert mov.m_mov(frames) == 255.0


def test_m_mov_menos_de_dos_frames_es_cero(tmp_path):
    frames = _seq(tmp_path / "u", [(10, 10, 10)])
    assert mov.m_mov(frames) == 0.0
    assert mov.m_mov([]) == 0.0


def test_trampas_u7b_separan_movimiento_de_estatico(tmp_path):
    mov_seq, est_seq = mov.trampas_mov(tmp_path / "trampas")
    assert len(mov_seq) == 8 and len(est_seq) == 8
    with Image.open(mov_seq[0]) as im:
        assert im.size == (1280, 720)
    m_mov = mov.m_mov(mov_seq)
    m_est = mov.m_mov(est_seq)
    assert m_mov >= mov.U7B_MOV_MIN, m_mov
    assert m_est <= mov.U7B_ESTATICO_MAX, m_est
    assert m_mov > m_est


def test_s_mov_clampa_en_rango():
    assert mov.s_mov(0.952) == 1.0
    assert mov.s_mov(0.046) == 0.092
    assert mov.s_mov(0.25) == 0.5
    assert mov.s_mov(0.0) == 0.0
    assert mov.s_mov(-1.0) == 0.0


def test_score_b2_hibrido_formula_ratificada():
    assert mov.score_b2_hibrido(1.0, 0.8, 0.6) == 0.85
    assert mov.score_b2_hibrido(0.0, 1.0, 1.0) == 0.5
    assert mov.score_b2_hibrido(0.092, 0.3096, 0.45) == 0.2359


def test_gate_u4p_con_datos_reales_y_bordes():
    ok, detalle = mov.gate_u4p(0.952, 0.046)
    assert ok, detalle
    assert mov.gate_u4p(0.19, 0.046)[0] is False
    assert mov.gate_u4p(0.20, 0.05)[0] is True
    assert mov.gate_u4p(0.30, 0.20)[0] is False
    assert mov.gate_u4p(0.952, 0.16)[0] is False
    assert mov.gate_u4p(None, 0.046)[0] is False
    assert mov.gate_u4p(0.952, None)[0] is False


def test_gate_u7b_ok_y_falla():
    assert mov.gate_u7b(1.42, 0.0)[0] is True
    assert mov.gate_u7b(0.10, 0.0)[0] is False
    assert mov.gate_u7b(1.42, 0.06)[0] is False
    assert mov.gate_u7b(None, 0.0)[0] is False


def test_gate_u3h_estabilidad_hibrida():
    e1 = {"V": 0.6, "A": 0.8, "error": None}
    e2 = {"V": 0.7, "A": 0.7, "error": None}
    ok, detalle = h18.gate_u3h(e1, e2, 0.75, 0.75)
    assert ok, detalle
    assert h18.gate_u3h(e1, e2, 0.75, 0.90)[0] is False
    assert h18.gate_u3h(e1, {"V": 0.2, "A": 0.7}, 0.75, 0.75)[0] is False
    assert h18.gate_u3h({"error": "x"}, e2, 0.75, 0.75)[0] is False


def test_gates_h18_exigen_u7a_y_u7b():
    assert h18.LLAMADAS_MAX == 8
    seis = {k: {"ok": True, "detalle": ""} for k in ("U1", "U2", "U3",
                                                     "U4", "U5", "U6")}
    assert base.gates_todos_ok(seis, h18.GATES_H18) is False
    siete = dict(seis, U7a={"ok": True, "detalle": ""})
    assert base.gates_todos_ok(siete, h18.GATES_H18) is False
    ocho = dict(siete, U7b={"ok": True, "detalle": ""})
    assert base.gates_todos_ok(ocho, h18.GATES_H18) is True


def test_score_final_h18_usa_score_b2_hibrido():
    gates = {k: {"ok": True, "detalle": ""} for k in h18.GATES_H18}
    b1 = {"BUILD": 1.0, "M_B1": 0.8333}
    e_def = {"Score_B2": 0.85}
    esperado = base.juez_b2.score_completo(1.0, 0.8333, 0.85)
    assert base.calcular_score_final(gates, b1, e_def,
                                     h18.GATES_H18) == esperado
    gates["U4"] = {"ok": False, "detalle": ""}
    assert base.calcular_score_final(gates, b1, e_def,
                                     h18.GATES_H18) is None
