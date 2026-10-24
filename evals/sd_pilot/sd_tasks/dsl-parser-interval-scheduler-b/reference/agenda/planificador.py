"""Planificador de intervalos con recursos. Implementación de referencia."""

from __future__ import annotations

from collections.abc import Iterable

from agenda.modelo import Asignacion, Intervalo, Plan, Rechazo
from agenda.recurso import Recurso


def planificar(
    intervalos: Iterable[Intervalo],
    recursos: Iterable[Recurso],
    ventana: tuple[int, int] | None = None,
) -> Plan:
    lista_recursos = list(recursos)
    lista_intervalos = list(intervalos)

    for recurso in lista_recursos:
        if recurso.capacidad < 1:
            raise ValueError(f"capacidad invalida: {recurso.nombre}")

    vistos: set[str] = set()
    for iv in lista_intervalos:
        if iv.identificador in vistos:
            raise ValueError(f"intervalo duplicado: {iv.identificador}")
        vistos.add(iv.identificador)

    for iv in lista_intervalos:
        if iv.inicio > iv.fin:
            raise ValueError(f"intervalo invertido: {iv.identificador}")
        if iv.prioridad < 0:
            raise ValueError(f"prioridad negativa: {iv.identificador}")

    recursos_ordenados = sorted(lista_recursos, key=lambda r: r.nombre)
    ocupados: dict[str, list[Intervalo]] = {
        r.nombre: [] for r in recursos_ordenados
    }

    elegibles: list[Intervalo] = []
    rechazados: list[Rechazo] = []
    for iv in lista_intervalos:
        if ventana is not None:
            desde, hasta = ventana
            if not (desde <= iv.inicio and iv.fin <= hasta):
                rechazados.append(Rechazo(iv, "fuera_de_ventana"))
                continue
        elegibles.append(iv)

    elegibles.sort(
        key=lambda iv: (-iv.prioridad, iv.inicio, iv.duracion, iv.identificador)
    )

    asignaciones: list[Asignacion] = []
    for iv in elegibles:
        colocado = False
        for recurso in recursos_ordenados:
            if _cabe(ocupados[recurso.nombre], iv, recurso.capacidad):
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
                nombre: _uso_maximo(cuartos)
                for nombre, cuartos in ocupados.items()
            },
        },
    )


def _cabe(
    ocupados: list[Intervalo], iv: Intervalo, capacidad: int
) -> bool:
    if iv.inicio == iv.fin:
        return True
    criticos = sorted(
        {p for otro in ocupados for p in (otro.inicio, otro.fin)
         if iv.inicio <= p < iv.fin}
        | {iv.inicio}
    )
    for punto in criticos:
        simultaneos = sum(
            1
            for otro in ocupados
            if otro.inicio <= punto < otro.fin
        )
        if simultaneos >= capacidad:
            return False
    return True


def _uso_maximo(asignados: list[Intervalo]) -> int:
    puntos = sorted({p for iv in asignados for p in (iv.inicio, iv.fin)})
    maximo = 0
    for punto in puntos:
        simultaneos = sum(
            1 for iv in asignados if iv.inicio <= punto < iv.fin
        )
        maximo = max(maximo, simultaneos)
    return maximo
