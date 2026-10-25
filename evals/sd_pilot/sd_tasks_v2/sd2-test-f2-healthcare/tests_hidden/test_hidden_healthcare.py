"""Tests ocultos de agenda médica."""

import pytest
from agenda.models import Cita
from agenda.service import procesar


def test_sin_citas():
    resultado = procesar([10, 11], [])
    assert resultado.asignadas == ()
    assert resultado.pendientes == 0


def test_sin_slots():
    resultado = procesar([], [Cita("a", 1)])
    assert resultado.asignadas == ()
    assert resultado.pendientes == 1


def test_cancelada_no_cuenta():
    citas = [Cita("a", 1, status="cancelled"), Cita("b", 2)]
    resultado = procesar([10], citas)
    assert resultado.asignadas == (("b", 10),)
    assert resultado.pendientes == 0


def test_prioridad_uno_primero():
    citas = [Cita("z", 3), Cita("a", 1)]
    resultado = procesar([10, 11], citas)
    assert resultado.asignadas[0] == ("a", 10)


def test_empate_por_id():
    citas = [Cita("b", 1), Cita("a", 1)]
    resultado = procesar([10, 11], citas)
    assert resultado.asignadas == (("a", 10), ("b", 11))


def test_prioridad_invalida_baja():
    with pytest.raises(ValueError, match="prioridad invalida: a"):
        procesar([10], [Cita("a", 0)])


def test_prioridad_invalida_alta():
    with pytest.raises(ValueError, match="prioridad invalida: a"):
        procesar([10], [Cita("a", 4)])


def test_slots_repetidos():
    with pytest.raises(ValueError, match="slot duplicado: 10"):
        procesar([10, 10], [Cita("a", 1)])


def test_mas_citas_que_slots():
    citas = [Cita("a", 1), Cita("b", 2), Cita("c", 3)]
    resultado = procesar([10, 11], citas)
    assert len(resultado.asignadas) == 2
    assert resultado.pendientes == 1


def test_asignacion_prioridad_tres():
    citas = [Cita("a", 3), Cita("b", 2), Cita("c", 1)]
    resultado = procesar([10, 11, 12], citas)
    assert resultado.asignadas == (
        ("c", 10),
        ("b", 11),
        ("a", 12),
    )


def test_slots_negativos_varios():
    with pytest.raises(ValueError, match="slot invalido: -2"):
        procesar([-2, 10], [Cita("a", 1)])


def test_cita_duplicada_con_cancelada():
    with pytest.raises(ValueError, match="cita duplicada: a"):
        procesar(
            [10],
            [Cita("a", 1), Cita("a", 2, status="cancelled")],
        )
