"""Tests ocultos: reglas del orden topológico."""
import pytest

from plugin_registry import (
    DependencyCycleError,
    PluginRegistry,
    PluginSpec,
)
from plugin_registry.resolver import resolve_order


def test_huerfano_alta_prioridad_entrada_y_cadena_respetada():
    reg = PluginRegistry()
    reg.register(PluginSpec("solo", priority=100))
    reg.register(PluginSpec("app", dependencies=("core",)))
    reg.register(PluginSpec("core", priority=-10))
    order = reg.resolve()
    assert order.index("core") < order.index("app")
    assert order[0] == "solo"


def test_empate_prioridad_mayor_primero():
    reg = PluginRegistry()
    reg.register(PluginSpec("b", priority=1))
    reg.register(PluginSpec("a", priority=2))
    reg.register(PluginSpec("c", priority=1))
    assert reg.resolve() == ["a", "b", "c"]


def test_empate_total_orden_alfabetico():
    reg = PluginRegistry()
    reg.register(PluginSpec("gamma"))
    reg.register(PluginSpec("alfa"))
    reg.register(PluginSpec("beta"))
    assert reg.resolve() == ["alfa", "beta", "gamma"]


def test_orden_independiente_del_registro():
    reg1 = PluginRegistry()
    for name in ("app", "core", "mid"):
        deps = {"app": ("mid",), "mid": ("core",), "core": ()}[name]
        reg1.register(PluginSpec(name, dependencies=deps))
    reg2 = PluginRegistry()
    for name in ("core", "app", "mid"):
        deps = {"app": ("mid",), "mid": ("core",), "core": ()}[name]
        reg2.register(PluginSpec(name, dependencies=deps))
    assert reg1.resolve() == reg2.resolve() == ["core", "mid", "app"]


def test_diamante_orden_correcto():
    reg = PluginRegistry()
    reg.register(PluginSpec("top", dependencies=("izq", "der")))
    reg.register(PluginSpec("izq", dependencies=("base",)))
    reg.register(PluginSpec("der", dependencies=("base",)))
    reg.register(PluginSpec("base"))
    order = reg.resolve()
    assert order[0] == "base"
    assert order[-1] == "top"
    assert order.index("izq") < order.index("top")
    assert order.index("der") < order.index("top")


def test_dos_cadenas_independientes_entrelazadas_por_prioridad():
    reg = PluginRegistry()
    reg.register(PluginSpec("b2", dependencies=("b1",), priority=1))
    reg.register(PluginSpec("b1", priority=0))
    reg.register(PluginSpec("a2", dependencies=("a1",), priority=0))
    reg.register(PluginSpec("a1", priority=1))
    assert reg.resolve() == ["a1", "a2", "b1", "b2"]


def test_ciclo_rama_colgante_no_oculta_ciclo_real():
    reg = PluginRegistry()
    reg.register(PluginSpec("x", dependencies=("y",)))
    reg.register(PluginSpec("y", dependencies=("x",)))
    reg.register(PluginSpec("huerfano"))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    assert exc.value.cycle == ["x", "y", "x"]


def test_ciclo_con_dependencia_compartida_fuera_del_ciclo():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", dependencies=("base", "b")))
    reg.register(PluginSpec("b", dependencies=("base", "a")))
    reg.register(PluginSpec("base"))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    assert exc.value.cycle == ["a", "b", "a"]


def test_mensaje_de_ciclo_contiene_nodos():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", dependencies=("b",)))
    reg.register(PluginSpec("b", dependencies=("a",)))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    texto = str(exc.value)
    assert "a" in texto and "b" in texto


def test_resolve_order_acepta_dict_vacio():
    assert resolve_order({}) == []


def test_registro_posterior_se_refleja_en_resolve():
    reg = PluginRegistry()
    reg.register(PluginSpec("b", dependencies=("a",)))
    reg.register(PluginSpec("a"))
    primero = reg.resolve()
    reg.register(PluginSpec("z", priority=99))
    assert primero == ["a", "b"]
    assert reg.resolve() == ["z", "a", "b"]
