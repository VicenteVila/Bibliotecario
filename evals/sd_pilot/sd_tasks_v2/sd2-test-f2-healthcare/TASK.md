# Tarea: completar la agenda médica

## Rol

`agenda.rules` ya asigna citas por prioridad y valida slots e ids. `service.py`
ordena solo por id y no valida. Los tests públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules.asignar`. No
modifiques `rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(slots, citas) -> Resultado(asignadas, pendientes)`.
- Propaga los `ValueError` de slots inválidos o duplicados, citas duplicadas y
  prioridades fuera de 1..3.
- Solo citas `pending`; orden por prioridad y luego `cita_id`.
- Slots en orden ascendente.
- `pendientes` cuenta las citas sin slot.

## Restricciones

- No toques nada fuera de `agenda` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
