"""Tests ocultos: validación de la API (mensajes exactos)."""
import pytest
from batchkit import BatchCoalescer, ManualClock


def test_window_negativa_es_valueerror():
    with pytest.raises(ValueError) as exc:
        BatchCoalescer(window=-1.0, clock=ManualClock())
    assert str(exc.value) == "window must be > 0"


def test_window_cero_es_valueerror():
    with pytest.raises(ValueError) as exc:
        BatchCoalescer(window=0, clock=ManualClock())
    assert str(exc.value) == "window must be > 0"


def test_window_bool_es_typeerror():
    with pytest.raises(TypeError) as exc:
        BatchCoalescer(window=True, clock=ManualClock())
    assert str(exc.value) == "window must be a number"


def test_window_str_es_typeerror():
    with pytest.raises(TypeError) as exc:
        BatchCoalescer(window="5", clock=ManualClock())
    assert str(exc.value) == "window must be a number"


def test_clock_no_callable_es_typeerror():
    with pytest.raises(TypeError) as exc:
        BatchCoalescer(window=1.0, clock=None)
    assert str(exc.value) == "clock must be callable"


def test_max_size_cero_es_valueerror():
    with pytest.raises(ValueError) as exc:
        BatchCoalescer(window=1.0, clock=ManualClock(), max_size=0)
    assert str(exc.value) == "max_size must be >= 1"


def test_max_size_negativo_es_valueerror():
    with pytest.raises(ValueError) as exc:
        BatchCoalescer(window=1.0, clock=ManualClock(), max_size=-2)
    assert str(exc.value) == "max_size must be >= 1"


def test_max_size_bool_es_typeerror():
    with pytest.raises(TypeError) as exc:
        BatchCoalescer(window=1.0, clock=ManualClock(), max_size=True)
    assert str(exc.value) == "max_size must be an integer"


def test_max_size_float_es_typeerror():
    with pytest.raises(TypeError) as exc:
        BatchCoalescer(window=1.0, clock=ManualClock(), max_size=2.5)
    assert str(exc.value) == "max_size must be an integer"


def test_add_item_no_str_es_typeerror():
    co = BatchCoalescer(window=1.0, clock=ManualClock())
    with pytest.raises(TypeError) as exc:
        co.add(42)
    assert str(exc.value) == "item must be str"


def test_add_item_bytes_es_typeerror():
    co = BatchCoalescer(window=1.0, clock=ManualClock())
    with pytest.raises(TypeError) as exc:
        co.add(b"a")
    assert str(exc.value) == "item must be str"


def test_add_ts_bool_es_typeerror():
    co = BatchCoalescer(window=1.0, clock=ManualClock())
    with pytest.raises(TypeError) as exc:
        co.add("a", ts=True)
    assert str(exc.value) == "ts must be a number"


def test_add_ts_str_es_typeerror():
    co = BatchCoalescer(window=1.0, clock=ManualClock())
    with pytest.raises(TypeError) as exc:
        co.add("a", ts="1")
    assert str(exc.value) == "ts must be a number"


def test_add_ts_int_es_valido():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a", ts=0)
    reloj.advance(5.0)
    assert co.poll() == [["a"]]


def test_typeerror_de_add_no_abre_lote():
    co = BatchCoalescer(window=1.0, clock=ManualClock())
    with pytest.raises(TypeError):
        co.add(7)
    assert co.pending == 0


def test_validaciones_del_constructor_en_orden():
    # window invalida se evalua antes que clock
    with pytest.raises(TypeError):
        BatchCoalescer(window="x", clock=None)
