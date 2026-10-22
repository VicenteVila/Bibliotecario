# Tarea: capa de caché TTL para el repositorio del catálogo

## Rol

Eres ingeniero de backend en un proyecto de gestión de biblioteca. El paquete
`catalogo` ya existe y funciona: tiene modelos, una capa de persistencia
SQLite (`db.py`), DAOs (`daos.py`) y un servicio de alto nivel
(`servicio.py`). El servicio consulta los DAOs en cada llamada y eso es un
problema de rendimiento en lecturas repetidas.

## Requisito

Implementa la capa de caché `catalogo/cache.py` (clase `CacheTTL`) de forma
que **se ajuste exactamente al contrato siguiente**, y deja que
`catalogo/servicio.py` la use tal como ya está diseñado para usarla. No
modifiques los módulos `modelos.py`, `db.py`, `daos.py` ni `servicio.py`:
son la arquitectura existente y su comportamiento es el correcto. Tu trabajo
es hacer que `CacheTTL` cumpla el contrato y encaje con el servicio.

El código debe ser determinista y sin E/S externa: la única fuente de tiempo
es el reloj inyectado en el constructor.

## Contrato exacto de `catalogo.cache.CacheTTL`

### Constructor

```python
CacheTTL(capacidad: int, reloj: Callable[[], float])
```

- `capacidad`: número máximo de entradas vivas simultáneas. Debe ser `>= 1`;
  si no se cumple se lanza `ValueError` con el mensaje exacto
  `capacidad debe ser >= 1`.
- `reloj`: función sin argumentos que devuelve el tiempo actual en segundos
  (puede ser un reloj falso de los tests). Es obligatoria.

### `obtener(clave: str) -> tuple[bool, Any]`

- Si `clave` no está almacenada o su TTL ya venció, devuelve
  `(False, None)`.
- Si `clave` está almacenada y no ha vencido, devuelve `(True, valor)` y la
  entrada pasa a ser la **más reciente** en el orden LRU.
- Una entrada expirada detectada al consultar se **elimina** en ese momento
  (purga perezosa) y se incrementan **dos** contadores: `expiraciones` (+1) y
  `fallos` (+1).
- **Borde del TTL**: una entrada escrita en el instante `t0` con `ttl` vence
  cuando `reloj() >= t0 + ttl`. Es decir, justo en el instante límite ya está
  expirada (no es un acierto).
- Un valor `None` almacenado es un valor normal: `obtener` devuelve
  `(True, None)` (acielo), no se confunde con una ausencia.

### `poner(clave: str, valor: Any, ttl: float) -> None`

- `ttl` debe ser `> 0`; si no se cumple se lanza `ValueError` con el mensaje
  exacto `ttl debe ser > 0`.
- Inserta o **reemplaza** la entrada. Reemplazar reinicia su expiración
  (nuevo `t0` = reloj actual) y la coloca como la más reciente (LRU).
- Tras insertar, si el tamaño supera `capacidad`, se **expulsa la entrada
  menos recientemente usada** (orden LRU: el orden de uso se marca con
  `obtener` y `poner`, ambos cuentan como uso) y se incrementa `evicciones`
  (+1 por entrada expulsada).
- Guardar `None` es permitido.

### `invalidar_prefijo(prefijo: str) -> int`

- Elimina **todas** las cuyos nombres **comiencen por** `prefijo`
  (`str.startswith`), incluida una clave idéntica al prefijo. NO se mira si
  han expirado: se eliminan igualmente y **sin** incrementar `expiraciones`.
- `prefijo == ""` elimina todas las entradas.
- Devuelve el número de entradas eliminadas.
- No modifica los contadores de aciertos/fallos.

### `estadisticas() -> dict[str, int]`

Devuelve exactamente estas seis claves, todas enteras:

```python
{"aciertos": int, "fallos": int, "expiraciones": int,
 "evicciones": int, "tamano": int, "capacidad": int}
```

- `tamano` = entradas vivas en el mapa (incluye las que ya vencieron pero
  aún no se han purgado; la consulta de estadísticas **no** debe purgarlas
  ni debe tocar ningún contador).
- `capacidad` = la capacidad fijada en el constructor.

### `limpiar() -> None`

- Elimina todas las entradas y pone a cero `aciertos`, `fallos`,
  `expiraciones` y `evicciones`. La `capacidad` no cambia.

## Contrato del servicio (`catalogo.servicio.CatalogoService`) — léelo, no lo toques

El servicio ya está escrito sobre la caché y define las claves y los TTLs.
Debes conocerlos porque son parte del contrato observable del sistema:

- `libro(isbn)`: clave `f"libro:{isbn}"`, TTL 60.0 s. Si el DAO no encuentra
  el ISBN, el resultado (`None`) **no se cachea** (se vuelve a consultar).
- `listar_por_autor(autor)`: clave `f"autor:{autor}"`, TTL 30.0 s. Devuelve
  siempre una **copia** de la lista de ISBNs (mutar el resultado no corrompe
  la caché). Una lista vacía sí se cachea.
- `copias_disponibles(isbn)`: clave `f"copias:{isbn}"`, TTL 60.0 s.
- `agregar_libro(libro)`: tras persistir, invalida el prefijo `"autor:"`
  (todos los listados de autores quedan obsoletos).
- `registrar_prestamo(id_prestamo, isbn)`: tras persistir, invalida
  `f"libro:{isbn}"` y `f"copias:{isbn}"`. No debe tocar claves de otros ISBN.
- `devolver_prestamo(id_prestamo)`: el DAO devuelve el ISBN prestado; tras
  persistir, invalida `f"copias:{isbn}"`.
- `actualizar_copias(isbn, delta)`: tras persistir, invalida
  `f"libro:{isbn}"` y `f"copias:{isbn}"`.
- El servicio devuelve siempre datos de `modelos.Libro` (inmutables) o copias
  de listas: el caché nunca debe permitir que un caller corrompa el estado.

## Restricciones

- Solo puedes cambiar/crear `catalogo/cache.py` (y, si lo necesitas, tests
  tuyos). El resto del paquete es intocable.
- Sin red, sin fechas reales, sin aleatoriedad: todo debe ser determinista.
- Compatible con Python 3.12 y el código actual del paquete (estilo en
  español, type hints, dataclasses).
