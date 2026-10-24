# Tarea B: csv-diff-engine-config-migration-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: csv-diff-engine — diff de tablas CSV por clave

## Contexto

El paquete `csvdiff` (en `workspace/csvdiff/`) lee un CSV en una `Table`
indexada por una o varias columnas clave y calcula el diff entre dos
archivos. La primera versión es rudimentaria: no gestiona BOM, filas en
blanco ni renombrados de columna.

## Requisito

Endurece el lector y el motor de diff para que sean robustos y para que
detecten **renombrados de columna**, manteniendo el contrato de salida
exacto (mismas claves, mismos tipos, mismo orden).

## Contrato exacto

### `csvdiff.read_table(path, key_columns) -> Table`

- Codificación **utf-8-sig**: un BOM inicial no debe aparecer en la
  primera columna.
- Dialecto `csv` por defecto: acepta LF y CRLF, campos entrecomillados con
  comas y comillas escapadas.
- **Filas en blanco** (sin celdas o con todas las celdas vacías) se
  ignoran por completo y no cuentan como filas de datos; la numeración de
  líneas que reportan los errores es la **línea física** del fichero
  (1-based, usando `csv.reader.line_num`).
- La primera fila no en blanco es la cabecera. Archivo sin ninguna fila
  no en blanco -> `MissingKeyColumnError` con la **primera** columna clave.
- Columna repetida en la cabecera -> `DuplicateColumnError(column, line)`
  (atributos `.column`, `.line`).
- Columna clave ausente -> `MissingKeyColumnError(column)` (atributo
  `.column`).
- Celdas que falten en una fila se rellenan con `""`; las sobrantes se
  ignoran.
- **Clave compuesta**: los valores de las columnas clave se unen con el
  separador `csvdiff.table.KEY_SEPARATOR` (`"\x1f"`), en el orden de
  `key_columns`. Clave repetida -> `DuplicateKeyError(key, line)`
  (atributos `.key`, `.line`), con la línea física de la segunda
  aparición.
- `Table` expone `.columns: list[str]`, `.key_columns: list[str]` y
  `.rows: dict[str, dict[str, str]]`.

### `csvdiff.diff_tables(old, new) -> DiffResult` y
### `csvdiff.diff_csv(old_path, new_path, key_columns) -> DiffResult`

`DiffResult` (dataclass) con estos campos, y `to_dict()` devuelve
**exactamente** este dict:

```python
{
    "added":   {clave: {columna: valor}},            # filas solo en new
    "removed": {clave: {columna: valor}},            # filas solo en old
    "changed": {clave: {columna: {"old": ..., "new": ...}}},
    "renamed_columns": {columna_vieja: columna_nueva},
    "unchanged": int,                                # claves en ambos sin cambios
}
```

Semántica:

- `added` usa **todos** los nombres de columna del archivo nuevo; `removed`
  los del archivo antiguo.
- **Detección de renombrados**: solo se declara un renombrado cuando
  exactamente falta una columna en el archivo nuevo (respecto al antiguo),
  exactamente sobra una en el nuevo y sus valores coinciden **en todas**
  las filas presentes en los dos archivos. Si hay más de una columna
  sobrante/faltante, o los valores no coinciden, `renamed_columns` es `{}`.
- `changed` compara únicamente las **columnas comparables**: la
  intersección de columnas tras aplicar el renombrado detectado (la
  columna vieja se compara bajo su nombre nuevo). Las columnas que sobran
  en un lado y no son renombrado se **ignoran** en la comparación, pero
  sí aparecen en las filas de `added`/`removed`.
- En `changed` solo entran las celdas que difieren (no la fila entera).
- Orden determinista: `added`, `removed` y `changed` iteran sus claves con
  `sorted(...)`; dentro de cada fila de `changed`, las columnas se insertan
  en orden alfabético.
- `unchanged` cuenta las claves presentes en ambos archivos que no tienen
  ninguna celda cambiada.

## Fuera de alcance

No toques nada fuera de `workspace/csvdiff/`.

---

## PARTE B

# Tarea: config-migration — añadir soporte TOML (tercer formato)

## Contexto

El paquete `configmig` (en `workspace/configmig/`) migra configuraciones
entre formatos. Hoy soporta dos **formatos de origen** (INI y JSON), un
modelo canónico `Config` (valores planos con claves con punto), un
validador de esquema y un orquestador `migrator` (detectar formato, leer,
validar, serializar). Necesitamos un **tercer formato: TOML**.

## Requisito

Extiende el paquete para soportar TOML de origen y destino, tocando los
módulos necesarios (lector, convertidor, validador, orquestador) sin
romper el contrato existente.

## Contrato exacto

### Modelo (`configmig.model`)

```python
@dataclass
class Config:
    values: dict[str, object]   # claves planas con punto -> str|int|float|bool
```

`flatten(data: dict) -> dict[str, object]`: aplana dicts anidados uniendo
con `"."`; dicts vacíos se omiten; un valor de tipo lista ->
`ConfigParseError`.

### Errores (`configmig.errors`)

- `ConfigParseError` — entrada mal formada.
- `UnknownFormatError(path)` — atributo `.path`.
- `ConfigValidationError(errors: list[str])` — atributo `.errors`
  (lista ordenada).

### Lectores (`configmig.readers`)

- `read_ini(text) -> Config`
  - Comentarios `#`/`;`, secciones `[seccion]`, pares `clave = valor`.
  - BOM inicial (`﻿`) se ignora.
  - Clave **fuera de cualquier sección** -> `ConfigParseError`.
  - Sección vacía `[]` -> `ConfigParseError`.
  - Clave repetida (misma clave con punto) -> `ConfigParseError`.
  - Valor recortado; si va entrecomillado con `'` o `"` en ambos extremos,
    se quitan las comillas.
  - Coerción del valor (tras quitar comillas): `true`/`false` exactos en
    minúsculas -> `bool`; `^[+-]?\d+$` -> `int`;
    `^[+-]?(\d+\.\d*|\.\d+)$` -> `float`; el resto -> `str`.
- `read_json(text) -> Config`
  - BOM inicial se ignora; raíz no-objeto o JSON inválido ->
    `ConfigParseError`; listas como valor -> `ConfigParseError`.
- `read_toml(text) -> Config` **(NUEVO)**
  - Usa `tomllib` de la stdlib. Sintaxis TOML inválida ->
    `ConfigParseError`. El resultado se aplana igual que JSON.

### Convertidores (`configmig.converters`)

- `write_json(config) -> str` — `json.dumps` del dict plano con
  `sort_keys=True, indent=2, ensure_ascii=False` y `"\n"` final.
- `write_ini(config) -> str` — claves **sin punto** primero (líneas
  `k = v`), luego cada sección en **orden alfabético** de nombre, en el
  formato:

  ```
  [seccion]
  clave = valor
  ```

  con claves ordenadas dentro de la sección y una línea en blanco antes
  de cada `[seccion]` (salvo si no hay líneas previas). Escalares:
  `bool` -> `true`/`false`, el resto con `str(v)`. Termina en `"\n"`.
- `write_toml(config) -> str` **(NUEVO)** — misma estructura que
  `write_ini`, pero las **cadenas** se serializan con
  `json.dumps(valor, ensure_ascii=False)` (entrecomilladas y escapadas);
  `bool` -> `true`/`false`; números sin comillas.

### Validador (`configmig.validator`)

Esquema canónico:

- Requeridas: `app.name: str`, `app.version: str`, `db.host: str`,
  `db.port: int`.
- Opcional: `db.tls: bool`.

`validate(config) -> None` lanza `ConfigValidationError` con **todos** los
fallos reunidos, en `.errors` ordenados alfabéticamente, con estos
prefijos exactos:

- `missing:<clave>` — requerida ausente.
- `type:<clave>` — el tipo no coincide **exactamente** (`bool` no vale
  como `int`: `True` para `db.port` es `type:db.port`).
- `empty:<clave>` — una cadena requerida cuyo valor es `""`.
- `unknown:<clave>` — clave fuera de requeridas+opcionales.

### Orquestador (`configmig.migrator`)

- `SUFFIXES`: `.ini`/`.cfg` -> `"ini"`, `.json` -> `"json"`, `.toml` ->
  `"toml"`.
- `detect_format(path) -> str`; extensión desconocida ->
  `UnknownFormatError`.
- `load(path) -> Config` — lee el fichero con `encoding="utf-8-sig"`
  (sin BOM) y delega en el lector que corresponda.
- `migrate(src_path, dst_format="json") -> str` — destino fuera de
  `"ini"|"json"|"toml"` -> `UnknownFormatError(dst_format)`; si no: load,
  `validate`, y serializa con el escritor del formato destino.

## Fuera de alcance

No toques nada fuera de `workspace/configmig/`.
