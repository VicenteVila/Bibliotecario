# Informe de celda A1_interval-scheduler

## LLM turno 0
- input_tokens=3685 output_tokens=1310
- respuesta: "###FILE: agenda/planificador.py###\n\"\"\"Planificador de intervalos con recursos.\"\"\"\n\nfrom __future__ import annotations\n\nfrom collections.abc import Iterable\n\nfrom agenda.modelo import Asignacion, Intervalo, Plan, Rechazo\nfrom agenda.recurso import Recurso\n\n\ndef planificar(\n    intervalos: Iterable[Intervalo],\n    recursos: Iterable[Recurso],\n    ventana: tuple[int, int] | None 
--- turno 1 ---
