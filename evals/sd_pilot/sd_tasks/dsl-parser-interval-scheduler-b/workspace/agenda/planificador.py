"""Planificador de intervalos (implementación preliminar).

PRELIMINAR: greedy por orden alfabético de identificador, solape inclusivo y
sin validación completa. Debe reemplazarse por la semántica del contrato
(orden de decisión, semiabiertos, ventanas, validaciones y estadísticas).
"""

from __future__ import annotations

from collections.abc import Iterable

from agenda.modelo import Asignacion, Intervalo, Plan, Rechazo
from agenda.recurso import Recurso


def planificar(
    intervalos: Iterable[Intervalo],
    recursos: Iterable[Recurso],
    ventana: tuple[int, int] | None = None,
) -> Plan:
    lista_intervalos = sorted(intervalos, key=lambda iv: iv.identificador)
    lista_recursos = list(recursos)
    if not lista_intervalos:
        return Plan(
            asignaciones=(),
            rechazados=(),
            estadisticas={
                "asignados": 0,
                "rechazados": 0,
                "motivos": {},
                "uso_por_recurso": {r.nombre: 0 for r in lista_recursos},
            },
        )

    ocupados: dict[str, list[Intervalo]] = {r.nombre: [] for r in lista_recursos}
    asignaciones: list[Asignacion] = []
    rechazados: list[Rechazo] = []

    for iv in lista_intervalos:
        if ventana is not None:
            desde, hasta = ventana
            if not (desde <= iv.inicio and iv.inicio < hasta):
                rechazados.append(Rechazo(iv, "fuera_de_ventana"))
                continue
        colocado = False
        for recurso in sorted(lista_recursos, key=lambda r: r.nombre):
            if _cabe_inclusivo(ocupados[recurso.nombre], iv, recurso.capacidad):
                ocupados[recurso.nombre].append(iv)
                asignaciones.append(Asignacion(iv, recurso.nombre))
                colocado = True
                break
        if not colocado:
            rechazados.append(Rechazo(iv, "sin_recurso_disponible"))

    motivos: dict[str, int] = {}
    for rechazo in rechazados:
        motivos[rechazo.motivo] = motivos.get(rechazo.motivo, 0) + 1

    return Plan(
        asignaciones=tuple(asignaciones),
        rechazados=tuple(rechazados),
        estadisticas={
            "asignados": len(asignaciones),
            "rechazados": len(rechazados),
            "motivos": motivos,
            "uso_por_recurso": {
                nombre: len(cuartos) for nombre, cuartos in ocupados.items()
            },
        },
    )


def _cabe_inclusivo(
    ocupados: list[Intervalo], iv: Intervalo, capacidad: int
) -> bool:
    if capacidad <= 0:
        return False
    en_conflicto = 0
    for otro in ocupados:
        if iv.inicio <= otro.fin and otro.inicio <= iv.fin:
            en_conflicto += 1
    return en_conflicto < capacidad
