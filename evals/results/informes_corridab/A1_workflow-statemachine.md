# Informe de celda A1_workflow-statemachine

## LLM turno 0
- input_tokens=2582 output_tokens=407
- respuesta: "###FILE: approvalflow/machine.py###\n\"\"\"Motor de transiciones del workflow (versión inicial naive).\"\"\"\nfrom __future__ import annotations\n\nfrom approvalflow.states import INITIAL, TERMINALS\nfrom approvalflow.transitions import TRANSITIONS\nfrom approvalflow.guards import GUARDS, GuardError\n\n\nclass IllegalTransition(Exception):\n    \"\"\"Transición no permitida desde el estado actual
--- turno 1 ---
