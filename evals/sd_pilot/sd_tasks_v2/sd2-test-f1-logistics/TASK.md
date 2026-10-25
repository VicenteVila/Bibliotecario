# Tarea: corregir cotización logística

## Rol

El paquete `logistica` cotiza envíos por peso, volumen, distancia y express.
Los tests públicos fallan. Repara la lógica sin cambiar la API ni los tests.

## Requisito

Corrige los defectos de `logistica`. No modifiques `workspace/tests_public/` ni
los tests ocultos.

## Contrato exacto

- `procesar(Envio(peso_kg, volumen_l, distancia_km, express)) -> Resultado`.
- `peso_kg`, `volumen_l` y `distancia_km` deben ser `>= 0`; errores
  `ValueError("peso invalido")`, `"volumen invalido"`, `"distancia invalida"`.
- `base = 500 + peso_kg*20 + volumen_l*2 + distancia_km*10`.
- Express recarga el **50 % de la base**, redondeado hacia abajo.
- `total = max(1000, base + recargos)`.
- `Resultado(base, recargos, total)`.

## Restricciones

- No toques nada fuera de `logistica` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
