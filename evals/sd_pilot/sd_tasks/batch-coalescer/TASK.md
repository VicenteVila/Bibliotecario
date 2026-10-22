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
