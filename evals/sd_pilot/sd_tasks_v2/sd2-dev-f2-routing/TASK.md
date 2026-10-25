# Tarea: completar el servicio de rutas

## Rol

`rutas.rules` ya implementa Dijkstra con validación y desempate determinista.
`service.py` usa BFS sin costes y sin validar. Los tests públicos fallan.

## Requisito

Implementa `procesar` en `service.py` reutilizando `rules.ruta`. No modifiques
`rules.py`, los modelos ni los tests.

## Contrato exacto

- `procesar(aristas, inicio, fin) -> Resultado(coste, camino)`.
- Propaga `ValueError("grafo vacio")`, `"coste invalido: ..."`,
  `"nodo desconocido: ..."` y `"sin ruta"`.
- Menor coste; en empate, camino lexicográficamente menor.
- `inicio == fin` devuelve coste 0 y camino `(inicio,)`.

## Restricciones

- No toques nada fuera de `rutas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
