# Tarea: fachada de rutas

## Rol

`rutas.rules` ya implementa el camino de menor coste. Se necesita una fachada
`Rutas` que encapsule aristas, inicio y fin. Los tests públicos fallan porque
la fachada está sin implementar.

## Requisito

Implementa `Rutas` en `service.py` reutilizando `rules.ruta`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `Rutas(aristas, inicio, fin)`: guarda una tupla de aristas.
- `ruta() -> Resultado`: delega en `rules.ruta`.
- `procesar() -> Resultado`: alias de `ruta()`.
- Propaga `ValueError` de grafo vacío, coste inválido, nodo desconocido o sin
  ruta.

## Restricciones

- No toques nada fuera de `rutas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
