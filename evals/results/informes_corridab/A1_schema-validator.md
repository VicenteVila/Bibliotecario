# Informe de celda A1_schema-validator

## LLM turno 0
- input_tokens=2508 output_tokens=680
- respuesta: "###FILE: jsonval/validator.py###\n\"\"\"Validador de esquemas (versión completa).\"\"\"\nfrom __future__ import annotations\n\nfrom jsonval.paths import ROOT, index, key\nfrom jsonval.types import matches, type_name\n\n\ndef validate(data: object, schema: dict) -> list[str]:\n    \"\"\"Valida data contra schema y devuelve lista de errores.\"\"\"\n    if not isinstance(schema, dict):\n        rais
--- turno 1 ---
