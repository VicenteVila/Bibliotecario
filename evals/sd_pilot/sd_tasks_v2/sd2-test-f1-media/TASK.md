# Tarea: corregir playlist

## Rol

El paquete `media` selecciona canciones con licencia que caben en una duración
máxima. Los tests públicos fallan. Repara la lógica sin cambiar la API ni los
tests.

## Requisito

Corrige los defectos de `media`. No modifiques `workspace/tests_public/` ni los
tests ocultos.

## Contrato exacto

- `procesar(canciones, max_segundos) -> Resultado`.
- `max_segundos >= 0`; si no, `ValueError("maximo invalido")`.
- Cada canción debe tener `segundos > 0`; si no,
  `ValueError("duracion invalida: <id>")`.
- Licencias conocidas: `"libre"`, `"cc"` y `"propietaria"`; cualquier otra,
  `ValueError("licencia invalida: <id>")`.
- Selecciona en orden de entrada las canciones con licencia válida que quepan
  sin superar `max_segundos`; si una no cabe, se salta y se sigue.
- `descartadas = total de canciones - seleccionadas`.

## Restricciones

- No toques nada fuera de `media` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
