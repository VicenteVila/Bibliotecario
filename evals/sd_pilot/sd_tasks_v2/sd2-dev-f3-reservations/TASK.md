# Tarea: fachada de reservas

## Rol

`reservas.rules` ya calcula capacidad, caducidad y alerta. Se necesita una
fachada `Reservas` que encapsule capacidad, reservas y `now`. Los tests
públicos fallan porque la fachada está sin implementar.

## Requisito

Implementa `Reservas` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `Reservas(capacidad, reservas, now)`: guarda una tupla de reservas.
- `disponible() -> int`: capacidad menos reservas `active` no caducadas.
- `caducadas() -> int`: reservas `active` caducadas.
- `alerta() -> bool`: `True` si `disponible() <= 1`.
- `procesar() -> Resultado`: combina los tres valores.
- Propaga `ValueError` de capacidad o cantidad inválida.

## Restricciones

- No toques nada fuera de `reservas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
