"""Tests públicos de agenda médica."""

import pytest
from agenda.models import Cita
from agenda.service import procesar


def test_asigna_en_orden_de_slots():
    resultado = procesar([10, 11], [Cita("a", 1), Cita("b", 2)])
    assert resultado.asignadas == (("a", 10), ("b", 11))


def test_prioridad_manda_sobre_id():
    citas = [Cita("b", 2), Cita("a", 1)]
    resultado = procesar([10, 11], citas)
    assert resultado.asignadas == (("a", 10), ("b", 11))


def test_slots_desordenados():
    resultado = procesar([11, 10], [Cita("a", 1)])
    assert resultado.asignadas == (("a", 10),)


def test_sin_slots_suficientes():
    resultado = procesar([10], [Cita("a", 1), Cita("b", 2)])
    assert resultado.pendientes == 1


def test_id_duplicado():
    with pytest.raises(ValueError, match="cita duplicada: a"):
        procesar([10, 11], [Cita("a", 1), Cita("a", 2)])


def test_slot_negativo():
    with pytest.raises(ValueError, match="slot invalido: -1"):
        procesar([-1], [Cita("a", 1)])
