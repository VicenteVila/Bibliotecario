# Informe de celda A1_plugin-registry

## LLM turno 0
- input_tokens=2470 output_tokens=634
- respuesta: "###FILE: plugin_registry/resolver.py###\n\"\"\"Orden de resolución de plugins (versión inicial simplificada).\"\"\"\nfrom __future__ import annotations\n\nfrom .errors import DependencyCycleError, MissingDependencyError\nfrom .plugin import PluginSpec\n\n\ndef resolve_order(specs: dict[str, PluginSpec]) -> list[str]:\n    \"\"\"Devuelve los nombres de plugin en orden de carga.\n\n    Versión inic
--- turno 1 ---
