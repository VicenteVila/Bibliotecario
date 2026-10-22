"""Tests públicos: despacho y formato del comando report."""
from stockcli.dispatcher import dispatch
from stockcli.formatter import format_result
from stockcli.models import Item
from stockcli.parser import parse

EJEMPLO = (
    Item("A-1", 5, "OK"),
    Item("B-2", 9, "LOW"),
    Item("C-3", 5, "OUT"),
)


def test_report_total_y_filas_en_orden():
    result = dispatch(parse(["report"]), list(EJEMPLO))
    kind, payload = result
    assert kind == "report"
    assert payload.total == 3
    assert [it.sku for it in payload.rows] == ["B-2", "A-1", "C-3"]
    texto = format_result(result)
    assert texto == "TOTAL 3\nB-2 9 LOW\nA-1 5 OK\nC-3 5 OUT"


def test_report_top_recorta_filas():
    result = dispatch(parse(["report", "--top", "1"]), list(EJEMPLO))
    _, payload = result
    assert payload.total == 3
    assert [it.sku for it in payload.rows] == ["B-2"]
    assert format_result(result) == "TOTAL 3\nB-2 9 LOW"


def test_report_min_qty_filtra():
    result = dispatch(parse(["report", "--min-qty", "6"]), list(EJEMPLO))
    _, payload = result
    assert payload.total == 1
    assert format_result(result) == "TOTAL 1\nB-2 9 LOW"


def test_main_report_exit_cero_y_salida():
    import io

    from stockcli import main

    out, err = io.StringIO(), io.StringIO()
    code = main(["report"], items=EJEMPLO, stdout=out, stderr=err)
    assert code == 0
    assert out.getvalue() == "TOTAL 3\nB-2 9 LOW\nA-1 5 OK\nC-3 5 OUT\n"
    assert err.getvalue() == ""
