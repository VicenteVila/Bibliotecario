"""Tests ocultos: registro de plugins (API, errores, hooks)."""
import pytest

from plugin_registry import (
    DependencyCycleError,
    DuplicatePluginError,
    MissingDependencyError,
    PluginRegistry,
    PluginSpec,
)
from plugin_registry import plugin as plugin_mod


def test_spec_normaliza_dependencies_a_tuple():
    spec = PluginSpec("a", dependencies=["x", "y"])
    assert spec.dependencies == ("x", "y")
    assert isinstance(spec.dependencies, tuple)


def test_spec_dependencies_como_str_lanza_typeerror():
    with pytest.raises(TypeError):
        PluginSpec("a", dependencies="x")


def test_spec_nombre_vacio_lanza_typeerror():
    with pytest.raises(TypeError):
        PluginSpec("")


def test_spec_hooks_none_se_convierte_en_dict_vacio():
    spec = PluginSpec("a", hooks=None)
    assert spec.hooks == {}


def test_duplicate_error_lleva_atributo_name():
    reg = PluginRegistry()
    reg.register(PluginSpec("duplicado"))
    with pytest.raises(DuplicatePluginError) as exc:
        reg.register(PluginSpec("duplicado"))
    assert exc.value.name == "duplicado"


def test_get_desconocido_es_keyerror_con_nombre():
    reg = PluginRegistry()
    with pytest.raises(KeyError) as exc:
        reg.get("fantasma")
    assert "fantasma" in str(exc.value)


def test_names_refleja_registros_posteriores():
    reg = PluginRegistry()
    reg.register(PluginSpec("uno"))
    reg.register(PluginSpec("dos"))
    assert reg.names() == ["uno", "dos"]


def test_register_invalido_lanza_typeerror():
    reg = PluginRegistry()
    with pytest.raises(TypeError):
        reg.register("no-soy-spec")
    with pytest.raises(TypeError):
        reg.register(None)


def test_emit_omite_plugins_sin_hook():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", hooks={"on_stop": lambda: "a"}))
    reg.register(PluginSpec("b"))
    assert reg.emit("on_stop") == ["a"]
    assert reg.emit("on_start") == []


def test_emit_pasa_kwargs_a_los_hooks():
    reg = PluginRegistry()
    capturas = []

    def hook(**kwargs):
        capturas.append(kwargs)
        return kwargs["valor"]

    reg.register(PluginSpec("a", hooks={"h": hook}))
    reg.register(PluginSpec("b", hooks={"h": hook}))
    resultados = reg.emit("h", valor=42)
    assert resultados == [42, 42]
    assert capturas == [{"valor": 42}, {"valor": 42}]


def test_emit_orden_respeta_dependencias():
    reg = PluginRegistry()
    reg.register(PluginSpec("ui", dependencies=("core",), hooks={"h": lambda: "ui"}))
    reg.register(PluginSpec("core", hooks={"h": lambda: "core"}))
    assert reg.emit("h") == ["core", "ui"]


def test_dependencia_transitiva():
    reg = PluginRegistry()
    reg.register(PluginSpec("c", dependencies=("b",)))
    reg.register(PluginSpec("b", dependencies=("a",)))
    reg.register(PluginSpec("a"))
    assert reg.resolve() == ["a", "b", "c"]


def test_missing_dependency_atributos():
    reg = PluginRegistry()
    reg.register(PluginSpec("app", dependencies=("db",)))
    with pytest.raises(MissingDependencyError) as exc:
        reg.resolve()
    assert exc.value.dependent == "app"
    assert exc.value.missing == "db"


def test_self_dependency_es_ciclo():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", dependencies=("a",)))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    assert exc.value.cycle == ["a", "a"]


def test_ciclo_dos_nodos():
    reg = PluginRegistry()
    reg.register(PluginSpec("a", dependencies=("b",)))
    reg.register(PluginSpec("b", dependencies=("a",)))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    assert exc.value.cycle == ["a", "b", "a"]


def test_ciclo_tres_nodos_arranca_por_menor_nombre():
    reg = PluginRegistry()
    reg.register(PluginSpec("c", dependencies=("a",)))
    reg.register(PluginSpec("b", dependencies=("c",)))
    reg.register(PluginSpec("a", dependencies=("b",)))
    with pytest.raises(DependencyCycleError) as exc:
        reg.resolve()
    assert exc.value.cycle == ["a", "b", "c", "a"]


def test_resolve_es_determinista_entre_llamadas():
    reg = PluginRegistry()
    reg.register(PluginSpec("z", dependencies=("m",)))
    reg.register(PluginSpec("m"))
    reg.register(PluginSpec("h", priority=5))
    primera = reg.resolve()
    segunda = reg.resolve()
    assert primera == segunda == ["h", "m", "z"]
