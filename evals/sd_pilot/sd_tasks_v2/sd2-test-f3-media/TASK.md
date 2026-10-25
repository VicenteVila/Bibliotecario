# Tarea: fachada de playlist

## Rol

`media.rules` ya selecciona canciones con licencia. Se necesita una fachada
`Playlist` que encapsule canciones y duración máxima. Los tests públicos fallan
porque la fachada está sin implementar.

## Requisito

Implementa `Playlist` en `service.py` reutilizando `rules.seleccionar`. No
modifiques `rules.py`, los modelos ni los tests.

## Contrato exacto

- `Playlist(canciones, max_segundos)`.
- `seleccion() -> tuple[str, ...]`: ids seleccionados.
- `total_segundos() -> int`: duración total seleccionada.
- `descartadas() -> int`: canciones no seleccionadas.
- `procesar() -> Resultado`: combina los tres valores.
- Propaga los `ValueError` de validación.

## Restricciones

- No toques nada fuera de `media` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
