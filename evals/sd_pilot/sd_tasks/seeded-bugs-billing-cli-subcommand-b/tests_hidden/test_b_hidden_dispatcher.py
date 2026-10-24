"""Tests ocultos: semántica de report (filtro, orden, top, total)."""
from stockcli.dispatcher import dispatch
from stockcli.formatter import format_result
from stockcli.models import ITEMS, Item
from stockcli.parser import parse

EJEMPLO = (
    Item("A-1", 5, "OK"),
    Item("B-2", 9, "LOW"),
    Item("C-3", 5, "OUT"),
)


def test_report_items_por_defecto_orden_completo():
    kind, payload = dispatch(parse(["report"]), list(ITEMS))
    assert kind == "report"
    assert payload.total == 10
    assert [it.sku for it in payload.rows] == [
        "PIN-077",
        "TORN-001",
        "BOX-001",
        "CLAV-011",
        "BOX-002",
        "CIN-001",
        "TORN-002",
        "LIJA-003",
        "CLAV-010",
        "PIN-078",
    ]


def test_report_formato_completo_items_por_defecto():
    texto = format_result(dispatch(parse(["report"]), list(ITEMS)))
    assert texto == (
        "TOTAL 10\n"
        "PIN-077 200 OK\n"
        "TORN-001 120 OK\n"
        "BOX-001 60 OK\n"
        "CLAV-011 45 OK\n"
        "BOX-002 17 OK\n"
        "CIN-001 17 LOW\n"
        "TORN-002 8 LOW\n"
        "LIJA-003 3 LOW\n"
        "CLAV-010 0 OUT\n"
        "PIN-078 0 OUT"
    )


def test_report_empate_qty_desempata_por_sku_ascendente():
    items = [
        Item("ZZ-9", 5, "OK"),
        Item("AA-1", 5, "OK"),
        Item("MM-5", 5, "OK"),
    ]
    _, payload = dispatch(parse(["report"]), items)
    assert [it.sku for it in payload.rows] == ["AA-1", "MM-5", "ZZ-9"]


def test_report_orden_independiente_del_orden_de_entrada():
    items = list(EJEMPLO)
    inversa = list(reversed(EJEMPLO))
    _, payload_a = dispatch(parse(["report"]), items)
    _, payload_b = dispatch(parse(["report"]), inversa)
    assert payload_a.rows == payload_b.rows


def test_report_filtro_status():
    kind, payload = dispatch(parse(["report", "--status", "OUT"]), list(ITEMS))
    assert payload.total == 2
    assert [it.sku for it in payload.rows] == ["CLAV-010", "PIN-078"]
    assert format_result((kind, payload)) == "TOTAL 2\nCLAV-010 0 OUT\nPIN-078 0 OUT"


def test_report_filtro_min_qty():
    _, payload = dispatch(parse(["report", "--min-qty", "50"]), list(ITEMS))
    assert payload.total == 3
    assert [it.sku for it in payload.rows] == ["PIN-077", "TORN-001", "BOX-001"]


def test_report_filtros_status_y_min_qty_se_acumulan():
    _, payload = dispatch(
        parse(["report", "--status", "OK", "--min-qty", "50"]), list(ITEMS)
    )
    assert payload.total == 3
    _, payload2 = dispatch(
        parse(["report", "--status", "LOW", "--min-qty", "50"]), list(ITEMS)
    )
    assert payload2.total == 0


def test_report_top_no_cambia_total():
    _, payload = dispatch(parse(["report", "--top", "2"]), list(ITEMS))
    assert payload.total == 10
    assert [it.sku for it in payload.rows] == ["PIN-077", "TORN-001"]


def test_report_top_mayor_que_numero_de_filas():
    _, payload = dispatch(parse(["report", "--top", "50"]), list(EJEMPLO))
    assert payload.total == 3
    assert len(payload.rows) == 3


def test_report_sin_resultados_solo_total_cero():
    kind, payload = dispatch(
        parse(["report", "--status", "OUT", "--min-qty", "1"]), list(ITEMS)
    )
    assert payload.total == 0
    assert payload.rows == ()
    assert format_result((kind, payload)) == "TOTAL 0"


def test_report_min_qty_en_borde_incluye_igual():
    items = [Item("X-1", 7, "OK"), Item("X-2", 6, "OK"), Item("X-3", 8, "OK")]
    _, payload = dispatch(parse(["report", "--min-qty", "7"]), items)
    assert payload.total == 2
    assert [it.sku for it in payload.rows] == ["X-3", "X-1"]


def test_report_top_y_filtro_combinados():
    _, payload = dispatch(
        parse(["report", "--status", "LOW", "--top", "1"]), list(ITEMS)
    )
    assert payload.total == 3
    assert [it.sku for it in payload.rows] == ["CIN-001"]


def test_report_rows_es_tupla_inmutable():
    _, payload = dispatch(parse(["report"]), list(EJEMPLO))
    assert isinstance(payload.rows, tuple)


def test_list_sigue_dando_una_linea_por_item():
    kind, payload = dispatch(parse(["list"]), list(EJEMPLO))
    assert kind == "list"
    assert format_result((kind, payload)) == "A-1 5 OK\nB-2 9 LOW\nC-3 5 OUT"


def test_list_filtrado_por_status():
    kind, payload = dispatch(parse(["list", "--status", "OK"]), list(EJEMPLO))
    assert format_result((kind, payload)) == "A-1 5 OK"


def test_list_vacio_es_empty():
    kind, payload = dispatch(parse(["list", "--status", "OUT"]), list(EJEMPLO[:1]))
    assert format_result((kind, payload)) == "EMPTY"


def test_count_con_y_sin_filtro():
    assert dispatch(parse(["count"]), list(EJEMPLO)) == ("count", 3)
    assert dispatch(parse(["count", "--status", "OK"]), list(EJEMPLO)) == (
        "count",
        1,
    )


def test_dispatch_no_command_es_typeerror():
    import pytest

    with pytest.raises(TypeError):
        dispatch("report", list(EJEMPLO))
