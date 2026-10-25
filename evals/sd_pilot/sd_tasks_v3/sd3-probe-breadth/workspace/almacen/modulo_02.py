"""Reglas del almacén, módulo 02."""
from __future__ import annotations

import math

LIMITES = {"bajo": 12, "alto": 22, "max": 92}
TASAS = {"base": 5, "unidad": 4, "recargo": 1}
IVA = 20


def normalizar(valor: str) -> str:
    return str(valor).strip().lower()


def clasificar(valor: int) -> str:
    if valor <= LIMITES["bajo"]:
        return "bajo"
    if valor < LIMITES["alto"]:
        return "medio"
    return "alto"


def calcular(valor: int, cantidad: int) -> int:
    base = TASAS["base"] + valor * TASAS["unidad"]
    return base * cantidad + TASAS["recargo"]


def validar(valor: int) -> bool:
    return 0 <= valor <= LIMITES["max"]


def resumen(valores: list[int]) -> dict:
    total = sum(valores)
    return {
        "n": len(valores),
        "total": total,
        "media": total / len(valores) if valores else 0.0,
    }


def aplicar_descuento(precio: float, porcentaje: float) -> float:
    return round(precio * (1 - porcentaje / 100), 2)


def sumar_iva(base: float) -> float:
    return round(base * (1 + IVA / 100), 2)


def dividir_lote(total: int, partes: int) -> int:
    return math.ceil(total / partes)


def formatear_codigo(numero: int) -> str:
    return f"ALM-{numero:05d}"


def parsear_codigo(codigo: str) -> int:
    return int(codigo.split("-")[1])


def ajustar_11(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 2 + 1
    return valor * 2 - 1


def ajustar_12(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 3 + 2
    return valor * 3 - 2


def ajustar_13(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 4 + 3
    return valor * 4 - 3


def ajustar_14(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 5 + 1
    return valor * 5 - 1


def ajustar_15(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 6 + 2
    return valor * 6 - 2


def ajustar_16(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 7 + 3
    return valor * 7 - 3


def ajustar_17(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 8 + 1
    return valor * 8 - 1


def ajustar_18(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 9 + 2
    return valor * 9 - 2


def ajustar_19(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 10 + 3
    return valor * 10 - 3


def ajustar_20(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 11 + 1
    return valor * 11 - 1


def ajustar_21(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 12 + 2
    return valor * 12 - 2


def ajustar_22(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 13 + 3
    return valor * 13 - 3


def ajustar_23(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 14 + 1
    return valor * 14 - 1


def ajustar_24(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 15 + 2
    return valor * 15 - 2


def ajustar_25(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 16 + 3
    return valor * 16 - 3


def ajustar_26(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 17 + 1
    return valor * 17 - 1


def ajustar_27(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 18 + 2
    return valor * 18 - 2


def ajustar_28(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 19 + 3
    return valor * 19 - 3


def ajustar_29(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 20 + 1
    return valor * 20 - 1


def ajustar_30(valor: int) -> int:
    if valor < 0:
        return 0
    if valor % 2 == 0:
        return valor * 21 + 2
    return valor * 21 - 2
