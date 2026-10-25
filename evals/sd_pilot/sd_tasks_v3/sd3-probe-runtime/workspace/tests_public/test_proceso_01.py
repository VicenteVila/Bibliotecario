from flujo import proceso_01 as m


def test_flujo_01():
    e = m.crear()
    if 1 == 1:
        m.transitar(e, "validar")
        assert e["estado"] == "validado"
    elif 1 == 2:
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
