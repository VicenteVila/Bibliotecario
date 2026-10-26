"""HITO27 — tests puros del runner de transferencia H26-B Fase 2.

Sin red, sin LLM, sin DB real: solo prompts, briefing, gates y resumen.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "evals" / "preflight"
for _p in (str(ROOT), str(PREFLIGHT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import run_transfer_h26b as tr


def _skills(n: int = 14) -> list[tuple[str, str]]:
    return [
        (f"tech_skill_{i:02d}", f"principio {i} " + "x" * 400)
        for i in range(n)
    ]


def _cell(task: str, arm: str, score: float, main: bool = True, build: bool = True) -> dict:
    return {
        "task": task,
        "arm": arm,
        "main_gd": main,
        "suite": {"score": score, "build_ok": build},
    }


def _cells() -> list[dict]:
    cells = []
    for i, task in enumerate(tr.TASKS):
        cells.append(_cell(task, "control", float(i)))
        cells.append(_cell(task, "skills", float(i + 1)))
    return cells


def test_tasks_son_cuatro_y_existen_en_la_suite():
    textos = tr.load_task_texts()
    assert list(textos) == list(tr.TASKS)
    assert len(set(tr.TASKS)) == 4


def test_compact_recorta_y_colapsa_espacios():
    assert tr.compact("  a   b  ") == "a b"
    recortado = tr.compact("x" * 500)
    assert len(recortado) == tr.SKILL_CHARS
    assert recortado.endswith("...")


def test_briefing_es_determinista_y_cabe():
    skills = _skills()
    a = tr.build_briefing(skills)
    b = tr.build_briefing(list(reversed(skills)))
    assert a == b
    assert a.count("### tech_skill_") == 14
    assert len(a) < 6000


def test_prompt_control_no_lleva_skills_y_skills_si():
    texto = "Crea un juego de prueba."
    briefing = tr.build_briefing(_skills())
    control = tr.build_prompt(texto, "control", briefing)
    skills = tr.build_prompt(texto, "skills", briefing)
    assert tr.BRIEF_MARK not in control
    assert "tech_skill_" not in control
    assert tr.BRIEF_MARK in skills
    assert "tech_skill_00" in skills
    assert texto in control and texto in skills


def test_tpm_y_no_fuga_con_prompts_reales():
    textos = tr.load_task_texts()
    briefing = tr.build_briefing(_skills())
    cells = tr.build_cells(textos, briefing)
    assert len(cells) == 8
    assert tr.check_tpm(cells)[0]
    assert tr.validate_no_leak(briefing, cells, textos)[0]


def test_no_fuga_detecta_id_de_tarea_en_briefing():
    textos = tr.load_task_texts()
    briefing = tr.build_briefing(_skills()) + tr.TASKS[0]
    cells = tr.build_cells(textos, briefing)
    ok, detalle = tr.validate_no_leak(briefing, cells, textos)
    assert not ok
    assert "prohibidos" in detalle


def test_resumen_delta_y_gates():
    cells = _cells()
    resumen = tr.summarize(cells)
    assert resumen["por_brazo"]["control"]["media"] == 1.5
    assert resumen["por_brazo"]["skills"]["media"] == 2.5
    assert resumen["delta_global_skills_control"] == 1.0
    gates = tr.evaluate_gates(
        cells, 8, 8, 1000, (True, "ok"), (True, "ok"), resumen
    )
    assert all(g["ok"] for g in gates.values())


def test_gates_detectan_main_o_build_insuficiente():
    cells = _cells()
    cells[0]["main_gd"] = False
    cells[1]["suite"]["build_ok"] = False
    resumen = tr.summarize(cells)
    gates = tr.evaluate_gates(
        cells, 8, 8, 1000, (True, "ok"), (True, "ok"), resumen
    )
    assert not gates["T2"]["ok"]
    assert gates["T3"]["ok"]  # 7/8 sigue ≥6
