# Tarea B: repo-cache-layer-dsl-parser-b — monorepo con dos paquetes

Esta tarea endurece el alcance: el repositorio contiene **dos paquetes independientes** y ambos contratos deben cumplirse. Los tests públicos de cada paquete son una guía incompleta; la especificación ejecutable son las dos partes de este documento.

## PARTE A

# Tarea: capa de caché TTL para el repositorio del catálogo

## Rol

Eres ingeniero de backend en un proyecto de gestión de biblioteca. El paquete
`catalogo` ya existe y funciona: tiene modelos, una capa de persistencia
SQLite (`db.py`), DAOs (`daos.py`) y un servicio de alto nivel
(`servicio.py`). El servicio consulta los DAOs en cada llamada y eso es un
problema de rendimiento en lecturas repetidas.

## Requisito

Implementa la capa de caché `catalogo/cache.py` (clase `CacheTTL`) de forma
que **se ajuste exactamente al contrato siguiente**, y deja que
`catalogo/servicio.py` la use tal como ya está diseñado para usarla. No
modifiques los módulos `modelos.py`, `db.py`, `daos.py` ni `servicio.py`:
son la arquitectura existente y su comportamiento es el correcto. Tu trabajo
es hacer que `CacheTTL` cumpla el contrato y encaje con el servicio.

El código debe ser determinista y sin E/S externa: la única fuente de tiempo
es el reloj inyectado en el constructor.

## Contrato exacto de `catalogo.cache.CacheTTL`

### Constructor

```python
CacheTTL(capacidad: int, reloj: Callable[[], float])
```

- `capacidad`: número máximo de entradas vivas simultáneas. Debe ser `>= 1`;
  si no se cumple se lanza `ValueError` con el mensaje exacto
  `capacidad debe ser >= 1`.
- `reloj`: función sin argumentos que devuelve el tiempo actual en segundos
  (puede ser un reloj falso de los tests). Es obligatoria.

### `obtener(clave: str) -> tuple[bool, Any]`

- Si `clave` no está almacenada o su TTL ya venció, devuelve
  `(False, None)`.
- Si `clave` está almacenada y no ha vencido, devuelve `(True, valor)` y la
  entrada pasa a ser la **más reciente** en el orden LRU.
- Una entrada expirada detectada al consultar se **elimina** en ese momento
  (purga perezosa) y se incrementan **dos** contadores: `expiraciones` (+1) y
  `fallos` (+1).
- **Borde del TTL**: una entrada escrita en el instante `t0` con `ttl` vence
  cuando `reloj() >= t0 + ttl`. Es decir, justo en el instante límite ya está
  expirada (no es un acierto).
- Un valor `None` almacenado es un valor normal: `obtener` devuelve
  `(True, None)` (acielo), no se confunde con una ausencia.

### `poner(clave: str, valor: Any, ttl: float) -> None`

- `ttl` debe ser `> 0`; si no se cumple se lanza `ValueError` con el mensaje
  exacto `ttl debe ser > 0`.
- Inserta o **reemplaza** la entrada. Reemplazar reinicia su expiración
  (nuevo `t0` = reloj actual) y la coloca como la más reciente (LRU).
- Tras insertar, si el tamaño supera `capacidad`, se **expulsa la entrada
  menos recientemente usada** (orden LRU: el orden de uso se marca con
  `obtener` y `poner`, ambos cuentan como uso) y se incrementa `evicciones`
  (+1 por entrada expulsada).
- Guardar `None` es permitido.

### `invalidar_prefijo(prefijo: str) -> int`

- Elimina **todas** las cuyos nombres **comiencen por** `prefijo`
  (`str.startswith`), incluida una clave idéntica al prefijo. NO se mira si
  han expirado: se eliminan igualmente y **sin** incrementar `expiraciones`.
- `prefijo == ""` elimina todas las entradas.
- Devuelve el número de entradas eliminadas.
- No modifica los contadores de aciertos/fallos.

### `estadisticas() -> dict[str, int]`

Devuelve exactamente estas seis claves, todas enteras:

```python
{"aciertos": int, "fallos": int, "expiraciones": int,
 "evicciones": int, "tamano": int, "capacidad": int}
```

- `tamano` = entradas vivas en el mapa (incluye las que ya vencieron pero
  aún no se han purgado; la consulta de estadísticas **no** debe purgarlas
  ni debe tocar ningún contador).
- `capacidad` = la capacidad fijada en el constructor.

### `limpiar() -> None`

- Elimina todas las entradas y pone a cero `aciertos`, `fallos`,
  `expiraciones` y `evicciones`. La `capacidad` no cambia.

## Contrato del servicio (`catalogo.servicio.CatalogoService`) — léelo, no lo toques

El servicio ya está escrito sobre la caché y define las claves y los TTLs.
Debes conocerlos porque son parte del contrato observable del sistema:

- `libro(isbn)`: clave `f"libro:{isbn}"`, TTL 60.0 s. Si el DAO no encuentra
  el ISBN, el resultado (`None`) **no se cachea** (se vuelve a consultar).
- `listar_por_autor(autor)`: clave `f"autor:{autor}"`, TTL 30.0 s. Devuelve
  siempre una **copia** de la lista de ISBNs (mutar el resultado no corrompe
  la caché). Una lista vacía sí se cachea.
- `copias_disponibles(isbn)`: clave `f"copias:{isbn}"`, TTL 60.0 s.
- `agregar_libro(libro)`: tras persistir, invalida el prefijo `"autor:"`
  (todos los listados de autores quedan obsoletos).
- `registrar_prestamo(id_prestamo, isbn)`: tras persistir, invalida
  `f"libro:{isbn}"` y `f"copias:{isbn}"`. No debe tocar claves de otros ISBN.
- `devolver_prestamo(id_prestamo)`: el DAO devuelve el ISBN prestado; tras
  persistir, invalida `f"copias:{isbn}"`.
- `actualizar_copias(isbn, delta)`: tras persistir, invalida
  `f"libro:{isbn}"` y `f"copias:{isbn}"`.
- El servicio devuelve siempre datos de `modelos.Libro` (inmutables) o copias
  de listas: el caché nunca debe permitir que un caller corrompa el estado.

## Restricciones

- Solo puedes cambiar/crear `catalogo/cache.py` (y, si lo necesitas, tests
  tuyos). El resto del paquete es intocable.
- Sin red, sin fechas reales, sin aleatoriedad: todo debe ser determinista.
- Compatible con Python 3.12 y el código actual del paquete (estilo en
  español, type hints, dataclasses).

---

## PARTE B

# Tarea: parser de un mini-DSL con mensajes de error exactos

## Rol

Eres ingeniero de un equipo que usa un mini-lenguaje de expresiones
(`mini_dsl`) para plantillas y reglas de negocio. El paquete ya existe de
forma preliminar pero sus mensajes de error y su cobertura semántica no
responden al contrato que consumen las herramientas internas (formateadores,
IDE, validadores). Debes completarlo.

## Requisito

Implementa el paquete `mini_dsl` (módulos `errores.py`, `tokens.py`,
`lexer.py`, `nodos.py`, `parser.py`, `evaluador.py`) para que cumpla
**exactamente** el contrato siguiente. Las firmas, los tipos de token, el
formato literal de los mensajes de error (incluidas posición línea:columna y
cada motivo) y la semántica de evaluación son parte del contrato: los
consumidores comparan los mensajes carácter a carácter.

## API pública

```python
from mini_dsl import tokenizar, parsear, ejecutar, ErrorDeSintaxis, Token
```

- `tokenizar(texto: str) -> list[Token]`
- `parsear(texto: str) -> Programa` (dataclass con campo `sentencias`, tupla
  de sentencias en orden)
- `ejecutar(texto: str) -> list[Any]` — parsea y evalúa con un entorno nuevo
  por llamada; devuelve un elemento por sentencia en orden: `None` para
  `let`, el valor de la expresión para expresiones sueltas.
- Todo error (léxico o sintáctico o de evaluación semántica del contrato)
  se lanza como `ErrorDeSintaxis` (definida en `mini_dsl.errores`, subclase
  de `Exception`) con el mensaje exacto descrito más abajo. No se lanzan
  `SyntaxError`, `ZeroDivisionError` ni otras excepciones ante entradas
  válidas o inválidas del DSL.

## Tokens

`Token` es un dataclass con campos `tipo: str`, `lexema: str`,
`linea: int`, `columna: int`. Línea y columna son 1-based; la columna es la
del primer carácter del token. Tipos exactos:

| tipo | lexemas |
|---|---|
| `NUM` | enteros `12` y decimales `3.5` (un solo punto) |
| `CADENA` | literales entre comillas dobles (ver escapes) |
| `IDENT` | `[A-Za-z_][A-Za-z0-9_]*` que no sea palabra clave |
| `PALABRA` | `let`, `si`, `entonces`, `sino`, `verdadero`, `falso` |
| `OP` | `==`, `!=`, `<=`, `>=`, `<`, `>`, `+`, `-`, `*`, `/`, `(`, `)`, `=` |
| `NL` | un salto de línea (`lexema` `"\n"`) |

Reglas del lexer:

- Espacios y tabs se ignoran. `#` inicia un comentario que llega hasta (sin
  incluir) el salto de línea; el salto de línea se emite como `NL`.
- Los `NL` consecutivos se emiten todos (el parser los trata como
  separadores); líneas en blanco y solo-comentarios son inocuas.
- Números: se toma la secuencia completa de caracteres `[0-9A-Za-z_.]*`
  empezando por un dígito. Si la secuencia completa no es un número válido
  (entero o decimal con un solo punto), se lanza
  `numero mal formado: {secuencia}` en la posición del primer dígito.
  Ejemplos: `12abc`, `1.2.3`, `1_0`.
- Cadenas: desde la comilla de apertura hasta la comilla de cierre, sin
  salto de línea dentro. El `lexema` del token `CADENA` es el texto crudo
  entre las comillas (sin las comillas y **sin decodificar** los escapes; el
  evaluador los decodifica). Escapes válidos: `\"` (comilla) y `\\`
  (barra invertida). Cualquier otra `\x` lanza `escape invalido: \x` en la
  posición de la **barra**. Si aparece fin de texto o salto de línea antes
  de cerrar: `cadena sin cerrar` en la posición de la **comilla de
  apertura**.
- Carácter no reconocido: `token inesperado: {repr}` (repr de Python del
  carácter, p. ej. `'@'`) en su posición.

## Gramática

```
programa  := (sentencia NL)* sentencia? (NL)*
sentencia := "let" IDENT "=" expr | expr
expr      := "si" expr "entonces" expr "sino" expr | comp
comp      := suma (op_comp suma)?
op_comp   := "==" | "!=" | "<" | "<=" | ">" | ">="
suma      := producto (("+" | "-") producto)*
producto  := primario (("*" | "/") primario)*
primario  := NUM | CADENA | "verdadero" | "falso" | IDENT
           | "(" expr ")"
```

- Cada sentencia debe terminar en `NL` o en fin de texto; si tras una
  sentencia viene otro token: `se esperaba fin de línea pero llegó {repr}`.
- Donde se espera un valor y aparece un salto de línea se usa el motivo
  `se esperaba un valor pero llegó '\n'`; para cualquier otro token que no
  puede iniciar un valor (p. ej. una palabra clave como `'si'` o `'entonces'`,
  un operador o el cierre `)`) se usa `token inesperado: {repr}`.
- `si ... entonces ... sino ...` es una construcción a nivel de expresión
  completa: no puede aparecer tras un operador sin paréntesis (p. ej.
  `1 + si verdadero entonces 2 sino 3` es error). Dentro de ramas o
  paréntesis se anida libremente.
- Todas las operaciones binarias son asociativas por la izquierda.
  Precedencia: `*` `/` > `+` `-` > comparaciones > `si`.

## Profundidad

Cada paréntesis de agrupación que se abre y cada construcción `si` que se
abre suma 1 al anidamiento. El máximo simultáneo permitido es **32**. Al
abrir el nivel 33 se lanza `profundidad maxima excedida (maxima: 32)` en la
posición del token que abre (`(` o `si`). 32 niveles exactos es válido.

## Posición del fin de entrada

Cuando un error ocurre porque llegó el fin del texto, la posición reportada
es el cursor inmediatamente después del **último token emitido**: si el
último token es un `NL`, `linea = token.linea + 1` y `columna = 1`; si no,
`linea = token.linea` y `columna = token.columna + len(token.lexema)`; si el
texto no produce tokens, `(1, 1)`.

## Mensajes de error (formato exacto)

Todo mensaje tiene la forma:

```
error(L{linea},C{columna}): {motivo}
```

Motivos exactos (literales; `{x}` es sustitución):

1. `token inesperado: {repr}` — carácter/lexema que no puede aparecer ahí
   (p. ej. `token inesperado: '@'`, `token inesperado: 'entonces'`).
2. `se esperaba un valor pero llegó fin de entrada`
3. `se esperaba un valor pero llegó {repr}`
4. `se esperaba ) pero llegó fin de entrada`
5. `se esperaba ) pero llegó {repr}`
6. `se esperaba un identificador pero llegó {repr}`
7. `se esperaba el operador '=' pero llegó {repr}`
8. `se esperaba una palabra clave 'entonces' pero llegó {repr|fin de entrada}`
9. `se esperaba una palabra clave 'sino' pero llegó {repr|fin de entrada}`
10. `se esperaba fin de línea pero llegó {repr}`
11. `cadena sin cerrar`
12. `escape invalido: \x` (barra + el carácter inválido)
13. `numero mal formado: {secuencia}`
14. `profundidad maxima excedida (maxima: 32)`
15. `identificador reservado: {nombre}` — donde se espera un `IDENT` y
    llega una `PALABRA` (p. ej. `let si = 1`). La posición es la de la
    palabra.
16. `tipo invalido para operador {op}: {t_izq} {op} {t_der}` — tipos:
    `numero`, `cadena`, `booleano` (p. ej.
    `tipo invalido para operador +: cadena + numero`).
17. `division entre cero`
18. `variable no definida: {nombre}` — posición del identificador.
19. `variable redefinida: {nombre}` — un `let` no puede redefinir; posición
    del identificador.
20. `la condicion de 'si' debe ser booleana, es {tipo}` — posición del
    token `si`.

En los motivos 3-10, cuando el problema es el fin de entrada se usa
literalmente la frase `fin de entrada` en lugar del `{repr}`. `{repr}` es
siempre `repr()` de Python del lexema (p. ej. `'2'`, `'\n'`).

## Semántica de evaluación

- Tipos de valor: `int`/`float` → `numero`, `str` → `cadena`,
  `bool` → `booleano` (¡los bool se comprueban antes que los enteros: un
  `bool` NO es un `numero` en este DSL!).
- `NUM` entero evalúa a `int`; con punto, a `float`. `a / b` siempre
  devuelve `float`. Divisor `0` (int o float) → `division entre cero` en la
  posición del operador `/`.
- `+`: `numero + numero` (suma) o `cadena + cadena` (concatenación);
  cualquier mezcla → error de tipo.
- `-` y `*`: solo `numero`.
- Comparaciones `==`, `!=`, `<`, `<=`, `>`, `>=`: ambos operandos deben ser
  del **mismo tipo** (numero/numero, cadena/cadena, booleano/booleano);
  mezclar tipos es error de tipo en la posición del operador. Entre
  cadenas, el orden es lexicográfico. Entre booleanos, `False < True`.
- `==` y `!=` comparan con igualdad de Python dentro del mismo tipo.
- `si c entonces a sino b`: se evalúa `c`; si no es `booleano` → error en la
  posición del `si`; si es `True` se evalúa y devuelve solo `a`; si `False`,
  solo `b` (evaluación perezosa: la rama no tomada **no** se evalúa, p. ej.
  `si verdadero entonces 1 sino (1 / 0)` devuelve `1`).
- `let x = e`: evalúa `e` y define `x` en el entorno de la ejecución; si
  `x` ya estaba definida → `variable redefinida: x`. El entorno no persiste
  entre llamadas a `ejecutar`.
- El valor de una expresión puede ser de cualquier tipo; no hay
  coerción implícita entre tipos.

## Restricciones

- No toques nada fuera del paquete `mini_dsl` y tus tests.
- Determinista: sin red, sin reloj real, sin aleatoriedad.
- Python 3.12, estilo del repo: type hints, dataclasses, identificadores en
  español.
