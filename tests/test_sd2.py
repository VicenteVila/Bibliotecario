"""Tests puros del vertical slice SD-2 (HITO22), sin LLM."""

from evals.sd_pilot.sd2_tasks import (
    SD2_DEV_TASK_IDS,
    SD2_TASK_IDS,
    SD2_TEST_TASK_IDS,
    lint_tasks,
    qa_all,
    task_dir,
)


def test_slice_declara_dev_y_test_disjuntos():
    assert set(SD2_DEV_TASK_IDS).isdisjoint(SD2_TEST_TASK_IDS)
    assert set(SD2_DEV_TASK_IDS) | set(SD2_TEST_TASK_IDS) == set(SD2_TASK_IDS)


def test_slice_lint_limpio():
    assert lint_tasks() == []


def test_slice_qa_build_ok():
    for resultado in qa_all():
        assert resultado["ok"] is True
        assert resultado["ref_score"] == 100.0
        assert resultado["ref_public"]["failed"] == 0
        assert resultado["empty_public"]["failed"] >= 1
        assert resultado["empty_score"] < 100.0


def test_hidden_y_reference_fuera_del_workspace():
    for task_id in SD2_TASK_IDS:
        workspace = task_dir(task_id) / "workspace"
        assert not (workspace / "tests_hidden").exists()
        assert not (workspace / "reference").exists()
