"""Tests ocultos de la fachada de agenda."""

import pytest
from agenda.models import Cita
from agenda.service import Agenda


def test_sin_citas():
    agenda = Agenda([10], [])
    assert agenda.asignar().asignadas == ()
    assert agenda.pendientes() == 0


def test_cancelada():
    agenda = Agenda(
        [10], [Cita("a", 1, status="cancelled"), Cita("b", 2)]
    )
    assert agenda.asignar().asignadas == (("b", 10),)


def test_prioridad():
    agenda = Agenda(
        [10, 11], [Cita("z", 3), Cita("a", 1)]
    )
    assert agenda.asignar().asignadas[0] == ("a", 10)


def test_empate_id():
    agenda = Agenda(
        [10, 11], [Cita("b", 1), Cita("a", 1)]
    )
    assert agenda.asignar().asignadas == (
        ("a", 10),
        ("b", 11),
    )


def test_prioridad_invalida():
    with pytest.raises(ValueError, match="prioridad invalida: a"):
        Agenda([10], [Cita("a", 0)]).asignar()


def test_slot_duplicado():
    with pytest.raises(ValueError, match="slot duplicado: 10"):
        Agenda([10, 10], [Cita("a", 1)]).asignar()


def test_slot_negativo():
    with pytest.raises(ValueError, match="slot invalido: -1"):
        Agenda([-1], [Cita("a", 1)]).asignar()


def test_pendientes_con_faltantes():
    agenda = Agenda(
        [10], [Cita("a", 1), Cita("b", 2), Cita("c", 3)]
    )
    assert agenda.pendientes() == 2


def test_slots_desordenados():
    agenda = Agenda([11, 10], [Cita("a", 1)])
    assert agenda.asignar().asignadas == (("a", 10),)


def test_procesar_coherente():
    agenda = Agenda([10], [Cita("a", 1)])
    assert agenda.procesar() == agenda.asignar()
