from __future__ import annotations

import json
from pathlib import Path

from evals.sd_pilot import sd3_sens, sd3_tasks
from evals.sd_pilot.run_sd3 import _proyeccion


def test_probe_tasks_declaradas_y_qa():
    assert sd3_tasks.SD3_PROBE_TASK_IDS == [
        "sd3-probe-breadth",
        "sd3-probe-runtime",
        "sd3-probe-contract",
    ]
    for tid in sd3_tasks.SD3_PROBE_TASK_IDS:
        assert sd3_tasks.task_dir(tid).is_dir()
        assert len(sd3_tasks.SD3_TASK_AXES[tid]) >= 2
    assert sd3_tasks.lint_tasks() == []
    qa = sd3_tasks.qa_all()
    assert all(item["ok"] for item in qa), qa


def test_lock_detecta_cambios(tmp_path: Path):
    target = tmp_path / "lock.json"
    sd3_tasks.write_lock(target)
    assert sd3_tasks.verify_lock(target) == []
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["task_count"] == 3
    assert data["split"]["probe_task_ids"] == sd3_tasks.SD3_PROBE_TASK_IDS
    data["files_sha256"]["inventado"] = "0" * 64
    target.write_text(json.dumps(data), encoding="utf-8")
    problems = sd3_tasks.verify_lock(target)
    assert any("inventado" in p for p in problems)


def test_proyeccion_probe_cabe_en_techo():
    payload = _proyeccion(12, 3, sd3_sens.PROBE_TECHO)
    assert payload["celdas"] == 6
    assert payload["cabe"] is True
    assert payload["total"] == 140_448


def _cells(scores_a1, scores_a5, *, writes=1, turns=5, tokens=1_000):
    cells = {}
    for i, score in enumerate(scores_a1):
        cells[f"A1_t{i}"] = {
            "score": score, "writes": 0, "turns": 1,
            "usage": {"total_tokens": 0},
        }
    for i, score in enumerate(scores_a5):
        cells[f"A5_t{i}"] = {
            "score": score, "writes": writes, "turns": turns,
            "usage": {"total_tokens": tokens},
        }
    return cells


def test_gates_probe_verdes():
    tasks = ["t0", "t1", "t2"]
    matrix = {"A1": dict(zip(tasks, [40, 60, 80])),
              "A5": dict(zip(tasks, [80, 90, 100]))}
    ev = sd3_sens.probe_gates(matrix, _cells([40, 60, 80], [80, 90, 100]), tasks)
    assert ev["cumple"] is True, ev["gates"]
    assert ev["A5_lt_100"] == 2
    assert ev["diferencia_A1_A5"] == 30.0


def test_gates_probe_falla_si_a1_satura():
    tasks = ["t0", "t1", "t2"]
    matrix = {"A1": dict(zip(tasks, [100, 100, 100])),
              "A5": dict(zip(tasks, [100, 100, 100]))}
    ev = sd3_sens.probe_gates(matrix, _cells([100, 100, 100], [100, 100, 100]), tasks)
    assert ev["cumple"] is False
    assert ev["gates"]["P2"]["ok"] is False
    assert ev["gates"]["P3"]["ok"] is False


def test_gates_probe_detecta_a5_atascada():
    tasks = ["t0", "t1", "t2"]
    matrix = {"A1": dict(zip(tasks, [40, 60, 80])),
              "A5": dict(zip(tasks, [80, 90, 100]))}
    cells = _cells([40, 60, 80], [80, 90, 100], writes=0, turns=12)
    ev = sd3_sens.probe_gates(matrix, cells, tasks)
    assert ev["gates"]["P4"]["ok"] is False


def test_gates_probe_detecta_infra_error():
    tasks = ["t0", "t1", "t2"]
    matrix = {
        "A1": dict(zip(tasks, [40, 60, 80])),
        "A5": dict(zip(tasks, [80, 90, 100])),
    }
    cells = _cells([40, 60, 80], [80, 90, 100])
    cells["A5_t1"]["infra_error"] = True
    ev = sd3_sens.probe_gates(matrix, cells, tasks)
    assert ev["gates"]["P1"]["ok"] is False
    assert ev["cumple"] is False
