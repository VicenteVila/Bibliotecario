"""HITO17 — tests puros del prefiltro Opción B y de la trampa U7.

Sin red, sin motor: Pillow escribe PNGs de prueba, la rúbrica de la
trampa se valida con el validador congelado y los gates se alimentan
con dicts sintéticos.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals" / "preflight"
for _p in (str(ROOT), str(PREFLIGHT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import juez_b2
import prefiltro_b2
import run_fase2_b2 as base
import run_fase2_b2_h17 as h17

RUB = juez_b2.cargar_rubrica("platformer-juego")
RUB_T = juez_b2.cargar_rubrica("grounding-trampa")


def _plano(tmp_path: Path, color=(0, 0, 0), name="plano.png") -> Path:
    p = tmp_path / name
    Image.new("RGB", (64, 36), color).save(p)
    return p


def _con_contenido(tmp_path: Path) -> Path:
    p = tmp_path / "contenido.png"
    im = Image.new("RGB", (64, 36), (0, 0, 0))
    ImageDraw.Draw(im).rectangle([8, 8, 30, 24], fill=(255, 255, 0))
    im.save(p)
    return p


def test_frame_plano_es_color_uniforme(tmp_path):
    assert prefiltro_b2.frame_plano(_plano(tmp_path, (0, 0, 0)))
    assert prefiltro_b2.frame_plano(_plano(tmp_path, (32, 32, 64)))


def test_frame_con_un_sprite_no_es_plano(tmp_path):
    assert not prefiltro_b2.frame_plano(_con_contenido(tmp_path))


def test_analizar_exige_todos_los_frames_planos(tmp_path):
    plano = _plano(tmp_path)
    contenido = _con_contenido(tmp_path)
    r = prefiltro_b2.analizar([plano, plano])
    assert r["sin_contenido"] is True and r["planos"] == 2
    r = prefiltro_b2.analizar([plano, contenido])
    assert r["sin_contenido"] is False and r["planos"] == 1
    assert prefiltro_b2.analizar([])["sin_contenido"] is False


def test_anular_tiene_forma_de_juez_y_puntua_cero():
    r = prefiltro_b2.anular(RUB, "motivo de prueba")
    assert set(r["items"]) == {it["id"] for it in RUB["items"]}
    assert all(v["score"] == 0.0 and v["justificacion"]
               for v in r["items"].values())
    assert r["intentos"] == 0
    cats = juez_b2.agregar(r, RUB)
    assert cats["Score_B2"] == 0.0 and cats["D"] == 0.0


def test_caso_anulado_pasa_gate_u2_sin_llamadas(tmp_path):
    frames = [_plano(tmp_path, name=f"f{i}.png") for i in range(3)]
    llamadas: list[int] = []
    tokens: list[int] = []
    caso = h17._eval("negro", RUB, frames, llamadas, tokens)
    assert llamadas == [0] and tokens == [0]
    assert caso["prefiltro"]["sin_contenido"] is True
    assert caso["intentos"] == 0
    ok, detalle = base.gate_u2(caso, RUB)
    assert ok, detalle


def test_trampa_u7_determinista(tmp_path):
    con, sin = h17.frames_trampa(tmp_path / "trampa")
    assert con.exists() and sin.exists()
    with Image.open(con) as im:
        assert im.size == (1280, 720)
    assert not prefiltro_b2.frame_plano(con)
    assert prefiltro_b2.frame_plano(sin)


def test_gate_u7_separa_juez_honesto_de_caucho():
    honesto = {"Score_B2": 1.0}
    vacio = {"Score_B2": 0.0}
    assert h17.gate_u7(honesto, vacio)[0] is True
    # juez caucho: puntua el vacio alto (fallo de grounding medido en H16)
    caucho = {"Score_B2": 1.0}
    vacio_caucho = {"Score_B2": 0.7762}
    assert h17.gate_u7(caucho, vacio_caucho)[0] is False
    # el pintado tambien exige ≥0.5
    flojo = {"Score_B2": 0.3}
    assert h17.gate_u7(flojo, vacio)[0] is False
    # error en cualquiera de los dos
    assert h17.gate_u7({"error": "x"}, vacio)[0] is False
    assert h17.gate_u7(honesto, {"error": "x"})[0] is False


def test_mini_rubrica_de_trampa_es_valida():
    assert len(RUB_T["items"]) == 3
    assert RUB_T["pesos"] == juez_b2.PESOS
    assert juez_b2.validar_rubrica(RUB_T) == []


def test_gates_h17_exige_tambien_u7():
    seis = {k: {"ok": True, "detalle": ""} for k in base.GATES_ESPERADOS}
    assert base.gates_todos_ok(seis) is True
    assert base.gates_todos_ok(seis, h17.GATES_H17) is False
    siete = dict(seis, U7={"ok": True, "detalle": ""})
    assert base.gates_todos_ok(siete, h17.GATES_H17) is True
    b1 = {"BUILD": 1.0, "M_B1": 0.5}
    e_def = {"Score_B2": 0.5}
    assert base.calcular_score_final(seis, b1, e_def, h17.GATES_H17) is None
    esperado = juez_b2.score_completo(1.0, 0.5, 0.5)
    assert base.calcular_score_final(siete, b1, e_def,
                                     h17.GATES_H17) == esperado


def test_peor_caso_de_llamadas_no_excede_u6():
    """negro anulado 0 + cinco evaluaciones × ≤2 intentos = 10 = máximo."""
    assert 0 + 5 * 2 <= base.LLAMADAS_MAX
