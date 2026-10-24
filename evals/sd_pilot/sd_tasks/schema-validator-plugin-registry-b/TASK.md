# Tarea B: schema-validator-plugin-registry-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: schema-validator — validador de esquemas con paths exactos

## Rol

Eres ingeniero de backend en un servicio que valida payloads JSON. El paquete
`jsonval` (en `workspace/jsonval/`) trae las utilidades de path
(`paths.py`) y de clasificación de tipos (`types.py`), ya completas y
congeladas. Falta el validador propiamente dicho: `jsonval/validator.py`.

## Requisito

Implementa `jsonval.validator.validate` para que cumpla exactamente el
contrato siguiente, **usando** `paths.py` y `types.py` (no dupliques sus
funciones). Determinismo total: el orden de los mensajes es fijo.

## Contrato exacto de `jsonval.validator.validate`

```python
def validate(data: object, schema: dict) -> list[str]
```

- `schema` no es `dict` -> `TypeError` con mensaje exacto
  `schema must be dict`.
- Devuelve la **lista acumulada** de mensajes de error; `[]` si `data`
  cumple `schema`. Cada mensaje tiene la forma `"{path}: {detalle}"`.

### Path (definido ya en `paths.py`; aquí queda documentado)

- Raíz: `$`.
- Clave que cumple `[A-Za-z_][A-Za-z0-9_]*` -> `$.a.b` (notación punto).
- Cualquier otra clave -> notación corchete con comillas:
  `$["mi clave"]`; dentro se escapan `\` -> `\\`, `"` -> `\"`,
  `\n` -> `\n`, `\t` -> `\t`, `\r` -> `\r` (las dos literales).
- Índice de array -> `[i]` pegado: `$.tags[0]`, `$.a[2].c`.

### Tipos soportados (`schema["type"]`)

`object`, `array`, `string`, `number`, `integer`, `boolean`, `null`.
La coincidencia la hace `types.matches`; el nombre del tipo del dato en
los mensajes lo da `types.type_name`.

Reglas de coincidencia (ya implementadas; sepáralas mentalmente):
`bool` **no** es `number` ni `integer`; `2.0` **no** es `integer`; `2` sí
es `number`. Un schema **sin** `type` no valida tipo (pero sí puede
llevar `enum`).

### Orden de recorrido y detalle de mensajes

Por cada nodo, en este orden:

1. Si el schema declara `type` y `types.matches(data, type)` es falso ->
   mensaje `{path}: expected {type}, got {type_name(data)}` y **se para
   ese nodo** (no se desciende, no se mira `enum` ni nada más).
2. Si el schema declara `enum` y el valor no está en la lista ->
   mensaje `{path}: value not in enum` y **se para ese nodo**.
   La pertenencia exige **igualdad estricta de tipo y valor**:
   `type(v) is type(e) and v == e` (por eso `True` no vale para el
   enum `[1]` ni `1` para `[True]`).
3. Si `type == "object"`:
   a. Cada nombre de `required` ausente en el dict del dato, **en el
      orden del array `required`** ->
      `{path}: missing required property '{nombre}'`.
   b. Cada clave del dict del dato **en orden de inserción**:
      - si está en `properties` -> validar el sub-schema con el path de
        la clave;
      - si no está en `properties` y `additionalProperties is False` ->
        mensaje `{path}: unexpected property '{clave}'` (path del
        **padre**; el valor extra no se valida);
      - en cualquier otro caso (extras permitidas por defecto) -> se
        ignora.
4. Si `type == "array"` y el schema declara `items`: validar cada
   elemento contra `items` con path `{path}[i]`, por índice.
5. Si `type == "string"`:
   - `minLength` presente y `len(data) < minLength` ->
     `{path}: string length {n} < minLength {m}`;
   - `maxLength` presente y `len(data) > maxLength` ->
     `{path}: string length {n} > maxLength {m}`.

`required`, `properties`, `additionalProperties` solo se interpretan si
`type == "object"`; `items` solo si `type == "array"`; `minLength` /
`maxLength` solo si `type == "string"`.

### Ejemplo canónico

```python
schema = {
    "type": "object",
    "properties": {
        "user": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
        "tags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["user"],
}
validate({"user": {}, "tags": [1]}, schema)
# ["$.user: missing required property 'name'",
#  "$.tags[0]: expected string, got integer"]
```

## Restricciones

- Solo puedes cambiar/crear dentro de `workspace/jsonval/` (normalmente
  `validator.py`; y tests tuyos). `paths.py` y `types.py` son intocables.
- Sin red, sin fechas reales, sin aleatoriedad: salida 100% determinista.
- Compatible con Python 3.12; estilo del paquete (type hints, español).

## Ejes de dureza

- Contrato de API estricto (paths y mensajes exactos, orden fijo).
- Casos límite exigentes (escaping de claves, bool/number, enum, acumulación).

---

## PARTE B

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
