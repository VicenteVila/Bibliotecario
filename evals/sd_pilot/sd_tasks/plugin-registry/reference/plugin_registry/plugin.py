"""Especificación de un plugin."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class PluginSpec:
    """Describe un plugin registrado en el :class:`PluginRegistry`.

    ``hooks`` mapea nombre de hook -> callable; el callable recibe los
    kwargs que se pasen a ``PluginRegistry.emit``.
    """

    name: str
    dependencies: tuple[str, ...] = ()
    priority: int = 0
    hooks: dict[str, Callable[..., object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise TypeError("el nombre del plugin debe ser una cadena no vacía")
        if isinstance(self.dependencies, (str, bytes)):
            raise TypeError("dependencies debe ser una secuencia de nombres")
        self.dependencies = tuple(self.dependencies)
        if self.hooks is None:
            self.hooks = {}
        else:
            self.hooks = dict(self.hooks)
