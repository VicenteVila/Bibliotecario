"""Tests ocultos: ventana temporal y cierres por reloj."""
from batchkit import BatchCoalescer, ManualClock


def test_ventana_exacta_cierra():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")
    reloj.advance(5.0)
    assert co.poll() == [["a"]]


def test_un_tick_antes_de_la_ventana_no_cierra():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")
    reloj.advance(4.999)
    assert co.poll() == []
    assert co.pending == 1


def test_poll_vacio_devuelve_lista_vacia():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=1.0, clock=reloj)
    assert co.poll() == []


def test_flush_vacio_devuelve_lista_vacia():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=1.0, clock=reloj)
    assert co.flush() == []


def test_ts_none_usa_el_reloj_inyectado():
    reloj = ManualClock(100.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")
    reloj.advance(5.0)
    assert co.poll() == [["a"]]


def test_ts_explicito_no_resetea_first_ts():
    reloj = ManualClock(10.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a", ts=0.0)          # first_ts=0
    co.add("b", ts=9.0)          # no toca first_ts
    reloj.advance(4.0)           # now=14; 14-0>=5
    assert co.poll() == [["a", "b"]]


def test_ts_stale_no_acelera_la_ventana():
    reloj = ManualClock(10.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")                  # first_ts=10
    co.add("b", ts=0.0)          # ts pasado: no cambia first_ts
    reloj.advance(2.0)           # now=12; 12-10=2<5
    assert co.poll() == []
    reloj.advance(3.0)           # now=15; 15-10=5>=5
    assert co.poll() == [["a", "b"]]


def test_ts_futuro_no_cierra():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a", ts=100.0)
    reloj.advance(50.0)          # now=50; 50-100<0
    assert co.poll() == []


def test_varios_cierres_por_ventana_en_un_solo_poll():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=3.0, clock=reloj, max_size=1)
    co.add("a")                  # listo por max_size
    co.add("b")                  # listo por max_size
    assert co.poll() == [["a"], ["b"]]
    co.add("c")
    reloj.advance(3.0)
    assert co.poll() == [["c"]]


def test_max_size_y_ventana_en_un_mismo_poll_orden_fifo():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj, max_size=2)
    co.add("a")
    co.add("b")                  # cerrado por tamaño -> listo
    co.add("c")                  # abierto
    reloj.advance(5.0)           # c por ventana -> listo detras de [a,b]
    assert co.poll() == [["a", "b"], ["c"]]


def test_poll_no_duplica_lotes():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=1.0, clock=reloj)
    co.add("a")
    reloj.advance(1.0)
    assert co.poll() == [["a"]]
    assert co.poll() == []


def test_max_size_uno_entrega_item_a_item():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=100.0, clock=reloj, max_size=1)
    co.add("a")
    co.add("b")
    co.add("c")
    assert co.poll() == [["a"], ["b"], ["c"]]
    assert co.pending == 0


def test_lote_abierto_nuevo_tras_max_size_tiene_su_propio_first_ts():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=10.0, clock=reloj, max_size=2)
    co.add("a")                  # abierto [a], first_ts=0
    reloj.advance(8.0)           # now=8
    co.add("b")                  # [a, b] alcanza max_size -> listo
    co.add("c")                  # abierto [c], first_ts=8
    reloj.advance(2.0)           # now=10; 10-8=2<10
    assert co.poll() == [["a", "b"]]
    reloj.advance(8.0)           # now=18; 18-8=10>=10
    assert co.poll() == [["c"]]


def test_flush_tras_poll_sin_duplicados_ni_vacios():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj)
    co.add("a")
    reloj.advance(5.0)
    assert co.poll() == [["a"]]
    co.add("b")
    assert co.flush() == [["b"]]
    assert co.flush() == []


def test_flush_entrega_listos_luego_abierto():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=10.0, clock=reloj, max_size=1)
    co.add("a")                  # listo por tamaño
    co.add("b")                  # abierto
    assert co.flush() == [["a"], ["b"]]
    assert co.pending == 0


def test_no_se_entregan_lotes_vacios():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=1.0, clock=reloj)
    assert co.flush() == []
    co.add("a")
    reloj.advance(1.0)
    assert co.poll() == [["a"]]
    assert co.flush() == []


def test_pending_tras_operaciones():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=5.0, clock=reloj, max_size=2)
    assert co.pending == 0
    co.add("a")
    assert co.pending == 1
    co.add("b")                  # cerrado por tamaño
    assert co.pending == 2
    assert co.poll() == [["a", "b"]]
    assert co.pending == 0
    co.add("c")
    co.add("d")                  # [c, d] alcanza max_size=2 -> listo
    assert co.flush() == [["c", "d"]]
    assert co.pending == 0


def test_items_dentro_del_lote_conservan_orden_de_insercion():
    reloj = ManualClock(0.0)
    co = BatchCoalescer(window=1.0, clock=reloj)
    for nombre in ("z", "m", "a"):
        co.add(nombre)
    reloj.advance(1.0)
    assert co.poll() == [["z", "m", "a"]]
