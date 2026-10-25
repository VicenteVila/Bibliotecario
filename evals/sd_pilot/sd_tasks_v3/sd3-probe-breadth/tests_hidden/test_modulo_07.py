from almacen import modulo_07 as m


def test_normalizar_07():
    assert m.normalizar("  AbC ") == "abc"


def test_clasificar_07():
    assert m.clasificar(10) == "bajo"
    assert m.clasificar(11) == "medio"
    assert m.clasificar(22) == "alto"


def test_calcular_07():
    esperado = (6 + 4 * 3) * 3 + 2
    assert m.calcular(4, 3) == esperado


def test_validar_07():
    assert m.validar(0) is True
    assert m.validar(90) is True
    assert m.validar(91) is False
    assert m.validar(-1) is False


def test_resumen_07():
    assert m.resumen([2, 4]) == {"n": 2, "total": 6, "media": 3.0}
    assert m.resumen([]) == {"n": 0, "total": 0, "media": 0.0}


def test_descuento_07():
    assert m.aplicar_descuento(100, 15) == 85.0


def test_iva_07():
    assert m.sumar_iva(100) == round(100 * (1 + 20 / 100), 2)


def test_lote_07():
    assert m.dividir_lote(10, 3) == 4
    assert m.dividir_lote(9, 3) == 3


def test_formato_07():
    assert m.formatear_codigo(7) == "ALM-00007"
    assert m.parsear_codigo("ALM-00042") == 42


def test_ajustes_07():
    assert m.ajustar_11(2) == 5
    assert m.ajustar_11(3) == 5
    assert m.ajustar_12(2) == 8
    assert m.ajustar_13(2) == 11
    assert m.ajustar_14(2) == 11
    assert m.ajustar_15(2) == 14
    assert m.ajustar_16(2) == 17
    assert m.ajustar_17(2) == 17
    assert m.ajustar_18(2) == 20
    assert m.ajustar_19(2) == 23
    assert m.ajustar_20(2) == 23
    assert m.ajustar_21(2) == 26
    assert m.ajustar_22(2) == 29
    assert m.ajustar_23(2) == 29
    assert m.ajustar_24(2) == 32
    assert m.ajustar_25(2) == 35
    assert m.ajustar_26(2) == 35
    assert m.ajustar_27(2) == 38
    assert m.ajustar_28(2) == 41
    assert m.ajustar_29(2) == 41
    assert m.ajustar_30(2) == 44
    assert m.ajustar_11(-1) == 0
