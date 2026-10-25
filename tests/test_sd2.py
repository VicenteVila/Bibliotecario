"""Tests puros del BUILD SD-2 (HITO22), sin LLM."""

from collections import Counter

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
