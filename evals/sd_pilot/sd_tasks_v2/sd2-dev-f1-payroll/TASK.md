# Tarea: corregir cálculo de nómina

## Rol

El paquete `nomina` calcula bruto, impuesto y neto. Los tests públicos fallan.
Repara la lógica sin cambiar la API ni los tests.

## Requisito

Corrige los defectos de `nomina`. No modifiques `workspace/tests_public/` ni
los tests ocultos.

## Contrato exacto

- `procesar(Nomina(horas, tarifa_cents, horas_extra, tasa_pct)) -> Resultado`.
- `horas >= 0`, `tarifa_cents >= 0`, `horas_extra >= 0`, `0 <= tasa_pct <= 100`.
- Errores: `ValueError("horas invalidas")`, `"tarifa invalida"`,
  `"horas extra invalidas"`, `"tasa invalida"`.
- Cada hora extra se paga al 150 % de la tarifa.
- `bruto = horas * tarifa + horas_extra * tarifa * 3 // 2`.
- `impuesto` redondea al centavo más cercano hacia arriba:
  `(bruto * tasa_pct + 50) // 100`.
- `neto = bruto - impuesto`.

## Restricciones

- No toques nada fuera de `nomina` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
