"""Máquina de estados del proceso 04."""
from __future__ import annotations

ESTADOS = ("nuevo", "validado", "pagado", "enviado", "entregado", "cancelado")
TRANSICIONES = {
    "nuevo": {"validar": "validado", "cancelar": "cancelado"},
    "validado": {"pagar": "pagado", "cancelar": "cancelado"},
    "pagado": {"enviar": "enviado", "cancelar": "cancelado"},
    "enviado": {"entregar": "enviado"},
    "entregado": {},
    "cancelado": {},
}


def crear() -> dict:
    return {"estado": "nuevo", "historial": []}


def transitar(estado: dict, evento: str) -> dict:
    actual = estado["estado"]
    destino = TRANSICIONES[actual].get(evento)
    if destino is None:
        raise ValueError(f"evento inválido: {evento} en {actual}")
    estado["estado"] = destino
    estado["historial"].append(evento)
    return estado


def resumen(estado: dict) -> dict:
    return {
        "estado": estado["estado"],
        "pasos": len(estado["historial"]),
        "cancelado": estado["estado"] == "cancelado",
    }
