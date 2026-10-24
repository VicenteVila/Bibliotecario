# Tarea B: workflow-statemachine-batch-coalescer-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

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

---

## PARTE B

# Tarea: batch-coalescer — coalescencia de lotes con ventana temporal

## Rol

Eres ingeniero de backend en un sistema de ingesta de eventos. El paquete
`batchkit` (en `workspace/batchkit/`) agrupa items en lotes para envío
por lotes. `batchkit/clock.py` define el protocolo de reloj y `ManualClock`,
un reloj manual determinista para tests y uso en general (el reloj es
**siempre inyectado**: el paquete no usa `time` real en ningún sitio y así
debe seguir siendo).

## Requisito

Implementa `batchkit.coalescer.BatchCoalescer` (hoy es un esqueleto) para
que cumpla exactamente el contrato siguiente. Determinismo absoluto: la
única fuente de tiempo es el reloj inyectado.

## Contrato exacto de `batchkit.coalescer.BatchCoalescer`

### Constructor

```python
BatchCoalescer(window: float, clock: Callable[[], float], max_size: int | None = None)
```

Validaciones, en este orden:

1. `window` no es numérico (`int`/`float`; **`bool` no cuenta**) ->
   `TypeError` con mensaje exacto `window must be a number`.
2. `window <= 0` -> `ValueError` con mensaje exacto `window must be > 0`.
3. `clock` no es callable -> `TypeError` con mensaje exacto
   `clock must be callable`.
4. `max_size` no es `None` y no es entero (`bool` no cuenta) ->
   `TypeError` con mensaje exacto `max_size must be an integer`.
5. `max_size` no es `None` y `max_size < 1` -> `ValueError` con mensaje
   exacto `max_size must be >= 1`.

### Modelo

- Solo hay **un lote abierto** a la vez. El lote abierto lleva sus items
  (en orden de inserción) y su `first_ts`: el timestamp efectivo del
  **primer** item que lo abrió.
- Timestamp efectivo de un `add`: el argumento `ts` si no es `None`, si no
  `clock()`. Los `add` posteriores **no** cambian el `first_ts` del lote
  abierto (aunque su `ts` sea menor o mayor).
- Hay una cola FIFO de lotes **listos** (cerrados y aún no entregados).

### `add(item: str, ts: float | None = None) -> None`

1. `item` no es `str` -> `TypeError` con mensaje exacto `item must be str`.
2. `ts` no es `None` y no es numérico (`bool` no cuenta) -> `TypeError`
   con mensaje exacto `ts must be a number`.
3. El item entra al lote abierto (creándolo si no lo hay, con
   `first_ts` = timestamp efectivo de ese item).
4. Si `max_size` no es `None` y el lote abierto alcanzó `max_size` items,
   el lote **se cierra inmediatamente** (pasa a la cola de listos) y el
   siguiente `add` abrirá uno nuevo con su propio `first_ts`.

### `poll() -> list[list[str]]`

- Cierra el lote abierto si `clock() - first_ts >= window` (borde
  incluido: en el instante exacto ya está vencido).
- Devuelve **todos** los lotes listos, en orden FIFO de cierre, y vacía
  la cola. Un lote cerrado por `max_size` se entrega en el primer
  `poll()` **sin** comprobar la ventana.
- Sin lotes listos -> `[]`. Nunca se entregan lotes vacíos.

### `flush() -> list[list[str]]`

- Entrega la cola de listos (FIFO) y, si hay lote abierto, lo cierra y lo
  entrega el último. La cola queda vacía y el estado de lotes se reinicia.
- Sin nada pendiente -> `[]`. Nunca se entregan lotes vacíos.

### `pending: int` (property)

Número de items aún no entregados (cola de listos + lote abierto).

### Ejemplo canónico

```python
reloj = ManualClock(0.0)
co = BatchCoalescer(window=5.0, clock=reloj, max_size=None)
co.add("a")                 # lote abierto [a], first_ts=0
reloj.advance(2.0)
co.add("b")                 # sigue abierto [a, b], first_ts=0
co.poll()                   # []  (now-first_ts=2 < 5)
reloj.advance(3.0)          # now=5; 5-0>=5
co.poll()                   # [["a", "b"]]
co.flush()                  # []
```

## Restricciones

- Solo puedes cambiar/crear dentro de `workspace/batchkit/` (normalmente
  `coalescer.py`; y tests tuyos). `clock.py` es intocable.
- Sin red, sin fechas reales, sin aleatoriedad, **sin `time` real**: usa
  el reloj inyectado.
- Compatible con Python 3.12; estilo del paquete (type hints, español).

## Ejes de dureza

- Casos límite exigentes (borde de ventana, `max_size`, FIFO, ts stale).
- Contrato de API estricto (mensajes de error y semántica de entrega).
