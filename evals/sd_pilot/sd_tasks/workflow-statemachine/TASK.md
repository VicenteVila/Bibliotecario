# Tarea: workflow-statemachine — motor de transiciones del workflow de aprobaciones

## Rol

Eres ingeniero de backend en un sistema de aprobación de gastos. El paquete
`approvalflow` (en `workspace/approvalflow/`) modela el workflow con
**arquitectura ya decidida y repartida en módulos**:

- `states.py` — estados, estado inicial y estados terminales.
- `transitions.py` — tabla legal `TRANSITIONS[(estado, evento)] = (destino, guard_id | None)`.
- `guards.py` — guardas (`GUARDS[guard_id](ctx)`) y su error `GuardError`.
- `machine.py` — el motor `StateMachine` (a implementar).

El equipo de proceso ya congeló la tabla de transiciones y las guardas: **no
las modifiques**. Tu trabajo es el motor, que hoy es una versión naive que
ignora guardas y estados terminales.

## Requisito

Implementa `approvalflow.machine.StateMachine` para que cumpla el contrato
siguiente, usando la arquitectura existente (lee `states.py`,
`transitions.py` y `guards.py`; no dupliques ni hardcodees estados).

## Contrato exacto de `approvalflow.machine.StateMachine`

### Constructor y estado

- `StateMachine()` arranca en `approvalflow.states.INITIAL`.
- Propiedad `state: str` — estado actual.

### `apply(event: str, ctx: dict | None = None) -> str`

Devuelve el **nuevo estado** y actualiza la máquina. Orden de validación
estricto (para cada paso, si falla, la máquina **no cambia de estado**):

1. `event` no es `str` -> `TypeError` con mensaje exacto `event must be str`.
2. `ctx` no es `None` ni `dict` -> `TypeError` con mensaje exacto
   `ctx must be dict or None`.
3. Si `state` está en `approvalflow.states.TERMINALS` ->
   `approvalflow.machine.IllegalTransition` con mensaje exacto
   `terminal: {state}`.
4. Si `(state, event)` no está en `TRANSITIONS` ->
   `IllegalTransition` con mensaje exacto `illegal: {state} -{event}-> ?`.
5. Si la transición tiene `guard_id` (no `None`): se ejecuta
   `GUARDS[guard_id](ctx if ctx is not None else {})`. Cualquier
   `GuardError` que lance se **propaga tal cual** (el estado no cambia).
6. Se aplica el destino y se devuelve.

### Excepciones

- `approvalflow.machine.IllegalTransition(Exception)`.
- `approvalflow.guards.GuardError(Exception)` (mensaje ya definido por cada
  guarda; se propaga sin envolver).

### Workflow vigente (léelo en los módulos; aquí queda documentado)

Estados: `draft`, `submitted`, `escalated`, `manager_approved`,
`finance_approved`, `rejected`, `paid`, `cancelled`.
Inicial: `draft`. Terminales: `rejected`, `paid`, `cancelled`.

Transiciones (evento desde estado -> destino, guarda):

| desde | evento | destino | guarda |
|---|---|---|---|
| draft | submit | submitted | — |
| draft | cancel | cancelled | — |
| submitted | approve | manager_approved | `approver_not_requester` |
| submitted | reject | rejected | `note_required` |
| submitted | escalate | escalated | `amount_ge_1000` |
| submitted | cancel | cancelled | — |
| escalated | approve | finance_approved | `approver_not_requester` |
| escalated | reject | rejected | `note_required` |
| manager_approved | approve | finance_approved | — |
| manager_approved | reject | rejected | `note_required` |
| manager_approved | cancel | cancelled | — |
| finance_approved | pay | paid | — |

Guardas (firma `guard(ctx: dict) -> None`; lanzan `GuardError`):

- `note_required`: `ctx["note"]` debe ser `str` no vacío; si no:
  `note required`.
- `amount_ge_1000`: `ctx["amount"]` debe ser numérico (`int`/`float`,
  **no** `bool`); si falta o no es numérico: `amount required`; si
  `amount < 1000`: `amount below 1000` (en el borde, 1000 pasa).
- `approver_not_requester`: `ctx["approver"]` y `ctx["requester"]` deben
  existir (si no: `approver and requester required`); si son iguales:
  `approver equals requester`.

## Restricciones

- Solo puedes cambiar/crear dentro de `workspace/approvalflow/` (normalmente
  `machine.py`; y tests tuyos). `states.py`, `transitions.py` y `guards.py`
  son intocables.
- Sin red, sin fechas reales, sin aleatoriedad: todo determinista.
- Compatible con Python 3.12; estilo del paquete (type hints, español).

## Ejes de dureza

- Casos límite exigentes (terminales, bordes de guarda, inmutabilidad ante error).
- Lectura de arquitectura existente (motor genérico sobre la tabla de módulos).
