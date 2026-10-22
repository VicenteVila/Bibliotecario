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
