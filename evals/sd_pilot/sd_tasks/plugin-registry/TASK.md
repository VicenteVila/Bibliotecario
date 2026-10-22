# Tarea: plugin-registry — resolución de dependencias entre plugins

## Contexto

El paquete `plugin_registry` (en `workspace/plugin_registry/`) es un registro
de plugins pequeño pero en uso: los plugins se describen con `PluginSpec`,
se registran en un `PluginRegistry` y el sistema les emite hooks. Hoy el
orden de carga es un empate por prioridad/nombre e ignora las dependencias.

## Requisito

Extiende el registro para que el orden de carga sea un **orden topológico
de dependencias**, determinista, respetando la API existente (no rompas
firmas ni formatos de error ya publicados).

## Contrato exacto

### `plugin_registry.PluginSpec`

```python
PluginSpec(
    name: str,                              # cadena no vacía; si no, TypeError
    dependencies: Sequence[str] = (),       # se normaliza a tuple en __post_init__
    priority: int = 0,
    hooks: Mapping[str, Callable] | None = None,   # se normaliza a dict
)
```

`dependencies` recibido como `str` o `bytes` -> `TypeError`.

### `plugin_registry.PluginRegistry`

- `register(spec: PluginSpec) -> None`
  - Si `spec` no es `PluginSpec` -> `TypeError`.
  - Si el nombre ya está registrado -> `DuplicatePluginError` (atributo
    `.name`).
- `is_registered(name: str) -> bool`
- `get(name: str) -> PluginSpec` — clave inexistente -> `KeyError` estándar.
- `names() -> list[str]` — nombres **en orden de registro**.
- `resolve() -> list[str]` — orden de carga (ver reglas abajo).
- `emit(hook: str, **kwargs) -> list[object]` — recorre `resolve()` y, para
  cada plugin cuyo `hooks` contenga `hook`, llama `fn(**kwargs)`. Devuelve
  la lista de resultados **en orden de carga**, omitiendo los plugins sin
  ese hook.

### Reglas de `resolve()`

1. Toda dependencia se carga **antes** que el plugin que la declara
   (incluidas dependencias transitivas).
2. Entre los plugins cuyas dependencias ya están todos emitidos, se elige
   siempre el de clave `(-priority, name)`: **mayor `priority` primero**;
   a igual prioridad, **alfabético ascendente**. El resultado es
   determinista e independiente del orden de registro.
3. Dependencia no registrada -> `MissingDependencyError` con atributos
   `.dependent` (quien la declara) y `.missing` (la que falta).
4. Ciclo (incluida la auto-dependencia `name` -> `name`) ->
   `DependencyCycleError` con atributo `.cycle: list[str]`: los nombres del
   ciclo empezando y terminando por el mismo nodo, p. ej. `["a", "b", "a"]`.
   En un ciclo, el nodo de arranque es el **menor nombre** del ciclo; en
   cada paso se sigue la dependencia sin cumplir de **menor nombre**.
5. Los plugins **huérfanos** (sin dependencias y de los que no depende
   nadie) se incluyen en la lista resultante, regidos únicamente por la
   clave del punto 2.
6. `resolve()` puede llamarse cuantas veces se quiera; si se registra un
   plugin nuevo, la siguiente llamada refleja el estado actual.

## Fuera de alcance

No toques nada fuera de `workspace/plugin_registry/`.
