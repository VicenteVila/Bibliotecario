# Tarea: corregir rutas

## Rol

El paquete `rutas` calcula el camino de menor coste entre dos nodos. Los tests
públicos fallan. Repara la lógica sin cambiar la API ni los tests.

## Requisito

Corrige los defectos de `rutas`. No modifiques `workspace/tests_public/` ni
los tests ocultos.

## Contrato exacto

- `procesar(aristas, inicio, fin) -> Resultado(coste, camino)`.
- `aristas` no puede estar vacío: `ValueError("grafo vacio")`.
- Cada arista debe tener `coste >= 0`; si no,
  `ValueError("coste invalido: <origen>-><destino>")`.
- `inicio` y `fin` deben aparecer en el grafo; si no,
  `ValueError("nodo desconocido: <nodo>")`.
- Si no hay camino, `ValueError("sin ruta")`.
- `inicio == fin` devuelve coste 0 y camino `(inicio,)`.
- Menor coste; en empate, camino lexicográficamente menor.
- Las aristas paralelas y los ciclos no deben romper el resultado.

## Restricciones

- No toques nada fuera de `rutas` ni los tests.
- Python 3.12; type hints; sin red ni aleatoriedad.
