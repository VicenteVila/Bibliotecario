"""Tests públicos: asignación básica, rechazo por solape y uso del consumidor."""

from agenda.consumidor import CoordinadorSala
from agenda.modelo import Intervalo
from agenda.planificador import planificar
from agenda.recurso import Recurso


def test_asignacion_simple_no_solapada():
    sala = Recurso("sala", 1)
    plan = planificar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 5, 10),
        ],
        [sala],
    )
    assert len(plan.asignaciones) == 2
    assert plan.estadisticas["asignados"] == 2
    assert plan.rechazados == ()


def test_solape_con_capacidad_uno_rechaza():
    sala = Recurso("sala", 1)
    plan = planificar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 3, 8),
        ],
        [sala],
    )
    assert len(plan.asignaciones) == 1
    assert len(plan.rechazados) == 1
    assert plan.rechazados[0].motivo == "sin_recurso_disponible"


def test_ventana_vacia_produce_plan_en_cero():
    sala = Recurso("sala", 2)
    plan = planificar([], [sala], ventana=(0, 100))
    assert plan.asignaciones == ()
    assert plan.rechazados == ()
    assert plan.estadisticas["asignados"] == 0
    assert plan.estadisticas["rechazados"] == 0
    assert plan.estadisticas["motivos"] == {}


def test_consumidor_de_sala_resumen():
    coordinador = CoordinadorSala(2)
    plan = coordinador.programar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 2, 6),
            Intervalo("c", 10, 12),
        ],
        desde=0,
        hasta=24,
    )
    resumen = coordinador.resumen(plan)
    assert resumen["asignados"] == 3
    assert resumen["rechazados"] == 0
    assert resumen["ocupacion_maxima"] == 2
