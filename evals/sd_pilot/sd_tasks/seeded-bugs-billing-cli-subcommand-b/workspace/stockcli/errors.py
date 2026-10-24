"""Errores de la CLI de inventario."""


class UsageError(Exception):
    """Error de uso de la CLI (exit code 2)."""


class DataError(Exception):
    """Error de datos del inventario (exit code 1)."""
