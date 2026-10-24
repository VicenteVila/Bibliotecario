# Tarea B: interval-scheduler-seeded-bugs-billing-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: planificador de intervalos con recursos

## Rol

Eres ingeniero de un sistema de agendado que reparte "intervalos" (turnos,
sesiones, reservas) entre "recursos" limitados (salas, máquinas, personal).
El paquete `agenda` ya contiene el modelo de datos, la gestión de recursos y
un módulo consumidor (`consumidor.py`) que llama al planificador: ese
consumidor define la semántica observable que no puedes romper. Tu trabajo es
implementar el corazón: `planificador.py`.

## Requisito

Implementa `agenda/planificador.py` (función `planificar`) ajustándote
**exactamente** al contrato siguiente. No modifiques `modelo.py`,
`recurso.py` ni `consumidor.py`: léelos; en particular, `consumidor.py` es
el cliente real del planificador y sus expectativas (claves de
estadísticas, determinismo, entradas vacías) forman parte del contrato.

## API

```python
from agenda.planificador import planificar

def planificar(
    intervalos: Iterable[Intervalo],
    recursos: Iterable[Recurso],
    ventana: tuple[int, int] | None = None,
) -> Plan: ...
```

Tipos (definidos en `agenda.modelo` y `agenda.recurso`; no los toques):

- `Intervalo(identificador: str, inicio: int, fin: int, prioridad: int = 0)`
- `Recurso(nombre: str, capacidad: int)`
- `Asignacion(intervalo, recurso)` — `recurso` es el **nombre** (str) del
  recurso asignado.
- `Rechazo(intervalo, motivo)` — `motivo` es una clave exacta (ver abajo).
- `Plan(asignaciones, rechazados, estadisticas)` — secuencias en orden de
  decisión y dict de estadísticas.

## Validación (antes de planificar)

Se validan **todos** los recursos y todos los intervalos **antes** de
asignar nada. Los errores son `ValueError` con mensaje exacto:

1. Recursos, en orden de entrada: `capacidad` debe ser `>= 1`; si no,
   `capacidad invalida: {nombre}`.
2. Identificadores de intervalo duplicados (en orden de entrada; se detecta
   el segundo y sucesivos): `intervalo duplicado: {identificador}`.
3. Cada intervalo, en orden de entrada: primero `inicio <= fin` (duración
   0 permitida); si no, `intervalo invertido: {identificador}`. Después
   `prioridad >= 0`; si no, `prioridad negativa: {identificador}`.

## Semántica de ocupación (semiabierta)

- Un intervalo ocupa su recurso en el conjunto semiabierto
  `[inicio, fin)`. **Dos intervalos solapan solo si sus rangos semiabiertos
  se intersecan de forma no vacía**: `[0,5)` y `[5,10)` NO solapan;
  `[0,5)` y `[4,10)` sí. Un intervalo de duración 0 (`[5,5)`) no ocupa
  capacidad en ningún instante, por lo que siempre cabe (si es elegible).
- Un recurso admite hasta `capacidad` intervalos simultáneos en cada
  instante.

## Ventana

- `ventana = None`: sin límites.
- `ventana = (desde, hasta)`: el intervalo es elegible solo si
  `desde <= inicio` y `fin <= hasta` (los bordes cuentan). Si no,
  se rechaza con motivo `fuera_de_ventana` **antes** de intentar asignación.
- Una ventana vacía o una lista de intervalos vacía produce un `Plan` con
  ambas secuencias vacías y estadísticas en cero (sin excepción, con o sin
  recursos).

## Orden de decisión y asignación

- Los intervalos elegibles se procesan en orden de **clave de decisión**:
  1. prioridad descendente (mayor primero),
  2. inicio ascendente,
  3. duración (`fin - inicio`) ascendente,
  4. identificador ascendente (orden lexicográfico).
- Cada intervalo se asigna al **primer recurso, en orden de nombre
  ascendente**, que tenga capacidad libre durante todo su tramo. Si ningún
  recurso cabe, se rechaza con motivo `sin_recurso_disponible`.
- `Plan.asignaciones` y `Plan.rechazados` conservan el orden de decisión.
- La función es pura y determinista: no usa reloj, red ni aleatoriedad.

## Estadísticas

`Plan.estadisticas` es exactamente un dict con estas claves:

```python
{
    "asignados": int,          # nº de asignaciones
    "rechazados": int,         # nº de rechazados
    "motivos": dict[str, int], # solo motivos presentes: fuera_de_ventana y/o sin_recurso_disponible
    "uso_por_recurso": dict[str, int],  # para cada recurso (nombre): máximo nº de
                                        # intervalos asignados simultáneos en un
                                        # instante (0 si no se usa; los de
                                        # duración 0 no cuentan)
}
```

## Módulo consumidor existente (`agenda/consumidor.py`) — léelo, no lo toques

`CoordinadorSala(capacidad)` programa contra un único recurso llamado
`sala`. Su método `programar(intervalos, desde, hasta)` llama a
`planificar` con ventana y devuelve el `Plan`; `resumen(plan)` devuelve
`{"ocupacion_maxima", "asignados", "rechazados"}` leyendo las claves de
estadísticas anteriores. Cualquier cambio en los nombres de claves o en la
semántica rompe este consumidor.

## Restricciones

- Solo implementas `planificador.py` (y tus tests). El resto es intocable.
- Sin red, sin fechas reales, sin aleatoriedad. Python 3.12, estilo del
  repo (type hints, dataclasses, identificadores en español).

---

## PARTE B

# Tarea: pipeline de facturación con defectos que hay que diagnosticar

## Rol

Eres ingeniero manteniendo el módulo de facturación de un negocio. El
paquete `facturacion` calcula subtotales, descuentos, IVA y emite facturas
con folio correlativo. **El paquete contiene exactamente 3 defectos, repartidos
en 3 ficheros distintos del paquete** (`impuestos.py`, `totales.py`,
`emitir.py`). Los tests públicos de `tests_public/` fallan ahora mismo y
evidencian los defectos.

## Requisito

Diagnostica los 3 defectos a partir de las **salidas de fallo de los
tests públicos** y de la lectura de todo el paquete, y corrige el **código**
para que el pipeline cumpla **exactamente** el contrato siguiente. No
corrijas ni modifiques los tests: son la especificación ejecutable. No
modifiques `modelos.py` salvo si fuera imprescindible (no debería serlo:
es correcto). Cada defecto está en un fichero distinto de los tres citados.

## Unidades y determinismo

- Todos los importes están en **céntimos enteros** (`int`). No hay floats
  en la API ni en los resultados.
- Sin fechas reales: el año de emisión se pasa explícitamente. Sin red ni
  aleatoriedad.

## Contrato exacto

### `modelos.py` (ya correcto; léelo)

- `Cliente(cif: str, nombre: str, exento_iva: bool = False)`
- `Linea(descripcion: str, cantidad: int, precio_unit_cents: int)`
- `Factura` dataclass con campos: `cliente`, `lineas` (tupla), `folio`,
  `anio`, `subtotal_cents`, `descuento_pct`, `base_cents`, `iva_cents`,
  `total_cents`.

### `totales.py`

- `subtotal_cents(lineas) -> int`: suma de `cantidad * precio_unit_cents`.
  Valida cada línea, en orden: `cantidad >= 1` o
  `ValueError("cantidad no positiva: {cantidad}")`; `precio_unit_cents >= 0`
  o `ValueError("precio negativo: {precio}")`.
- `descuento_por_volumen_pct(num_lineas: int) -> int`:
  - `num_lineas < 5` → `0`
  - `5 <= num_lineas < 10` → `5`
  - `num_lineas >= 10` → `10`
  (los umbrales son **incluyentes**: 5 líneas dan 5%, 10 líneas dan 10%).
- `descuento_cents(monto: int, pct: int) -> int`: **half-up exacto en
  céntimos**, fórmula obligatoria `(monto * pct + 50) // 100`. NUNCA
  `round()` de Python (usa redondeo bancario: `round(262.5) == 262`).
- `base_imponible_cents(lineas, descuento_extra_pct: int = 0) -> int`:
  `subtotal - descuento_cents(subtotal, pct_total)` donde
  `pct_total = descuento_por_volumen_pct(len(lineas)) + descuento_extra_pct`;
  si `pct_total > 100` → `ValueError("descuento total invalido: {pct_total}")`.

### `impuestos.py`

- `TASA_IVA_DEFECTO = 21`
- `iva_cents(base_cents: int, tasa_pct: int = TASA_IVA_DEFECTO) -> int`:
  mismo redondeo half-up obligatorio: `(base_cents * tasa_pct + 50) // 100`.
  NUNCA `round()`.

### `emitir.py`

- `class Emisor`: mantiene la secuencia de folios por año.
  `siguiente_folio(anio: int) -> str` devuelve `f"F-{anio}-{n:04d}"` con
  `n` empezando en **1** en el primer folio de cada año y correlativo
  después (por año, independientes: `F-2024-0001`, `F-2025-0001`, ...).
- `emitir(emisor, cliente, lineas, anio, descuento_extra_pct=0) -> Factura`:
  1. `lineas` vacío → `ValueError("sin lineas")`.
  2. `subtotal = subtotal_cents(lineas)` (valida).
  3. `descuento_pct = descuento_por_volumen_pct(len(lineas)) + descuento_extra_pct`;
     `> 100` → el ValueError de `base_imponible_cents`.
  4. `base = base_imponible_cents(lineas, descuento_extra_pct)`.
  5. `iva = 0` si `cliente.exento_iva`, si no `iva_cents(base)`.
  6. `total = base + iva`.
  7. `folio = emisor.siguiente_folio(anio)` (el folio se toma **una sola
     vez** por factura emitida).

## Restricciones

- No toques nada fuera del paquete `facturacion` y tus tests.
- Compatible con Python 3.12, estilo del repo (type hints, dataclasses,
  identificadores en español).
