"""Tests públicos: múltiples recursos y prioridades."""

from agenda.modelo import Intervalo
from agenda.planificador import planificar
from agenda.recurso import Recurso


def test_dos_recursos_admiten_solape():
    plan = planificar(
        [
            Intervalo("a", 0, 5),
            Intervalo("b", 0, 5),
        ],
        [Recurso("cabinas", 1), Recurso("sala", 1)],
    )
    assert len(plan.asignaciones) == 2
    recursos = sorted(a.recurso for a in plan.asignaciones)
    assert recursos == ["cabinas", "sala"]


def test_prioridad_alta_va_primero():
    plan = planificar(
        [
            Intervalo("comun", 0, 5, prioridad=1),
            Intervalo("urgente", 0, 5, prioridad=5),
        ],
        [Recurso("sala", 1)],
    )
    assert plan.asignaciones[0].intervalo.identificador == "urgente"
    assert plan.rechazados[0].intervalo.identificador == "comun"
