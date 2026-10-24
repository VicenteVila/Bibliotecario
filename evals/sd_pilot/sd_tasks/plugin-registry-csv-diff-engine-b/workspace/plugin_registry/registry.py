"""Registro de plugins."""
from __future__ import annotations

from .errors import DuplicatePluginError
from .plugin import PluginSpec
from .resolver import resolve_order


class PluginRegistry:
    """Almacena plugins y emite hooks en orden de carga."""

    def __init__(self) -> None:
        self._plugins: dict[str, PluginSpec] = {}

    def register(self, spec: PluginSpec) -> None:
        if not isinstance(spec, PluginSpec):
            raise TypeError("solo se pueden registrar PluginSpec")
        if spec.name in self._plugins:
            raise DuplicatePluginError(spec.name)
        self._plugins[spec.name] = spec

    def is_registered(self, name: str) -> bool:
        return name in self._plugins

    def get(self, name: str) -> PluginSpec:
        return self._plugins[name]

    def names(self) -> list[str]:
        """Nombres en orden de registro."""
        return list(self._plugins)

    def resolve(self) -> list[str]:
        """Orden determinista de carga de los plugins."""
        return resolve_order(self._plugins)

    def emit(self, hook: str, **kwargs: object) -> list[object]:
        """Llama al hook de cada plugin en orden de carga y colecta resultados."""
        results: list[object] = []
        for name in self.resolve():
            fn = self._plugins[name].hooks.get(hook)
            if fn is not None:
                results.append(fn(**kwargs))
        return results
