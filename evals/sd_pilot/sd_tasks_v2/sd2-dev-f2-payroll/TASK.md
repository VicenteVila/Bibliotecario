# Tarea: completar el servicio de nómina

## Rol

`nomina.rules` ya calcula bruto, impuesto y neto con validación. `service.py`
es una versión incompleta que ignora las horas extra al 150 % y el impuesto.
Los tests públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(Nomina(horas, tarifa_cents, horas_extra, tasa_pct)) -> Resultado`.
- Validación en `rules`; propaga sus `ValueError`.
- Horas extra al 150 %: `horas_extra * tarifa_cents * 3 // 2`.
- Impuesto: `(bruto * tasa_pct + 50) // 100`.
- `neto = bruto - impuesto`.

## Restricciones

- No toques nada fuera de `nomina` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
