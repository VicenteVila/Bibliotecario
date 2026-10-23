# Informe de celda A1_batch-coalescer

## LLM turno 0
- input_tokens=2211 output_tokens=896
- respuesta: "###FILE: batchkit/coalescer.py###\n\"\"\"Coalescencia de lotes con ventana temporal (esqueleto inicial).\"\"\"\nfrom __future__ import annotations\n\nfrom collections import deque\nfrom collections.abc import Callable\n\n\ndef _is_number(value: object) -> bool:\n    \"\"\"Return True if value is int or float but not bool.\"\"\"\n    return isinstance(value, (int, float)) and not isinstance(value,
--- turno 1 ---
