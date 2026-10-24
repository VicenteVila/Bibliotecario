"""Orden de resolución de plugins con dependencias."""
from __future__ import annotations

import heapq
from collections import defaultdict

from .errors import DependencyCycleError, MissingDependencyError
from .plugin import PluginSpec


def resolve_order(specs: dict[str, PluginSpec]) -> list[str]:
    """Orden topológico determinista (Kahn + heap).

    - Toda dependencia se carga antes que el plugin que la declara.
    - Entre los plugins ya disponibles se elige por clave
      ``(-priority, name)``: mayor prioridad primero; a igual prioridad,
      orden alfabético.
    - Dependencia no registrada -> MissingDependencyError.
    - Ciclo (incluido auto-dependencia) -> DependencyCycleError.
    - Los plugins sin relaciones (huérfanos) entran al heap cuando todas
      sus dependencias (ninguna) lo permiten, respetando la misma clave.
    """
    indegree: dict[str, int] = {name: 0 for name in specs}
    dependents: dict[str, list[str]] = defaultdict(list)
    for name, spec in specs.items():
        for dep in spec.dependencies:
            if dep not in specs:
                raise MissingDependencyError(dependent=name, missing=dep)
            indegree[name] += 1
            dependents[dep].append(name)

    heap: list[tuple[int, str]] = [
        (-specs[name].priority, name)
        for name in specs
        if indegree[name] == 0
    ]
    heapq.heapify(heap)

    order: list[str] = []
    while heap:
        _, name = heapq.heappop(heap)
        order.append(name)
        for dep_name in dependents[name]:
            indegree[dep_name] -= 1
            if indegree[dep_name] == 0:
                heapq.heappush(heap, (-specs[dep_name].priority, dep_name))

    if len(order) != len(specs):
        remaining = set(specs) - set(order)
        start = min(remaining)
        seen: dict[str, int] = {}
        cycle: list[str] = []
        cur = start
        while cur not in seen:
            seen[cur] = len(cycle)
            cycle.append(cur)
            unmet = [d for d in specs[cur].dependencies if d in remaining]
            cur = min(unmet)
        if cur == start:
            cycle.append(start)
        else:
            cycle = cycle[seen[cur] :] + [cur]
        raise DependencyCycleError(cycle)

    return order
