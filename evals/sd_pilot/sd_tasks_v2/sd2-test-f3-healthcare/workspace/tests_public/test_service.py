"""Tests públicos de la fachada de agenda."""

import pytest
from agenda.models import Cita
from agenda.service import Agenda


def _agenda() -> Agenda:
    return Agenda([10, 11], [Cita("b", 2), Cita("a", 1)])


def test_asignar():
    assert _agenda().asignar().asignadas == (
        ("a", 10),
        ("b", 11),
    )


def test_pendientes():
    assert _agenda().pendientes() == 0


def test_procesar():
    resultado = _agenda().procesar()
    assert resultado.asignadas[0] == ("a", 10)


def test_sin_slots():
    agenda = Agenda([], [Cita("a", 1)])
    assert agenda.procesar().pendientes == 1


def test_id_duplicado():
    with pytest.raises(ValueError, match="cita duplicada: a"):
        Agenda([10], [Cita("a", 1), Cita("a", 2)]).asignar()
