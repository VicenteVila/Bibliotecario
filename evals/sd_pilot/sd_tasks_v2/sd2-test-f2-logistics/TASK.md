# Tarea: completar la cotización logística

## Rol

`logistica.rules` ya calcula base, recargo express y mínimo. `service.py` es
una versión incompleta que ignora express, mínimo y validación. Los tests
públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(Envio(...)) -> Resultado`.
- Propaga los `ValueError` de peso, volumen o distancia negativos.
- Express recarga el 50 % de la base.
- `total = max(1000, base + recargos)`.

## Restricciones

- No toques nada fuera de `logistica` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
