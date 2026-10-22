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
