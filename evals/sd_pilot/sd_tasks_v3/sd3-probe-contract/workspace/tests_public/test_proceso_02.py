from procesos import proceso_02 as m


def test_flujo_02():
    e = m.crear()
    if 2 == 1:
        m.transitar(e, "validar")
        assert e["estado"] == "validado"
    elif 2 == 2:
        m.transitar(e, "validar")
        m.transitar(e, "pagar")
        assert e["estado"] == "pagado"
    else:
        m.transitar(e, "validar")
        m.transitar(e, "pagar")
        m.transitar(e, "enviar")
        assert e["estado"] == "enviado"
        m.transitar(e, "entregar")
        assert e["estado"] == "entregado"
    assert m.resumen(e)["pasos"] >= 1
