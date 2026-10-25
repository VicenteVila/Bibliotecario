# Tarea: reversión de asientos bancarios

## Rol

El paquete `ledger` ya registra asientos y calcula saldos. Falta completar la
reversión de un asiento. Los tests públicos de `tests_public/` fallan ahora y
muestran parte del contrato.

## Requisito

Completa `reversal.py` para que cumpla el contrato. No modifiques los tests ni
el resto del paquete.

## Contrato exacto

### `reversal.py`

- `reverse_entry(asiento, motivo) -> Asiento`: solo admite asientos con
  `status == "posted"`; si no,
  `ValueError("solo se revierten asientos posted")`. Si `motivo` está vacío,
  `ValueError("motivo requerido")`. Devuelve un asiento nuevo con
  `asiento_id=f"rev-{asiento.asiento_id}"`, mismo `cuenta_id`,
  `amount_cents=-asiento.amount_cents` y `status="posted"`.
- `apply_reversal(cuenta, asientos, asiento_id, motivo) -> tuple[Asiento, ...]`:
  busca el asiento por `asiento_id`; si no existe,
  `ValueError(f"asiento no encontrado: {asiento_id}")`. Si ya existe un asiento
  `rev-{asiento_id}`, `ValueError("asiento ya revertido")`. En caso contrario
  devuelve una tupla nueva con el reverso al final. No muta la secuencia
  original.

## Restricciones

- No toques nada fuera de `ledger` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
