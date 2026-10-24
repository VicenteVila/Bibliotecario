"""Tests ocultos: ventanas, validaciones y estadísticas."""

import pytest
from agenda.modelo import Intervalo
from agenda.planificador import planificar
from agenda.recurso import Recurso


def test_ventana_bordes_incluidos():
    plan = planificar(
        [Intervalo("a", 10, 20)],
        [Recurso("sala", 1)],
        ventana=(10, 20),
    )
    assert len(plan.asignaciones) == 1


def test_ventana_inicio_fuera():
    plan = planificar(
        [Intervalo("a", 9, 20)],
        [Recurso("sala", 1)],
        ventana=(10, 20),
    )
    assert plan.rechazados[0].motivo == "fuera_de_ventana"


def test_ventana_fin_fuera():
    plan = planificar(
        [Intervalo("a", 10, 21)],
        [Recurso("sala", 1)],
        ventana=(10, 20),
    )
    assert plan.rechazados[0].motivo == "fuera_de_ventana"


def test_estadisticas_conteo_de_motivos_mixtos():
    plan = planificar(
        [
            Intervalo("ok", 0, 5),
            Intervalo("fuera", -10, -5),
            Intervalo("solapado", 0, 5),
        ],
        [Recurso("sala", 1)],
        ventana=(0, 100),
    )
    assert plan.estadisticas["motivos"] == {
        "fuera_de_ventana": 1,
        "sin_recurso_disponible": 1,
    }
    assert plan.estadisticas["asignados"] == 1
    assert plan.estadisticas["rechazados"] == 2


def test_uso_por_recurso_incluye_recursos_sin_uso():
    plan = planificar(
        [Intervalo("a", 0, 5)],
        [Recurso("sala", 1), Recurso("cabinas", 1)],
    )
    assert plan.estadisticas["uso_por_recurso"] == {"cabinas": 1, "sala": 0}


def test_intervalo_invertido_es_valueerror():
    with pytest.raises(ValueError, match="intervalo invertido: a"):
        planificar([Intervalo("a", 10, 5)], [Recurso("sala", 1)])


def test_prioridad_negativa_es_valueerror():
    with pytest.raises(ValueError, match="prioridad negativa: a"):
        planificar([Intervalo("a", 0, 5, prioridad=-1)], [Recurso("sala", 1)])


def test_capacidad_invalida_es_valueerror():
    with pytest.raises(ValueError, match="capacidad invalida: sala"):
        planificar([Intervalo("a", 0, 5)], [Recurso("sala", 0)])


def test_intervalo_duplicado_es_valueerror():
    with pytest.raises(ValueError, match="intervalo duplicado: a"):
        planificar(
            [Intervalo("a", 0, 5), Intervalo("a", 10, 15)],
            [Recurso("sala", 1)],
        )


def test_lista_vacia_sin_recursos():
    plan = planificar([], [], ventana=None)
    assert plan.asignaciones == ()
    assert plan.rechazados == ()
    assert plan.estadisticas == {
        "asignados": 0,
        "rechazados": 0,
        "motivos": {},
        "uso_por_recurso": {},
    }
