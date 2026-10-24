# Tarea B: checkout-rounding-repo-cache-layer-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: checkout-rounding — redondeo monetario exacto en el pipeline de checkout

## Rol

Eres ingeniero de backend en un comercio online. El paquete `checkout`
(`workspace/checkout/`) procesa un pedido completo: **líneas de pedido →
impuestos → totales → recibo**. La versión actual es un borrador que hace
cuentas con `float` y con `round()` de Python, y redondea en el sitio
equivocado: con importes de dinero eso produce tickets que no cuadran.

## Requisito

Implementa (reescribe lo que haga falta) el paquete `checkout` para que
cumpla **exactamente** el contrato siguiente, con `decimal.Decimal` en toda
la API y redondeo monetario **half-up** en los puntos que fija el contrato.

- Los tests públicos de `workspace/tests_public/` son una **guía
  incompleta**: sirven para orientarte, pero **no cubren el contrato**. La
  especificación ejecutable completa es este documento: cada regla, cada
  mensaje de error y cada formato de aquí debe cumplirse.
- No modifiques los tests públicos; añade tus propios tests si quieres.
- No toques nada fuera de `workspace/checkout/` y de tus tests.

## Unidades, tipos y determinismo

- Todo importe y toda tasa se manipulan como `decimal.Decimal`. La firma y
  el resultado de las funciones del contrato son `Decimal`, nunca `float`.
- **Prohibido el `float` para dinero**: todo punto de entrada que reciba un
  importe o una tasa y encuentre un `float` debe lanzar `TypeError` con el
  mensaje que indica el contrato. Tampoco se admite `bool` donde se pide un
  `int` (`bool` no cuenta como entero).
- Prohibido `round()` de Python: usa exclusivamente
  `decimal.ROUND_HALF_UP` vía `quantize`.
- Sin red, sin fechas reales, sin aleatoriedad. Todo determinista.
- Python 3.12, type hints, identificadores en español, estilo del repo.

## Semántica de redondeo (vale para todo el documento)

Redondeo **half-up**: el empate se resuelve **hacia fuera de cero**
(*away from zero*), es decir `decimal.ROUND_HALF_UP`:

| entrada | decimales | resultado |
| --- | --- | --- |
| `Decimal("1.005")` | 2 | `Decimal("1.01")` |
| `Decimal("2.675")` | 2 | `Decimal("2.68")` |
| `Decimal("-1.005")` | 2 | `Decimal("-1.01")` |
| `Decimal("2.5")` | 0 | `Decimal("3")` |
| `Decimal("-2.5")` | 0 | `Decimal("-3")` |
| `Decimal("1.00005")` | 4 | `Decimal("1.0001")` |
| `Decimal("1.00004")` | 4 | `Decimal("1.0000")` |

Esto **no** es el redondeo bancario de `round()`: `round(1.005, 2) == 1.0`
y `round(2.5) == 2` están expresamente fuera de contrato.

## Contrato exacto

### `checkout/redondeo.py`

- `a_decimal(valor) -> Decimal`
  - `Decimal` → tal cual; `int` → `Decimal(valor)`; `str` → `Decimal(valor)`.
  - `float` → `TypeError("float prohibido para dinero: float")`
    (el mensaje lleva el nombre del tipo: `type(valor).__name__`).
  - cadena no convertible a número →
    `ValueError("importe no valido: {valor}")`.
  - cualquier otro tipo (p. ej. `None`) →
    `TypeError("tipo no soportado: NoneType")`.
- `redondear(valor: Decimal, decimales: int = 2) -> Decimal`
  - Devuelve `valor` redondeado half-up a `decimales` dígitos con exponente
    exacto: `redondear(Decimal("10"), 2)` devuelve `Decimal("10.00")` (y su
    `str` es `"10.00"`).
  - `valor` que no sea `Decimal` → `TypeError("se espera Decimal: float")`.
  - `decimales` que no sea entero → `TypeError("decimales no entero: ...")`;
    `decimales < 0` → `ValueError("decimales invalidos: {decimales}")`.
    En ese orden: primero el tipo, luego el rango.
  - `decimales` admite cualquier entero `>= 0` (el contrato se ejercita con
    0, 2 y 4).

### `checkout/modelos.py`

- `LineaPedido(descripcion: str, cantidad: int, precio_unitario: Decimal | str | int)`
  (dataclass `frozen`), con validación **en este orden** al construir:
  1. `descripcion` vacía → `ValueError("descripcion vacia")`.
  2. `cantidad` que no sea `int` (o que sea `bool`) →
     `TypeError("cantidad no entera: str")` (nombre del tipo real).
  3. el precio se convierte con `a_decimal` (aquí saltan sus `TypeError` /
     `ValueError`, incluido el del `float`).
  4. precio `< 0` → `ValueError("precio negativo: {valor original}")`.
  - El atributo `precio_unitario` queda normalizado a `Decimal`.
  - `cantidad` **puede ser 0 y puede ser negativa** (devoluciones): eso no
    es error, es el caso de uso.
- `Pedido(identificador: str, lineas: tuple[LineaPedido, ...], impuestos: tuple[Impuesto, ...] = (), decimales: int = 2)`
  (dataclass `frozen`), con validación en este orden:
  1. `identificador` vacío → `ValueError("identificador vacio")`.
  2. `decimales` que no sea entero → `TypeError("decimales no entero: ...")`.
  3. `decimales < 0` → `ValueError("decimales invalidos: {decimales}")`.
  - `impuestos` puede ser la tupla vacía (pedido sin impuestos).
  - `decimales` es la **precisión configurable** del pedido entero
    (por defecto 2; el contrato se ejercita con 0, 2 y 4).

### `checkout/impuestos.py`

- `Impuesto(nombre: str, tasa_pct: Decimal | str | int)` (dataclass `frozen`),
  validación en este orden:
  1. `nombre` vacío → `ValueError("nombre de impuesto vacio")`.
  2. la tasa se convierte con `a_decimal` (un `float` →
     `TypeError("float prohibido para dinero: float")`).
  3. tasa `< 0` → `ValueError("tasa negativa: {tasa}")`.
  4. tasa `> 100` → `ValueError("tasa fuera de rango: {tasa}")`.
  - El atributo `tasa_pct` queda normalizado a `Decimal`.
- Constantes predefinidas:
  - `IVA_GENERAL = Impuesto("IVA", Decimal("21"))`
  - `IVA_REDUCIDO = Impuesto("IVA reducido", Decimal("10.5"))`
  - `EXENTO = Impuesto("EXENTO", Decimal("0"))`
- `importe_impuesto(base: Decimal, impuesto: Impuesto, decimales: int = 2) -> Decimal`
  - `redondear(base * impuesto.tasa_pct / 100, decimales)`: **cada impuesto
    se calcula y redondea por separado**, con half-up.
  - `base` que no sea `Decimal` → `TypeError("se espera Decimal: float")`.
  - Ejemplos: `importe_impuesto(Decimal("100"), IVA_GENERAL) == Decimal("21.00")`;
    `importe_impuesto(Decimal("0.25"), Impuesto("t", "2")) == Decimal("0.01")`
    (empate `0.005` → sube); `importe_impuesto(Decimal("-0.25"), Impuesto("t", "2")) == Decimal("-0.01")`;
    `importe_impuesto(Decimal("100"), EXENTO) == Decimal("0.00")`;
    `importe_impuesto(Decimal("1.005"), IVA_GENERAL, 4) == Decimal("0.2111")`.

### `checkout/totales.py`

- `importe_linea(linea: LineaPedido, decimales: int = 2) -> Decimal`
  - `redondear(Decimal(linea.cantidad) * linea.precio_unitario, decimales)`.
  - **El redondeo de línea ocurre AQUÍ, antes de cualquier suma.**
  - Ejemplos: `importe_linea(LineaPedido("x", 3, "19.99")) == Decimal("59.97")`;
    `importe_linea(LineaPedido("x", 0, "19.99")) == Decimal("0.00")`;
    `importe_linea(LineaPedido("x", -2, "19.99")) == Decimal("-39.98")`;
    `importe_linea(LineaPedido("x", 1, "0.00025"), 4) == Decimal("0.0003")`.
- `subtotal(pedido: Pedido) -> Decimal`
  - Suma de los `importe_linea` **ya redondeados**. Está prohibido sumar en
    bruto y redondear una sola vez al final: con dos líneas de `1.005` el
    subtotal es `Decimal("2.02")`, no `2.01`. Con tres líneas de `0.00005` y
    `decimales=4` el subtotal es `Decimal("0.0003")`.
  - Pedido sin líneas → `Decimal("0.00")` (a la precisión del pedido).
- `desglose_impuestos(pedido: Pedido) -> tuple[tuple[Impuesto, Decimal], ...]`
  - Un tramo `(impuesto, importe)` **por cada impuesto configurado, en el
    orden del pedido** (aunque su importe sea 0).
  - El importe de cada tramo es la suma de
    `importe_impuesto(importe_linea(linea, decimales), impuesto, decimales)`
    recorriendo **línea a línea**. Está prohibido aplicar las tasas sobre el
    subtotal del pedido: con dos líneas de `0.05` e impuesto del `10%`, el
    tramo vale `Decimal("0.02")` (0.01 + 0.01), no `0.01`.
  - Pedido sin impuestos → tupla vacía `()`.
- `total_impuestos(pedido: Pedido) -> Decimal`
  - Suma de los importes del desglose (todos ya redondeados).
- `total_pedido(pedido: Pedido) -> Decimal`
  - `subtotal(pedido) + total_impuestos(pedido)` (resultado en la precisión
    del pedido). El total es siempre la suma de las partes ya redondeadas:
    con tres líneas de `1.005` e `IVA_GENERAL`:
    `subtotal == 3.03`, `total_impuestos == 0.63`, `total == 3.66`.

### `checkout/recibo.py`

- `formato_importe(valor: Decimal, decimales: int = 2) -> str`
  - Redondea half-up y devuelve **exactamente** `decimales` dígitos tras un
    punto `.` (nunca coma, nunca notación exponencial):
    `Decimal("19.5")` → `"19.50"`; `Decimal("10")` con 4 → `"10.0000"`;
    `Decimal("2.5")` con 0 → `"3"`; `Decimal("2.675")` → `"2.68"`.
  - El cero se escribe **siempre sin signo**: `Decimal("-0.004")` →
    `"0.00"` y `Decimal("-0.00004")` con 4 → `"0.0000"`.
  - Los negativos distintos de cero conservan el signo:
    `Decimal("-39.987")` → `"-39.99"`.
  - Un valor que no sea `Decimal` → `TypeError("se espera Decimal: ...")`.
- `formato_tasa(tasa_pct: Decimal | str | int) -> str`
  - Notación simple sin ceros sobrantes: `Decimal("21")` → `"21"`,
    `Decimal("10.50")` → `"10.5"`, `"10.5"` → `"10.5"`, `0` → `"0"`.
  - Un `float` → `TypeError("float prohibido para dinero: float")`.
- `recibo(pedido: Pedido) -> str`
  - Sin líneas → `ValueError("sin lineas")`.
  - Devuelve el texto plano con las líneas unidas por `"\n"` y **sin salto
    de línea final**. Estructura EXACTA, en este orden:
    1. `PEDIDO {identificador}`
    2. `"=" * len(cabecera)` (tantas `=` como caracteres tiene la línea 1)
    3. una línea por cada línea del pedido, en orden:
       `{descripcion} x{cantidad} @{precio} = {importe}` donde
       `precio = formato_importe(precio_unitario, decimales)` (se **muestra**
       el precio ya redondeado a la precisión del pedido; el **cálculo** del
       importe usa el precio sin redondear) e
       `importe = formato_importe(importe_linea(linea, decimales), decimales)`.
    4. `SUBTOTAL {formato_importe(subtotal(pedido), decimales)}`
    5. una línea por cada tramo de `desglose_impuestos`, en orden:
       `{impuesto.nombre} {formato_tasa(impuesto.tasa_pct)}% {formato_importe(importe, decimales)}`
       (aparecen **todas** las tasas configuradas, también las del `0%`).
    6. `TOTAL {formato_importe(total_pedido(pedido), decimales)}`

#### Ejemplo 1 (2 decimales, un impuesto)

```python
Pedido(
    "P-001",
    (LineaPedido("LIBRO", 1, "19.99"), LineaPedido("CAJA", 3, "2.50")),
    (IVA_GENERAL,),
)
```

```
PEDIDO P-001
============
LIBRO x1 @19.99 = 19.99
CAJA x3 @2.50 = 7.50
SUBTOTAL 27.49
IVA 21% 5.78
TOTAL 33.27
```

(El `IVA` es 4.20 + 1.58: se redondea **por línea**, 19.99·21% = 4.1979 →
4.20 y 7.50·21% = 1.575 → 1.58.)

#### Ejemplo 2 (impuestos combinados)

```python
Pedido(
    "P-002",
    (LineaPedido("SERVICIO", 1, "100.00"),),
    (IVA_GENERAL, IVA_REDUCIDO),
)
```

```
PEDIDO P-002
============
SERVICIO x1 @100.00 = 100.00
SUBTOTAL 100.00
IVA 21% 21.00
IVA reducido 10.5% 10.50
TOTAL 131.50
```

#### Ejemplo 3 (4 decimales)

```python
Pedido(
    "P-003",
    (LineaPedido("SERIE", 2, "1.00005"),),
    (IVA_GENERAL,),
    decimales=4,
)
```

```
PEDIDO P-003
============
SERIE x2 @1.0001 = 2.0001
SUBTOTAL 2.0001
IVA 21% 0.4200
TOTAL 2.4201
```

## Restricciones

- No toques nada fuera de `workspace/checkout/` y de tus tests.
- Compatible con Python 3.12; type hints y nombres en español, como el
  resto del repo.

---

## PARTE B

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
