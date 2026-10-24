"""Tests ocultos: integración con el consumidor existente (CoordinadorSala)."""

from agenda.consumidor import CoordinadorSala
from agenda.modelo import Intervalo


def test_consumidor_determinista_repetible():
    coordinador = CoordinadorSala(1)
    datos = [Intervalo("b", 0, 5), Intervalo("a", 0, 5)]
    plan1 = coordinador.programar(datos, desde=0, hasta=24)
    plan2 = coordinador.programar(datos, desde=0, hasta=24)
    assert plan1 == plan2


def test_consumidor_ventana_excluye():
    coordinador = CoordinadorSala(1)
    plan = coordinador.programar([Intervalo("a", 0, 5)], desde=10, hasta=20)
    assert plan.rechazados[0].motivo == "fuera_de_ventana"
    assert coordinador.resumen(plan)["asignados"] == 0


def test_consumidor_orden_de_asignacion_por_decision():
    coordinador = CoordinadorSala(1)
    plan = coordinador.programar(
        [Intervalo("z", 0, 5), Intervalo("y", 0, 5)], desde=0, hasta=24
    )
    assert [a.intervalo.identificador for a in plan.asignaciones] == ["y"]


def test_consumidor_resumen_claves_exactas():
    coordinador = CoordinadorSala(1)
    plan = coordinador.programar(
        [Intervalo("a", 0, 5), Intervalo("b", 0, 5)], desde=0, hasta=24
    )
    resumen = coordinador.resumen(plan)
    assert set(resumen) == {"ocupacion_maxima", "asignados", "rechazados"}
    assert resumen == {"ocupacion_maxima": 1, "asignados": 1, "rechazados": 1}


def test_consumidor_adyacentes_ocupan_la_misma_sala():
    coordinador = CoordinadorSala(1)
    plan = coordinador.programar(
        [Intervalo("a", 0, 5), Intervalo("b", 5, 10)], desde=0, hasta=24
    )
    assert coordinador.resumen(plan) == {
        "ocupacion_maxima": 1,
        "asignados": 2,
        "rechazados": 0,
    }
