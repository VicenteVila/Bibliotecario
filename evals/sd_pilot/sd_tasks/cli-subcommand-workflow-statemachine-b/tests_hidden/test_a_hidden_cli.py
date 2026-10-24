"""Tests ocultos: main (exit codes, streams, formato final)."""
import io

from stockcli import main
from stockcli.models import ITEMS, Item

EJEMPLO = (
    Item("A-1", 5, "OK"),
    Item("B-2", 9, "LOW"),
)


def _run(argv, items=EJEMPLO):
    out, err = io.StringIO(), io.StringIO()
    code = main(argv, items=items, stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def test_main_report_exit_cero_y_nueva_final():
    code, out, err = _run(["report", "--top", "1"])
    assert code == 0
    assert out == "TOTAL 2\nB-2 9 LOW\n"
    assert err == ""


def test_main_report_items_por_defecto():
    code, out, _ = _run(["report"], items=ITEMS)
    assert code == 0
    assert out.startswith("TOTAL 10\nPIN-077 200 OK\n")
    assert out.count("\n") == 11


def test_main_error_uso_exit_dos_y_stderr_prefijado():
    code, out, err = _run(["report", "--zzz", "1"])
    assert code == 2
    assert out == ""
    assert err == "error: unknown flag: --zzz\n"


def test_main_error_comando_desconocido():
    code, out, err = _run(["bogus"])
    assert code == 2
    assert out == ""
    assert err == "error: unknown command: 'bogus'\n"


def test_main_argv_vacia():
    code, out, err = _run([])
    assert code == 2
    assert out == ""
    assert err == "error: missing command\n"


def test_main_list_sigue_funcionando():
    code, out, err = _run(["list", "--status", "OK"])
    assert code == 0
    assert out == "A-1 5 OK\n"
    assert err == ""


def test_main_count_sigue_funcionando():
    code, out, _ = _run(["count"])
    assert code == 0
    assert out == "COUNT 2\n"


def test_main_report_con_todos_los_flags():
    code, out, _ = _run(
        ["report", "--status", "OK", "--min-qty", "4", "--top", "1"], items=EJEMPLO
    )
    assert code == 0
    assert out == "TOTAL 1\nA-1 5 OK\n"
