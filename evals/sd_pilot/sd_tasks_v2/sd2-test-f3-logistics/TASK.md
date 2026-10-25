# Tarea: fachada de cotización logística

## Rol

`logistica.rules` ya calcula base, recargo express y mínimo. Se necesita una
fachada `Cotizador` que encapsule un `Envio`. Los tests públicos fallan porque
la fachada está sin implementar.

## Requisito

Implementa `Cotizador` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `Cotizador(envio)`.
- `base() -> int`: base del envío.
- `recargos() -> int`: 50 % de la base si es express, si no 0.
- `total() -> int`: `max(1000, base + recargos)`.
- `procesar() -> Resultado`: combina los tres valores.
- Propaga los `ValueError` de validación.

## Restricciones

- No toques nada fuera de `logistica` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
