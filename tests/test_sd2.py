"""Tests puros del BUILD SD-2 (HITO22), sin LLM."""

from collections import Counter

from evals.sd_pilot import run_sd2, sd2_sens
from evals.sd_pilot.sd2_tasks import (
    SD2_DEV_TASK_IDS,
    SD2_TASK_DOMAIN,
    SD2_TASK_FAMILY,
    SD2_TASK_IDS,
    SD2_TEST_TASK_IDS,
    lint_tasks,
    qa_all,
    task_dir,
    verify_lock,
)


def test_sd2_declara_24_tareas_y_split():
    assert len(SD2_TASK_IDS) == 24
    assert len(SD2_DEV_TASK_IDS) == 12
    assert len(SD2_TEST_TASK_IDS) == 12
    assert set(SD2_DEV_TASK_IDS).isdisjoint(SD2_TEST_TASK_IDS)
    assert set(SD2_DEV_TASK_IDS) | set(SD2_TEST_TASK_IDS) == set(SD2_TASK_IDS)


def test_sd2_familias_y_dominios():
    assert Counter(SD2_TASK_FAMILY.values()) == {
        "F1": 8,
        "F2": 8,
        "F3": 8,
    }
    assert Counter(SD2_TASK_DOMAIN.values()) == {
        "inventory": 3,
        "reservations": 3,
        "payroll": 3,
        "routing": 3,
        "banking": 3,
        "healthcare": 3,
        "logistics": 3,
        "media": 3,
    }


def test_sd2_lint_limpio():
    assert lint_tasks() == []


def test_sd2_lock_correcto():
    assert verify_lock() == []


def test_sd2_qa_build_ok():
    for resultado in qa_all():
        assert resultado["ok"] is True
        assert resultado["ref_score"] == 100.0
        assert resultado["ref_public"]["failed"] == 0
        assert resultado["empty_public"]["failed"] >= 1
        assert resultado["empty_score"] < 100.0


def test_sd2_hidden_y_reference_fuera_del_workspace():
    for task_id in SD2_TASK_IDS:
        workspace = task_dir(task_id) / "workspace"
        assert not (workspace / "tests_hidden").exists()
        assert not (workspace / "reference").exists()


def _celdas(matrix, tasks, coste=1000):
    celdas = {}
    for variante, fila in matrix.items():
        for tarea in tasks:
            celdas[f"{variante}_{tarea}"] = {
                "score": fila[tarea],
                "model": sd2_sens.MODEL,
                "max_turns": sd2_sens.MAX_TURNS,
                "usage": {"total_tokens": coste},
            }
    return celdas


def test_calibracion_c1_c4_pasa():
    tareas = list(SD2_DEV_TASK_IDS)
    matriz = {
        "A1": {t: 70.0 for t in tareas},
        "A5": {t: 55.0 for t in tareas},
    }
    ev = sd2_sens.calibration_gates(
        matriz, _celdas(matriz, tareas), tareas
    )
    assert ev["cumple"] is True
    assert ev["valid_tasks"] == 12
    assert ev["diferencia_A1_A5"] == 15.0


def test_calibracion_falla_si_no_hay_ventana():
    tareas = list(SD2_DEV_TASK_IDS)
    matriz = {
        "A1": {t: 60.0 for t in tareas},
        "A5": {t: 55.0 for t in tareas},
    }
    ev = sd2_sens.calibration_gates(
        matriz, _celdas(matriz, tareas), tareas
    )
    assert ev["gates"]["C3"]["ok"] is False
    assert ev["cumple"] is False


def _matriz_oficial():
    tareas = list(SD2_TEST_TASK_IDS)
    base = [60.0, 65.0, 55.0, 70.0, 50.0, 75.0,
            45.0, 80.0, 40.0, 85.0, 35.0, 90.0]
    return {
        "A1": {t: v for t, v in zip(tareas, base)},
        "A2": {t: v - 5 for t, v in zip(tareas, base)},
        "A3": {t: v - 10 for t, v in zip(tareas, base)},
        "A4": {t: v - 15 for t, v in zip(tareas, base)},
        "A5": {t: v - 25 for t, v in zip(tareas, base)},
    }


def test_oficial_u1_u10_pasa():
    tareas = list(SD2_TEST_TASK_IDS)
    matriz = _matriz_oficial()
    ev = sd2_sens.official_gates(
        matriz,
        _celdas(matriz, tareas),
        lock_ok=True,
        harness_card_ok=True,
    )
    assert ev["cumple"] is True
    assert ev["n_sens_finitos"] >= 6
    assert ev["n_sens_positivos"] >= 6
    assert ev["gates"]["U8"]["ok"] is True


def test_oficial_falla_u8_sin_headroom():
    tareas = list(SD2_TEST_TASK_IDS)
    matriz = _matriz_oficial()
    matriz["A1"] = {t: 90.0 for t in tareas}
    ev = sd2_sens.official_gates(
        matriz,
        _celdas(matriz, tareas),
        lock_ok=True,
        harness_card_ok=True,
    )
    assert ev["gates"]["U8"]["ok"] is False
    assert ev["cumple"] is False


def test_presupuesto_calibracion_y_oficial_caben():
    cal = run_sd2._proyeccion(
        12, 12, run_sd2.CAL_VARIANTS, run_sd2.CAL_TECHO
    )
    oficial = run_sd2._proyeccion(
        12, 12, run_sd2.OFICIAL_VARIANTS, run_sd2.OFICIAL_TECHO
    )
    assert cal["cabe"] is True
    assert oficial["cabe"] is True
    assert oficial["total"] > cal["total"]
