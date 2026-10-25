"""Tests públicos de la fachada logística."""

import pytest
from logistica.models import Envio
from logistica.service import Cotizador


def _cotizador() -> Cotizador:
    return Cotizador(Envio(15, 0, 0, express=True))


def test_base():
    assert _cotizador().base() == 800


def test_recargos():
    assert _cotizador().recargos() == 400


def test_total():
    assert _cotizador().total() == 1200


def test_procesar():
    resultado = _cotizador().procesar()
    assert resultado.base == 800
    assert resultado.total == 1200


def test_peso_negativo():
    with pytest.raises(ValueError, match="peso invalido"):
        Cotizador(Envio(-1, 0, 0)).base()
