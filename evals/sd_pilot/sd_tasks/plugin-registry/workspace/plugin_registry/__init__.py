"""Registro de plugins con hooks y resolución de dependencias."""
from .errors import (
    DependencyCycleError,
    DuplicatePluginError,
    MissingDependencyError,
)
from .plugin import PluginSpec
from .registry import PluginRegistry

__all__ = [
    "PluginSpec",
    "PluginRegistry",
    "DuplicatePluginError",
    "MissingDependencyError",
    "DependencyCycleError",
]
