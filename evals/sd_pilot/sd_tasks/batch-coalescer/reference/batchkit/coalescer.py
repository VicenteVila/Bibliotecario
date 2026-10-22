"""Coalescencia de lotes con ventana temporal."""
from __future__ import annotations

from collections import deque
from collections.abc import Callable


class BatchCoalescer:
    """Agrupa items en lotes; la ventana la decide el reloj inyectado."""

    def __init__(
        self,
        window: float,
        clock: Callable[[], float],
        max_size: int | None = None,
    ) -> None:
        if not isinstance(window, (int, float)) or isinstance(window, bool):
            raise TypeError("window must be a number")
        if window <= 0:
            raise ValueError("window must be > 0")
        if not callable(clock):
            raise TypeError("clock must be callable")
        if max_size is not None:
            if not isinstance(max_size, int) or isinstance(max_size, bool):
                raise TypeError("max_size must be an integer")
            if max_size < 1:
                raise ValueError("max_size must be >= 1")
        self._window = float(window)
        self._clock = clock
        self._max_size = max_size
        self._open_items: list[str] = []
        self._open_ts: float | None = None
        self._ready: deque[list[str]] = deque()

    def add(self, item: str, ts: float | None = None) -> None:
        """Añade un item al lote abierto (y lo cierra si alcanza max_size)."""
        if not isinstance(item, str):
            raise TypeError("item must be str")
        if ts is not None:
            if not isinstance(ts, (int, float)) or isinstance(ts, bool):
                raise TypeError("ts must be a number")
            when = float(ts)
        else:
            when = float(self._clock())
        if self._open_ts is None:
            self._open_ts = when
        self._open_items.append(item)
        if self._max_size is not None and len(self._open_items) >= self._max_size:
            self._ready.append(self._open_items)
            self._open_items = []
            self._open_ts = None

    def _close_expired(self) -> None:
        if self._open_ts is None:
            return
        now = float(self._clock())
        if now - self._open_ts >= self._window:
            self._ready.append(self._open_items)
            self._open_items = []
            self._open_ts = None

    def poll(self) -> list[list[str]]:
        """Entrega los lotes cerrados (por tamaño o por ventana vencida)."""
        self._close_expired()
        lotes = list(self._ready)
        self._ready.clear()
        return lotes

    def flush(self) -> list[list[str]]:
        """Entrega todo lo pendiente, incluido el lote abierto."""
        self._close_expired()
        lotes = list(self._ready)
        self._ready.clear()
        if self._open_items:
            lotes.append(self._open_items)
            self._open_items = []
            self._open_ts = None
        return lotes

    @property
    def pending(self) -> int:
        """Items aún no entregados (listos + abiertos)."""
        return sum(len(lote) for lote in self._ready) + len(self._open_items)
