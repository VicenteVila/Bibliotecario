"""Tests ocultos: parser (report, errores exactos, normalización)."""
import pytest
from stockcli import Command, UsageError, parse


def test_parse_report_vacio_devuelve_opciones_vacias():
    assert parse(["report"]) == Command("report", {})


def test_parse_report_llaves_con_guion_bajo():
    cmd = parse(["report", "--min-qty", "5", "--top", "2"])
    assert cmd.options == {"min_qty": 5, "top": 2}


def test_parse_flag_igual_valor_inline():
    cmd = parse(["report", "--min-qty=7", "--status=LOW"])
    assert cmd.options == {"min_qty": 7, "status": "LOW"}


def test_parse_solo_top():
    cmd = parse(["report", "--top", "1"])
    assert cmd.options == {"top": 1}


def test_parse_top_uno_es_valido():
    assert parse(["report", "--top", "1"]).options == {"top": 1}


def test_parse_min_qty_cero_es_valido():
    assert parse(["report", "--min-qty", "0"]).options == {"min_qty": 0}


def test_parse_status_invalido_report():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--status", "Z"])
    assert str(exc.value) == "invalid status: 'Z' (expected OK|LOW|OUT)"


def test_parse_status_invalido_tambien_en_list():
    with pytest.raises(UsageError) as exc:
        parse(["list", "--status", "ROJO"])
    assert str(exc.value) == "invalid status: 'ROJO' (expected OK|LOW|OUT)"


def test_parse_min_qty_negativo():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--min-qty", "-1"])
    assert str(exc.value) == "min-qty must be >= 0"


def test_parse_top_cero():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--top", "0"])
    assert str(exc.value) == "top must be >= 1"


def test_parse_top_negativo():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--top", "-3"])
    assert str(exc.value) == "top must be >= 1"


def test_parse_integer_invalido_min_qty():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--min-qty", "abc"])
    assert str(exc.value) == "invalid integer for --min-qty: 'abc'"


def test_parse_integer_invalido_top():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--top", "1.5"])
    assert str(exc.value) == "invalid integer for --top: '1.5'"


def test_parse_integer_invalido_vacio():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--top", ""])
    assert str(exc.value) == "invalid integer for --top: ''"


def test_parse_flag_desconocido_mensaje_exacto():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--orden", "asc"])
    assert str(exc.value) == "unknown flag: --orden"


def test_parse_flag_sin_valor_al_final():
    with pytest.raises(UsageError) as exc:
        parse(["report", "--status"])
    assert str(exc.value) == "flag requires a value: --status"


def test_parse_top_como_flag_de_list():
    with pytest.raises(UsageError) as exc:
        parse(["list", "--top", "2"])
    assert str(exc.value) == "unknown flag: --top"


def test_parse_argv_vacio():
    with pytest.raises(UsageError) as exc:
        parse([])
    assert str(exc.value) == "missing command"


def test_parse_comando_desconocido():
    with pytest.raises(UsageError) as exc:
        parse(["restock"])
    assert str(exc.value) == "unknown command: 'restock'"


def test_parse_token_posicional_inesperado():
    with pytest.raises(UsageError) as exc:
        parse(["report", "extra"])
    assert str(exc.value) == "unexpected argument: 'extra'"


def test_parse_valor_con_igual_puede_contener_guiones():
    cmd = parse(["report", "--status=OUT"])
    assert cmd.options == {"status": "OUT"}
