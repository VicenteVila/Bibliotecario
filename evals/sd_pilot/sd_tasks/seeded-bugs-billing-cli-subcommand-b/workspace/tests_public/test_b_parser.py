"""Tests públicos: parser de la CLI."""
import pytest
from stockcli import Command, UsageError, parse


def test_parse_report_basico_sin_flags():
    cmd = parse(["report"])
    assert cmd == Command("report", {})


def test_parse_list_con_status_sigue_funcionando():
    cmd = parse(["list", "--status", "LOW"])
    assert cmd == Command("list", {"status": "LOW"})


def test_parse_report_con_todos_los_flags():
    cmd = parse(["report", "--status", "OK", "--min-qty", "10", "--top", "3"])
    assert cmd == Command("report", {"status": "OK", "min_qty": 10, "top": 3})


def test_parse_flag_desconocido_es_usage_error():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--orden", "asc"])
    assert "unknown flag" in str(exc.value)
