# Tarea: fachada de nómina

## Rol

`nomina.rules` ya calcula bruto, impuesto y neto. Se necesita una fachada
`CalculoNomina` que encapsule una `Nomina`. Los tests públicos fallan porque
la fachada está sin implementar.

## Requisito

Implementa `CalculoNomina` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `CalculoNomina(nomina)`.
- `bruto() -> int`: regla de horas y extras.
- `impuesto() -> int`: impuesto sobre el bruto.
- `neto() -> int`: bruto menos impuesto.
- `procesar() -> Resultado`: combina los tres valores.
- Propaga los `ValueError` de validación de `rules`.

## Restricciones

- No toques nada fuera de `nomina` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
