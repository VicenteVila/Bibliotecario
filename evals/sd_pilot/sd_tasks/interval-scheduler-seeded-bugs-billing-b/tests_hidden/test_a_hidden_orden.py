"""Tests ocultos: orden de decisión y desempates."""

from agenda.modelo import Intervalo
from agenda.planificador import planificar
from agenda.recurso import Recurso


def test_empate_de_prioridad_desempata_por_inicio():
    plan = planificar(
        [
            Intervalo("tardio", 10, 20, prioridad=2),
            Intervalo("temprano", 0, 30, prioridad=2),
        ],
        [Recurso("sala", 1)],
    )
    assert plan.asignaciones[0].intervalo.identificador == "temprano"
    assert plan.rechazados[0].intervalo.identificador == "tardio"


def test_empate_de_inicio_desempata_por_duracion():
    plan = planificar(
        [
            Intervalo("largo", 0, 30),
            Intervalo("corto", 0, 5),
        ],
        [Recurso("sala", 1)],
    )
    assert plan.asignaciones[0].intervalo.identificador == "corto"


def test_empate_total_desempata_por_identificador():
    plan = planificar(
        [
            Intervalo("b", 0, 5),
            Intervalo("a", 0, 5),
        ],
        [Recurso("sala", 1)],
    )
    assert plan.asignaciones[0].intervalo.identificador == "a"
    assert plan.rechazados[0].intervalo.identificador == "b"


def test_prioridad_domina_sobre_el_inicio():
    plan = planificar(
        [
            Intervalo("temprano-baja", 0, 100, prioridad=1),
            Intervalo("tardio-alta", 50, 60, prioridad=9),
        ],
        [Recurso("sala", 1)],
    )
    assert plan.asignaciones[0].intervalo.identificador == "tardio-alta"
    assert plan.rechazados[0].intervalo.identificador == "temprano-baja"


def test_orden_de_asignaciones_y_rechazados_es_orden_de_decision():
    plan = planificar(
        [
            Intervalo("z", 0, 10),
            Intervalo("y", 0, 10),
            Intervalo("x", 20, 30),
        ],
        [Recurso("sala", 1)],
    )
    assert [a.intervalo.identificador for a in plan.asignaciones] == ["y", "x"]
    assert [r.intervalo.identificador for r in plan.rechazados] == ["z"]


def test_asignacion_va_al_primer_recurso_libre_en_nombre_asc():
    plan = planificar(
        [Intervalo("a", 0, 5), Intervalo("b", 0, 5)],
        [Recurso("sala", 1), Recurso("cabinas", 1)],
    )
    por_recurso = {
        a.intervalo.identificador: a.recurso for a in plan.asignaciones
    }
    assert por_recurso == {"a": "cabinas", "b": "sala"}


def test_reutilizacion_de_recurso_en_el_tiempo():
    plan = planificar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 5, 10),
            Intervalo("c", 3, 7),
        ],
        [Recurso("sala", 1)],
    )
    assert [a.intervalo.identificador for a in plan.asignaciones] == ["a", "b"]
    assert plan.rechazados[0].intervalo.identificador == "c"
