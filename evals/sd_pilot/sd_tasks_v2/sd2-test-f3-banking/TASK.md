# Tarea: fachada del libro con estado

## Rol

El paquete `ledger` ya tiene funciones de saldo, registro e informes. Ahora se
necesita una fachada con estado, `Ledger`, que encapsule la cuenta y sus
asientos. Los tests públicos de `tests_public/` fallan porque la fachada está
sin implementar.

## Requisito

Implementa `Ledger` en `service.py` reutilizando las funciones existentes. No
modifiques los tests ni `posting.py`, `reports.py` o `fees.py`.

## Contrato exacto

- `Ledger(cuenta: Cuenta, asientos: Iterable[Asiento])`: guarda una copia de la
  secuencia de asientos; no comparte la lista original.
- `saldo() -> int`: `balance_cents` de la cuenta y los asientos internos.
- `registrar(asiento) -> None`: usa `post` para añadir el asiento; propaga sus
  `ValueError` y no muta el estado si falla.
- `informe() -> int`: `balance_after` de la cuenta y los asientos internos.
- `asientos_actuales() -> tuple[Asiento, ...]`: tupla con los asientos
  internos actuales.

## Restricciones

- No toques nada fuera de `ledger` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
