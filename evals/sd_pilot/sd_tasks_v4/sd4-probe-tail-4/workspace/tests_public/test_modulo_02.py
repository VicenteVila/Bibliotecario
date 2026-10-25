from facturacion import modulo_02 as m


def test_primero_02():
    assert m.consultar("C02-0001") == {"grupo": "B", "valor": 239}
