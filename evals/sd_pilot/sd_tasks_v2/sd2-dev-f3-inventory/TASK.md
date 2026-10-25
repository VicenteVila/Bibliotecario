# Tarea: fachada de inventario con estado

## Rol

El paquete `inventory` ya tiene funciones de stock y reservas. Ahora se necesita
una fachada con estado, `Inventario`, que encapsule productos y reservas y
libere las caducadas. Los tests públicos de `tests_public/` fallan porque la
fachada está sin implementar.

## Requisito

Implementa `Inventario` en `service.py` reutilizando las funciones existentes.
No modifiques los tests ni las funciones de `stock.py`, `reservations.py` o
`alerts.py`.

## Contrato exacto

- `Inventario(productos: dict[str, Producto], reservas: Iterable[Reserva])`:
  guarda una copia de productos y reservas; no comparte la lista de reservas.
- `disponible(sku, now) -> int`: `available_stock` del producto; `KeyError` si
  el `sku` no existe.
- `alerta(sku, now) -> bool`: `needs_reorder` del producto; `KeyError` si no
  existe.
- `liberar(now) -> int`: sustituye las reservas internas por
  `release_expired(...)` y devuelve cuántas reservas **activas** pasaron a
  `"expired"`. Es idempotente: una segunda llamada sin nuevas caducadas
  devuelve 0.
- `reservas_actuales() -> tuple[Reserva, ...]`: tupla con las reservas
  internas actuales.

## Restricciones

- No toques nada fuera de `inventory` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
