"""Tests puros de SD-4 (HITO24): fixtures, QA, lock y gates. Sin LLM."""
from __future__ import annotations

from pathlib import Path

from evals.sd_pilot import sd4_sens, sd4_tasks


def test_probe_ids_y_sin_fase2() -> None:
    assert sd4_tasks.SD4_PROBE_TASK_IDS == [
        "sd4-probe-tail-2",
        "sd4-probe-tail-4",
        "sd4-probe-tail-24",
    ]
    assert sd4_tasks.SD4_DEV_TASK_IDS == []
    assert sd4_tasks.SD4_TEST_TASK_IDS == []
    assert sd4_tasks.SD4_TASK_IDS == sd4_tasks.SD4_PROBE_TASK_IDS


def test_lint_limpio() -> None:
    assert sd4_tasks.lint_tasks() == []


def test_qa_referencia_y_workspace() -> None:
    qa = sd4_tasks.qa_all()
    assert len(qa) == 3
    for item in qa:
        assert item["ok"] is True
        assert item["ref_score"] == 100.0
        assert item["ref_public"]["failed"] == 0
        assert item["ref_public"]["errors"] == 0
        assert item["empty_score"] < 100.0
        assert (
            item["empty_public"]["failed"] + item["empty_public"]["errors"]
        ) > 0


def test_cola_fuera_del_inline_y_dentro_de_lectura() -> None:
    for tid in sd4_tasks.SD4_PROBE_TASK_IDS:
        n = sd4_tasks.SD4_MODULE_COUNTS[tid]
        for i in range(1, n + 1):
            path = (
                sd4_tasks.task_dir(tid)
                / "workspace"
                / _paquete(tid)
                / f"modulo_{i:02d}.py"
            )
            text = path.read_text(encoding="utf-8")
            assert 6000 < len(text) < 8000
            assert text.index("TABLA_EXTRA") > 6000
            assert text.rstrip().endswith("TABLA_EXTRA = {")


def _paquete(tid: str) -> str:
    return {
        "sd4-probe-tail-2": "catalogo",
        "sd4-probe-tail-4": "facturacion",
        "sd4-probe-tail-24": "inventario",
    }[tid]


def _cells(a1: list[float], a5: list[float], *, writes: int = 2) -> dict:
    tasks = ["t1", "t2", "t3"]
    cells = {}
    for i, tid in enumerate(tasks):
        cells[f"A1_{tid}"] = {
            "score": a1[i],
            "writes": 0,
            "turns": 1,
            "usage": {"total_tokens": 1000, "calls": 1,
                      "prompt_tokens": 900, "completion_tokens": 100},
        }
        cells[f"A5_{tid}"] = {
            "score": a5[i],
            "writes": writes,
            "turns": 6,
            "usage": {"total_tokens": 1000, "calls": 3,
                      "prompt_tokens": 800, "completion_tokens": 200},
        }
    return cells


def _matrix(a1: list[float], a5: list[float]) -> dict:
    tasks = ["t1", "t2", "t3"]
    return {
        "A1": dict(zip(tasks, a1, strict=True)),
        "A5": dict(zip(tasks, a5, strict=True)),
    }


def test_gates_verdes() -> None:
    ev = sd4_sens.probe_gates(
        _matrix([0, 0, 0], [100, 100, 50]), _cells([0, 0, 0], [100, 100, 50]),
        ["t1", "t2", "t3"],
    )
    assert ev["cumple"] is True
    assert all(g["ok"] for g in ev["gates"].values())
    assert ev["A5_ge_80"] == 2
    assert ev["A5_writes"] == 3


def test_gates_a1_saturado_falla_r2() -> None:
    ev = sd4_sens.probe_gates(
        _matrix([100, 100, 100], [100, 100, 100]),
        _cells([100, 100, 100], [100, 100, 100]),
        ["t1", "t2", "t3"],
    )
    assert ev["cumple"] is False
    assert ev["gates"]["R2"]["ok"] is False


def test_gates_sin_escrituras_falla_r4() -> None:
    ev = sd4_sens.probe_gates(
        _matrix([0, 0, 0], [100, 100, 50]),
        _cells([0, 0, 0], [100, 100, 50], writes=0),
        ["t1", "t2", "t3"],
    )
    assert ev["cumple"] is False
    assert ev["gates"]["R4"]["ok"] is False


def test_gates_techo_falla_r5() -> None:
    cells = _cells([0, 0, 0], [100, 100, 50])
    for cell in cells.values():
        cell["usage"]["total_tokens"] = 100_000
    ev = sd4_sens.probe_gates(
        _matrix([0, 0, 0], [100, 100, 50]), cells, ["t1", "t2", "t3"],
        techo=250_000,
    )
    assert ev["cumple"] is False
    assert ev["gates"]["R5"]["ok"] is False


def test_lock_ida_y_vuelta(tmp_path: Path) -> None:
    target = sd4_tasks.write_lock(tmp_path / "SD4_PROBE_LOCK.json")
    assert sd4_tasks.verify_lock(target) == []
    data = target.read_text(encoding="utf-8")
    assert '"task_count": 3' in data
    assert "sd4-probe-tail-24" in data
