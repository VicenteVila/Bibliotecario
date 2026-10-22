# Tarea: pipeline de facturación con defectos que hay que diagnosticar

## Rol

Eres ingeniero manteniendo el módulo de facturación de un negocio. El
paquete `facturacion` calcula subtotales, descuentos, IVA y emite facturas
con folio correlativo. **El paquete contiene exactamente 3 defectos, repartidos
en 3 ficheros distintos del paquete** (`impuestos.py`, `totales.py`,
`emitir.py`). Los tests públicos de `tests_public/` fallan ahora mismo y
evidencian los defectos.

## Requisito

Diagnostica los 3 defectos a partir de las **salidas de fallo de los
tests públicos** y de la lectura de todo el paquete, y corrige el **código**
para que el pipeline cumpla **exactamente** el contrato siguiente. No
corrijas ni modifiques los tests: son la especificación ejecutable. No
modifiques `modelos.py` salvo si fuera imprescindible (no debería serlo:
es correcto). Cada defecto está en un fichero distinto de los tres citados.

## Unidades y determinismo

- Todos los importes están en **céntimos enteros** (`int`). No hay floats
  en la API ni en los resultados.
- Sin fechas reales: el año de emisión se pasa explícitamente. Sin red ni
  aleatoriedad.

## Contrato exacto

### `modelos.py` (ya correcto; léelo)

- `Cliente(cif: str, nombre: str, exento_iva: bool = False)`
- `Linea(descripcion: str, cantidad: int, precio_unit_cents: int)`
- `Factura` dataclass con campos: `cliente`, `lineas` (tupla), `folio`,
  `anio`, `subtotal_cents`, `descuento_pct`, `base_cents`, `iva_cents`,
  `total_cents`.

### `totales.py`

- `subtotal_cents(lineas) -> int`: suma de `cantidad * precio_unit_cents`.
  Valida cada línea, en orden: `cantidad >= 1` o
  `ValueError("cantidad no positiva: {cantidad}")`; `precio_unit_cents >= 0`
  o `ValueError("precio negativo: {precio}")`.
- `descuento_por_volumen_pct(num_lineas: int) -> int`:
  - `num_lineas < 5` → `0`
  - `5 <= num_lineas < 10` → `5`
  - `num_lineas >= 10` → `10`
  (los umbrales son **incluyentes**: 5 líneas dan 5%, 10 líneas dan 10%).
- `descuento_cents(monto: int, pct: int) -> int`: **half-up exacto en
  céntimos**, fórmula obligatoria `(monto * pct + 50) // 100`. NUNCA
  `round()` de Python (usa redondeo bancario: `round(262.5) == 262`).
- `base_imponible_cents(lineas, descuento_extra_pct: int = 0) -> int`:
  `subtotal - descuento_cents(subtotal, pct_total)` donde
  `pct_total = descuento_por_volumen_pct(len(lineas)) + descuento_extra_pct`;
  si `pct_total > 100` → `ValueError("descuento total invalido: {pct_total}")`.

### `impuestos.py`

- `TASA_IVA_DEFECTO = 21`
- `iva_cents(base_cents: int, tasa_pct: int = TASA_IVA_DEFECTO) -> int`:
  mismo redondeo half-up obligatorio: `(base_cents * tasa_pct + 50) // 100`.
  NUNCA `round()`.

### `emitir.py`

- `class Emisor`: mantiene la secuencia de folios por año.
  `siguiente_folio(anio: int) -> str` devuelve `f"F-{anio}-{n:04d}"` con
  `n` empezando en **1** en el primer folio de cada año y correlativo
  después (por año, independientes: `F-2024-0001`, `F-2025-0001`, ...).
- `emitir(emisor, cliente, lineas, anio, descuento_extra_pct=0) -> Factura`:
  1. `lineas` vacío → `ValueError("sin lineas")`.
  2. `subtotal = subtotal_cents(lineas)` (valida).
  3. `descuento_pct = descuento_por_volumen_pct(len(lineas)) + descuento_extra_pct`;
     `> 100` → el ValueError de `base_imponible_cents`.
  4. `base = base_imponible_cents(lineas, descuento_extra_pct)`.
  5. `iva = 0` si `cliente.exento_iva`, si no `iva_cents(base)`.
  6. `total = base + iva`.
  7. `folio = emisor.siguiente_folio(anio)` (el folio se toma **una sola
     vez** por factura emitida).

## Restricciones

- No toques nada fuera del paquete `facturacion` y tus tests.
- Compatible con Python 3.12, estilo del repo (type hints, dataclasses,
  identificadores en español).
