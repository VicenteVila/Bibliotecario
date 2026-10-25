# Tarea: fachada de agenda médica

## Rol

`agenda.rules` ya asigna citas por prioridad. Se necesita una fachada `Agenda`
que encapsule slots y citas. Los tests públicos fallan porque la fachada está
sin implementar.

## Requisito

Implementa `Agenda` en `service.py` reutilizando `rules.asignar`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `Agenda(slots, citas)`: guarda tuplas.
- `asignar() -> Resultado`: delega en `rules.asignar`.
- `pendientes() -> int`: número de citas sin slot.
- `procesar() -> Resultado`: alias de `asignar()`.
- Propaga los `ValueError` de validación.

## Restricciones

- No toques nada fuera de `agenda` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
