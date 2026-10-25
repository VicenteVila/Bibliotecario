# Tarea: completar la playlist

## Rol

`media.rules` ya selecciona canciones con licencia y valida duraciones. El
`service.py` actual ignora licencias distintas de `"propietaria"` y no valida.
Los tests públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules.seleccionar`. No
modifiques `rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(canciones, max_segundos) -> Resultado`.
- Propaga `ValueError` de máximo negativo, duración no positiva o licencia
  inválida.
- Licencias conocidas: `"libre"`, `"cc"` y `"propietaria"`; solo las dos primeras son seleccionables.
- Selección greedy en orden de entrada, sin superar `max_segundos`.
- `descartadas = total - seleccionadas`.

## Restricciones

- No toques nada fuera de `media` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
