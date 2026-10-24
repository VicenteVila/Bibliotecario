"""Tests públicos del registro de plugins."""
import pytest

from plugin_registry import (
    DuplicatePluginError,
    PluginRegistry,
    PluginSpec,
)


def test_register_y_names_preserva_orden_de_registro():
    reg = PluginRegistry()
    reg.register(PluginSpec("beta"))
    reg.register(PluginSpec("alfa"))
    assert reg.names() == ["beta", "alfa"]
    assert reg.is_registered("beta")
    assert not reg.is_registered("nunca")


def test_register_duplicado_lanza_error():
    reg = PluginRegistry()
    reg.register(PluginSpec("a"))
    with pytest.raises(DuplicatePluginError) as exc:
        reg.register(PluginSpec("a"))
    assert exc.value.name == "a"


def test_get_devuelve_spec_o_keyerror():
    reg = PluginRegistry()
    spec = PluginSpec("a", dependencies=("b",), priority=3)
    reg.register(spec)
    assert reg.get("a") is spec
    with pytest.raises(KeyError):
        reg.get("zzz")


def test_register_no_plugin_spec_lanza_typeerror():
    reg = PluginRegistry()
    with pytest.raises(TypeError):
        reg.register({"name": "x"})
