"""Tests públicos de la resolución de dependencias."""
import pytest

from plugin_registry import (
    DependencyCycleError,
    PluginRegistry,
    PluginSpec,
)


def test_resolve_cadena_de_dependencias():
    reg = PluginRegistry()
    reg.register(PluginSpec("app", dependencies=("db", "cache")))
    reg.register(PluginSpec("db", dependencies=("core",)))
    reg.register(PluginSpec("cache", dependencies=("core",)))
    reg.register(PluginSpec("core"))
    order = reg.resolve()
    assert order.index("core") < order.index("db")
    assert order.index("db") < order.index("app")
    assert order.index("cache") < order.index("app")
    assert sorted(order) == ["app", "cache", "core", "db"]


def test_resolve_ciclo_lanza_error():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", dependencies=("b",)))
    reg.register(PluginSpec("b", dependencies=("a",)))
    with pytest.raises(DependencyCycleError):
        reg.resolve()


def test_emit_llama_hooks_y_devuelve_resultados():
    reg = PluginRegistry()
    reg.register(PluginSpec("logger", priority=10, hooks={"on_start": lambda **kw: "log"}))
    reg.register(PluginSpec("core", hooks={"on_start": lambda **kw: "core"}))
    assert reg.emit("on_start") == ["log", "core"]
