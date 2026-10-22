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
