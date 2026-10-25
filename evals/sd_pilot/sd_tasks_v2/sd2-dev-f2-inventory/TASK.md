# Tarea: transferencias de inventario

## Rol

Mantienes el paquete `inventory` de un almacén. Ya existen las funciones de
stock y reservas; falta completar la planificación de transferencias entre dos
almacenes. Los tests públicos de `tests_public/` fallan ahora y muestran parte
del contrato.

## Requisito

Completa `plan_transfer` para que cumpla el contrato. No modifiques los tests.
Puedes leer el resto del paquete: `available_stock` ya existe y debe usarse.

## Contrato exacto

### `transfers.py`

- `Transferencia(sku: str, cantidad: int, origen: str, destino: str)` es una
  dataclass inmutable.
- `plan_transfer(origen, destino, reservas, cantidad, now) -> Transferencia`:
  1. `cantidad <= 0` → `ValueError(f"cantidad invalida: {cantidad}")`.
  2. `origen.sku != destino.sku` →
     `ValueError(f"sku distinto: {origen.sku} != {destino.sku}")`.
  3. si `available_stock(origen, reservas, now) < cantidad` →
     `ValueError(f"stock insuficiente: {cantidad}")`.
  4. en caso contrario devuelve `Transferencia(origen.sku, cantidad,
     origen.sku, destino.sku)`. No muta las reservas ni los productos.

## Restricciones

- No toques nada fuera de `inventory` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
