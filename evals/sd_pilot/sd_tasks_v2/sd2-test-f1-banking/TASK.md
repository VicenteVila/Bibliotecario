# Tarea: libro de movimientos bancarios

## Rol

Mantienes el paquete `ledger` de un banco. Los movimientos se registran como
asientos; solo los `"posted"` afectan al saldo. El paquete contiene defectos
en el código. Los tests públicos de `tests_public/` fallan ahora y muestran
parte del comportamiento incorrecto.

## Requisito

Diagnostica los defectos ejecutando los tests públicos y leyendo el paquete.
Corrige **solo el código** para cumplir el contrato. No modifiques los tests.

## Contrato exacto

### `models.py` (correcto; léelo)

- `Cuenta(cuenta_id: str, balance_cents: int, overdraft_limit_cents: int)`
- `Asiento(asiento_id: str, cuenta_id: str, amount_cents: int,
  status: str = "posted")`
- `status` solo puede ser `"posted"`, `"pending"` o `"reversed"`.

### `fees.py`

- `fee_cents(amount_cents: int, rate_bps: int) -> int`: comisión en céntimos
  con **half-up exacto**, fórmula obligatoria
  `(amount_cents * rate_bps + 5000) // 10000`. NUNCA `round()` de Python
  (redondeo bancario).

### `posting.py`

- `balance_cents(cuenta, asientos) -> int`: `cuenta.balance_cents` más la suma
  de `amount_cents` de los asientos con `status == "posted"`. Pendientes y
  revertidos no cuentan.
- `post(cuenta, asientos, nuevo) -> tuple[Asiento, ...]`: devuelve una tupla
  nueva con `nuevo` al final. Si ya existe un asiento con el mismo
  `asiento_id` (en cualquier estado), lanza
  `ValueError(f"asiento duplicado: {nuevo.asiento_id}")`. Calcula el saldo
  resultante; si queda **estrictamente por debajo** de
  `-cuenta.overdraft_limit_cents`, lanza
  `ValueError("limite de descubierto excedido")`. El límite exacto **está
  permitido** (no lanza).

### `reports.py`

- `balance_after(cuenta, asientos) -> int`: saldo después de aplicar solo los
  asientos `"posted"`. Es el mismo criterio que `balance_cents`, pero el
  informe no debe incluir pendientes ni revertidos.

## Restricciones

- No toques nada fuera de `ledger` ni los tests.
- Python 3.12; type hints; identificadores en español; sin red ni aleatoriedad.
