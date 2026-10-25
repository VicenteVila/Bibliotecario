# Tarea: corregir agenda médica

## Rol

El paquete `agenda` asigna citas pendientes a slots disponibles por prioridad.
Los tests públicos fallan. Repara la lógica sin cambiar la API ni los tests.

## Requisito

Corrige los defectos de `agenda`. No modifiques `workspace/tests_public/` ni
los tests ocultos.

## Contrato exacto

- `procesar(slots, citas) -> Resultado(asignadas, pendientes)`.
- Los slots deben ser `>= 0` y no repetirse; errores
  `ValueError("slot invalido: <slot>")` y `"slot duplicado: <slot>"`.
- Los ids de cita no se repiten, aunque estén canceladas; error
  `ValueError("cita duplicada: <id>")`.
- Prioridad entre 1 y 3; error `ValueError("prioridad invalida: <id>")`.
- Solo las citas `pending` se asignan.
- Orden: prioridad ascendente y, en empate, `cita_id` lexicográfico.
- Los slots se usan en orden ascendente.
- `pendientes` cuenta las citas que no obtuvieron slot.

## Restricciones

- No toques nada fuera de `agenda` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
