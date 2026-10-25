from catalogo import modulo_01 as m


def test_primero_01():
    assert m.consultar("C01-0001") == {"grupo": "B", "valor": 138}
