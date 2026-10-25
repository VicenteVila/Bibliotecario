# Tarea: completar el servicio de reservas

## Rol

`reservas.rules` ya implementa capacidad, caducidad y alerta. `service.py` es
una versión incompleta que ignora estado, caducidad y validación. Los tests
públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(capacidad, reservas, now) -> Resultado`.
- `capacidad >= 0`; si no, `ValueError("capacidad invalida")`.
- Cada reserva debe tener `cantidad > 0`; si no,
  `ValueError("cantidad invalida: <reserva_id>")`.
- Caducidad: `now - created_at >= ttl_seconds`.
- Solo las reservas `active` y no caducadas restan capacidad.
- `caducadas` cuenta las reservas `active` caducadas.
- `alerta` es `True` si `disponible <= 1`.
- La sobreventa produce disponible negativo.

## Restricciones

- No toques nada fuera de `reservas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
