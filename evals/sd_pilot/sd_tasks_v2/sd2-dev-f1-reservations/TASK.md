# Tarea: corregir reservas

## Rol

El paquete `reservas` calcula disponibilidad, caducidades y alertas. Los tests
públicos fallan. Repara la lógica sin cambiar la API ni los tests.

## Requisito

Corrige los defectos del paquete `reservas`. No modifiques
`workspace/tests_public/` ni los tests ocultos.

## Contrato exacto

- `procesar(capacidad, reservas, now) -> Resultado`.
- `capacidad` debe ser `>= 0`; si no, `ValueError("capacidad invalida")`.
- Cada reserva debe tener `cantidad > 0`; si no,
  `ValueError("cantidad invalida: <reserva_id>")`.
- Una reserva está caducada cuando
  `now - created_at >= ttl_seconds`.
- Solo las reservas `active` y no caducadas restan capacidad.
- `caducadas` cuenta las reservas `active` caducadas.
- `alerta` es `True` si `disponible <= 1`.
- La sobreventa produce disponible negativo; no la ocultes.

## Restricciones

- No toques nada fuera de `reservas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
