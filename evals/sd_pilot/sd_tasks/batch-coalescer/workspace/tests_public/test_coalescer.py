"""Tests públicos: BatchCoalescer con reloj manual."""
import pytest
from batchkit import BatchCoalescer, ManualClock


def test_ventana_basica_con_reloj_manual():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")
    reloj.advance(2.0)
    co.add("b")
    assert co.poll() == []
    reloj.advance(3.0)
    assert co.poll() == [["a", "b"]]
    assert co.pending == 0


def test_max_size_cierra_sin_esperar_la_ventana():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=100.0, clock=reloj, max_size=2)
    co.add("a")
    assert co.poll() == []
    co.add("b")
    assert co.poll() == [["a", "b"]]


def test_flush_entrega_el_lote_abierto():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=10.0, clock=reloj)
    co.add("x")
    assert co.flush() == [["x"]]
    assert co.flush() == []


def test_window_invalida_es_valueerror():
    with pytest.raises(ValueError):
        BatchCoalescer(window=0, clock=ManualClock())
