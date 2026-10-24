"""Tests ocultos: semiabiertos, capacidad y uso máximo por recurso."""

from agenda.modelo import Intervalo
from agenda.planificador import planificar
from agenda.recurso import Recurso


def test_intervalos_adyacentes_no_solapan():
    plan = planificar(
        [Intervalo("a", 0, 5), Intervalo("b", 5, 10)],
        [Recurso("sala", 1)],
    )
    assert len(plan.asignaciones) == 2
    assert plan.estadisticas["motivos"] == {}


def test_solape_parcial_real_sí_conflicta():
    plan = planificar(
        [Intervalo("a", 0, 5), Intervalo("b", 4, 10)],
        [Recurso("sala", 1)],
    )
    assert len(plan.asignaciones) == 1
    assert plan.rechazados[0].motivo == "sin_recurso_disponible"


def test_solape_en_un_punto_compartido():
    plan = planificar(
        [Intervalo("a", 0, 5), Intervalo("b", 4, 5)],
        [Recurso("sala", 1)],
    )
    assert len(plan.rechazados) == 1


def test_capacidad_dos_admite_dos_simultaneos():
    plan = planificar(
        [
            Intervalo("a", 0, 10),
            Intervalo("b", 0, 10),
            Intervalo("c", 0, 10),
        ],
        [Recurso("sala", 2)],
    )
    assert len(plan.asignaciones) == 2
    assert plan.rechazados[0].intervalo.identificador == "c"
    assert plan.estadisticas["uso_por_recurso"]["sala"] == 2


def test_uso_maximo_no_es_el_total_sino_el_simultaneo():
    plan = planificar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 1, 6),
            Intervalo("c", 7, 9),
        ],
        [Recurso("sala", 3)],
    )
    assert plan.estadisticas["uso_por_recurso"]["sala"] == 2


def test_duracion_cero_ocupa_ningun_instante():
    plan = planificar(
        [
            Intervalo("a", 0, 10),
            Intervalo("punto", 5, 5),
        ],
        [Recurso("sala", 1)],
    )
    assert len(plan.asignaciones) == 2
    assert plan.estadisticas["uso_por_recurso"]["sala"] == 1


def test_dos_duraciones_cero_en_el_mismo_instante():
    plan = planificar(
        [
            Intervalo("p1", 5, 5),
            Intervalo("p2", 5, 5),
        ],
        [Recurso("sala", 1)],
    )
    assert len(plan.asignaciones) == 2


def test_recursos_se_eligen_por_nombre_ascendente():
    plan = planificar(
        [Intervalo("a", 0, 5)],
        [Recurso("zeta", 1), Recurso("alfa", 1)],
    )
    assert plan.asignaciones[0].recurso == "alfa"
