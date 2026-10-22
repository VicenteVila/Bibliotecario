"""Errores de la migración de configuraciones."""


class ConfigParseError(Exception):
    """El texto de entrada no es un config válido del formato declarado."""


class UnknownFormatError(Exception):
    """Extensión o nombre de formato desconocido."""

    def __init__(self, path: str) -> None:
        super().__init__(f"formato desconocido para: {path!r}")
        self.path = path


class ConfigValidationError(Exception):
    """El config no cumple el esquema. ``errors`` es la lista ordenada de fallos."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = list(errors)
