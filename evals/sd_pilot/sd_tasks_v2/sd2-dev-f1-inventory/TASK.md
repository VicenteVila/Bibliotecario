# Tarea: inventario con reservas caducadas

## Rol

Mantienes el paquete `inventory` de un almacén. El stock disponible se calcula
restando las reservas activas no caducadas. El paquete contiene **exactamente
3 defectos, en 3 ficheros distintos**: `stock.py`, `reservations.py` y
`alerts.py`. Los tests públicos de `tests_public/` fallan ahora y muestran
parte del comportamiento incorrecto.

## Requisito

Diagnostica los defectos ejecutando los tests públicos y leyendo el paquete.
Corrige **solo el código** para cumplir el contrato. No modifiques los tests:
son la especificación ejecutable.

## Contrato exacto

### `models.py` (correcto; léelo)

- `Producto(sku: str, nombre: str, stock: int, reorder_level: int)`
- `Reserva(sku: str, cantidad: int, created_at: int, ttl_seconds: int,
  status: str = "active")`
- `status` solo puede ser `"active"`, `"expired"` o `"cancelled"`.

### `reservations.py`

- `is_expired(reserva, now) -> bool`: una reserva caduca cuando
  `now - reserva.created_at >= reserva.ttl_seconds`. El instante exacto del
  TTL **ya está caducado**.
- `release_expired(reservas, now) -> tuple[Reserva, ...]`: devuelve una tupla
  nueva; las reservas `"active"` caducadas pasan a `"expired"`. No muta las
  originales y no toca las que no están caducadas.

### `stock.py`

- `available_stock(producto, reservas, now) -> int`: empieza en
  `producto.stock` y resta **solo** las reservas del mismo `sku`, con
  `status == "active"` y **no caducadas**. Las caducadas, canceladas y de otro
  `sku` no restan. No recorta el resultado a cero.

### `alerts.py`

- `needs_reorder(producto, reservas, now) -> bool`: usa
  `available_stock(...)`; devuelve `True` cuando el disponible es
  **menor o igual** que `producto.reorder_level`. El umbral es incluyente.

## Restricciones

- No toques nada fuera de `inventory` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
