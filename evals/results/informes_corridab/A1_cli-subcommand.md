# Informe de celda A1_cli-subcommand

## LLM turno 0
- input_tokens=3934 output_tokens=1377
- respuesta: "###FILE: stockcli/parser.py###\n\"\"\"Parser de argv de la CLI.\"\"\"\nfrom __future__ import annotations\n\nfrom dataclasses import dataclass\n\nfrom stockcli.errors import UsageError\n\nVALID_STATUS = (\"OK\", \"LOW\", \"OUT\")\n\n\n@dataclass(frozen=True)\nclass Command:\n    \"\"\"Comando parseado: nombre + opciones normalizadas.\"\"\"\n\n    name: str\n    options: dict[str, str | int]\n\n\n
--- turno 1 ---
