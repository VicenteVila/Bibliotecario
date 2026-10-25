import pytest
from procesos import proceso_06 as m


def test_inicio_06():
    e = m.crear()
    assert e["estado"] == "nuevo"
    assert e["historial"] == []


def test_camino_feliz_06():
    e = m.crear()
    for evento, estado in [("validar", "validado"), ("pagar", "pagado"),
                           ("enviar", "enviado"), ("entregar", "entregado")]:
        m.transitar(e, evento)
        assert e["estado"] == estado
    assert m.resumen(e) == {"estado": "entregado", "pasos": 4, "cancelado": False}


def test_cancelacion_06():
    e = m.crear()
    m.transitar(e, "cancelar")
    assert e["estado"] == "cancelado"
    assert m.resumen(e)["cancelado"] is True


def test_cancelacion_pagado_06():
    e = m.crear()
    m.transitar(e, "validar")
    m.transitar(e, "pagar")
    m.transitar(e, "cancelar")
    assert e["estado"] == "cancelado"


def test_evento_invalido_06():
    e = m.crear()
    with pytest.raises(ValueError):
        m.transitar(e, "entregar")
