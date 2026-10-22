# Tarea: cli-subcommand — subcomando `report` para la CLI de inventario

## Rol

Eres ingeniero de backend en un almacén. El paquete `stockcli` (en
`workspace/stockcli/`) es la CLI interna de consulta del inventario: parsea
argv (`parser.py`), despacha a handlers (`dispatcher.py`), formatea la salida
(`formatter.py`) y expone `main` (`cli.py`). Hoy soporta los comandos
`list` y `count`. Product management pide un subcomando nuevo: `report`.

## Requisito

Añade el subcomando `report` a la CLI, tocando las tres capas existentes
(parser / dispatcher / formatter) sin romper los comandos ya publicados
(`list`, `count`) ni sus formatos de salida. No toques `errors.py` ni
`models.py` (salvo, si lo necesitas, añadir el dataclass `ReportResult` que
ya está previsto en el contrato). No cambies la firma de `main`.

## Contrato exacto

### `stockcli.parser.Command`

```python
Command(name: str, options: dict[str, str | int])
```

Claves de `options`: nombre del flag con guiones convertidos a guion bajo
(`--min-qty` -> `options["min_qty"]`). Las opciones no presentes en argv
**no** aparecen en el dict.

### `stockcli.parser.parse(argv: list[str]) -> Command`

Gramática: `argv[0]` es el comando; el resto son flags `--flag` o
`--flag=valor`. Un flag sin `=` consume el siguiente token como valor.
Errores (excepción `stockcli.errors.UsageError`, mensaje exacto):

- `argv` vacío -> `missing command`
- comando desconocido -> `unknown command: {name!r}`
- token que no empieza por `--` -> `unexpected argument: {token!r}`
- flag que no pertenece al comando -> `unknown flag: --{flag}`
- `--flag` sin valor al final -> `flag requires a value: --{flag}`
- valor entero no convertible -> `invalid integer for --{flag}: {raw!r}`
- `--status` fuera de `OK|LOW|OUT` -> `invalid status: {raw!r} (expected OK|LOW|OUT)`
- `--min-qty` con valor `< 0` -> `min-qty must be >= 0`
- `--top` con valor `< 1` -> `top must be >= 1`

Flags por comando:

- `list`: `--status <OK|LOW|OUT>`
- `count`: `--status <OK|LOW|OUT>`
- `report`: `--status <OK|LOW|OUT>`, `--min-qty <int>`, `--top <int>`

El parser actual usa el registro `_SPECS`; extiéndelo, no lo reescribas.

### `stockcli.dispatcher.dispatch(command: Command, items) -> tuple[str, object]`

Devuelve siempre una tupla `(kind, payload)`:

- `list` -> `("list", list[Item])`
- `count` -> `("count", int)`
- `report` -> `("report", ReportResult)`

El registro actual es `_HANDLERS`; registra el handler de `report`.

### Semántica de `report`

Dados `items` (secuencia de `stockcli.models.Item`):

1. **Filtro**: si `options` trae `status`, solo items con ese `status`;
   si trae `min_qty`, solo items con `qty >= min_qty`. Ambos filtros se
   acumulan (Y).
2. **Orden**: `qty` descendente; a igual `qty`, `sku` ascendente
   (orden lexicográfico). Determinista, independiente del orden de entrada.
3. **`top`**: si está presente, el resultado lleva solo las primeras N
   filas ya ordenadas. `ReportResult.total` es el número de items
   **tras los filtros y antes de aplicar `top`**.
4. `ReportResult` es un dataclass congelado: `total: int` y
   `rows: tuple[Item, ...]` (las filas ya ordenadas y recortadas).

### `stockcli.formatter`

Formatos existentes (intocables):

- `list`: una línea por item `"{sku} {qty} {status}"`; si no hay items,
  literalmente `EMPTY`.
- `count`: una línea `COUNT {n}`.

Formato nuevo de `report`:

- Primera línea: `TOTAL {total}` (con `total` de `ReportResult.total`).
- Después, una línea por fila de `rows` en orden, mismo formato que
  `list`: `"{sku} {qty} {status}"`.
- Con `total == 0` la salida es **solo** la línea `TOTAL 0` (sin filas).

`format_result(result: tuple[str, object]) -> str` enruta por `kind` con el
registro `_FORMATTERS`; registra `report`. Formato desconocido ->
`UsageError` con mensaje `unknown result kind: {kind!r}`.

### `stockcli.cli.main`

```python
main(argv: list[str] | None = None, *, items=ITEMS, stdout=None, stderr=None) -> int
```

- `argv is None` -> `sys.argv[1:]`; `stdout`/`stderr` `None` -> `sys.*`.
- Éxito: escribe `format_result(result) + "\n"` en stdout y devuelve `0`.
- `UsageError`: escribe `f"error: {exc}\n"` en stderr y devuelve `2`
  (stdout queda vacío).
- `DataError`: idéntico pero devuelve `1`.
- `items` por defecto: `stockcli.models.ITEMS`.

## Restricciones

- Solo puedes cambiar/crear dentro de `workspace/stockcli/` (y tests tuyos).
- Sin red, sin fechas reales, sin aleatoriedad: salida 100% determinista.
- Compatible con Python 3.12; estilo del paquete (type hints, español).

## Ejes de dureza

- Integración multi-fichero (parser + dispatcher + formatter + registro).
- Contrato de API estricto (mensajes de error y formato de salida exactos).
