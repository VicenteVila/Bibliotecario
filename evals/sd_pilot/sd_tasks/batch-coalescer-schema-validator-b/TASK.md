# Tarea B: batch-coalescer-schema-validator-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: batch-coalescer — coalescencia de lotes con ventana temporal

## Rol

Eres ingeniero de backend en un sistema de ingesta de eventos. El paquete
`batchkit` (en `workspace/batchkit/`) agrupa items en lotes para envío
por lotes. `batchkit/clock.py` define el protocolo de reloj y `ManualClock`,
un reloj manual determinista para tests y uso en general (el reloj es
**siempre inyectado**: el paquete no usa `time` real en ningún sitio y así
debe seguir siendo).

## Requisito

Implementa `batchkit.coalescer.BatchCoalescer` (hoy es un esqueleto) para
que cumpla exactamente el contrato siguiente. Determinismo absoluto: la
única fuente de tiempo es el reloj inyectado.

## Contrato exacto de `batchkit.coalescer.BatchCoalescer`

### Constructor

```python
BatchCoalescer(window: float, clock: Callable[[], float], max_size: int | None = None)
```

Validaciones, en este orden:

1. `window` no es numérico (`int`/`float`; **`bool` no cuenta**) ->
   `TypeError` con mensaje exacto `window must be a number`.
2. `window <= 0` -> `ValueError` con mensaje exacto `window must be > 0`.
3. `clock` no es callable -> `TypeError` con mensaje exacto
   `clock must be callable`.
4. `max_size` no es `None` y no es entero (`bool` no cuenta) ->
   `TypeError` con mensaje exacto `max_size must be an integer`.
5. `max_size` no es `None` y `max_size < 1` -> `ValueError` con mensaje
   exacto `max_size must be >= 1`.

### Modelo

- Solo hay **un lote abierto** a la vez. El lote abierto lleva sus items
  (en orden de inserción) y su `first_ts`: el timestamp efectivo del
  **primer** item que lo abrió.
- Timestamp efectivo de un `add`: el argumento `ts` si no es `None`, si no
  `clock()`. Los `add` posteriores **no** cambian el `first_ts` del lote
  abierto (aunque su `ts` sea menor o mayor).
- Hay una cola FIFO de lotes **listos** (cerrados y aún no entregados).

### `add(item: str, ts: float | None = None) -> None`

1. `item` no es `str` -> `TypeError` con mensaje exacto `item must be str`.
2. `ts` no es `None` y no es numérico (`bool` no cuenta) -> `TypeError`
   con mensaje exacto `ts must be a number`.
3. El item entra al lote abierto (creándolo si no lo hay, con
   `first_ts` = timestamp efectivo de ese item).
4. Si `max_size` no es `None` y el lote abierto alcanzó `max_size` items,
   el lote **se cierra inmediatamente** (pasa a la cola de listos) y el
   siguiente `add` abrirá uno nuevo con su propio `first_ts`.

### `poll() -> list[list[str]]`

- Cierra el lote abierto si `clock() - first_ts >= window` (borde
  incluido: en el instante exacto ya está vencido).
- Devuelve **todos** los lotes listos, en orden FIFO de cierre, y vacía
  la cola. Un lote cerrado por `max_size` se entrega en el primer
  `poll()` **sin** comprobar la ventana.
- Sin lotes listos -> `[]`. Nunca se entregan lotes vacíos.

### `flush() -> list[list[str]]`

- Entrega la cola de listos (FIFO) y, si hay lote abierto, lo cierra y lo
  entrega el último. La cola queda vacía y el estado de lotes se reinicia.
- Sin nada pendiente -> `[]`. Nunca se entregan lotes vacíos.

### `pending: int` (property)

Número de items aún no entregados (cola de listos + lote abierto).

### Ejemplo canónico

```python
reloj = ManualClock(0.0)
co = BatchCoalescer(window=5.0, clock=reloj, max_size=None)
co.add("a")                 # lote abierto [a], first_ts=0
reloj.advance(2.0)
co.add("b")                 # sigue abierto [a, b], first_ts=0
co.poll()                   # []  (now-first_ts=2 < 5)
reloj.advance(3.0)          # now=5; 5-0>=5
co.poll()                   # [["a", "b"]]
co.flush()                  # []
```

## Restricciones

- Solo puedes cambiar/crear dentro de `workspace/batchkit/` (normalmente
  `coalescer.py`; y tests tuyos). `clock.py` es intocable.
- Sin red, sin fechas reales, sin aleatoriedad, **sin `time` real**: usa
  el reloj inyectado.
- Compatible con Python 3.12; estilo del paquete (type hints, español).

## Ejes de dureza

- Casos límite exigentes (borde de ventana, `max_size`, FIFO, ts stale).
- Contrato de API estricto (mensajes de error y semántica de entrega).

---

## PARTE B

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
