"""Errores del registro de plugins."""


class DuplicatePluginError(Exception):
    """Se intentó registrar un plugin con un nombre ya existente."""

    def __init__(self, name: str) -> None:
        super().__init__(f"plugin ya registrado: {name!r}")
        self.name = name


class MissingDependencyError(Exception):
    """Un plugin declara una dependencia que no está registrada."""

    def __init__(self, dependent: str, missing: str) -> None:
        super().__init__(
            f"el plugin {dependent!r} depende de {missing!r} que no está registrado"
        )
        self.dependent = dependent
        self.missing = missing


class DependencyCycleError(Exception):
    """Las dependencias contienen un ciclo."""

    def __init__(self, cycle: list[str]) -> None:
        super().__init__("ciclo de dependencias: " + " -> ".join(cycle))
        self.cycle = list(cycle)
