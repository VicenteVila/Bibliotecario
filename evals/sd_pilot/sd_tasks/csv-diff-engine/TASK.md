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
