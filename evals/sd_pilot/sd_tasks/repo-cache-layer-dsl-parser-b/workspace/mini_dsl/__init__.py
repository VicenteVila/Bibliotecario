"""Mini-DSL de expresiones para plantillas y reglas de negocio.

IMPLEMENTACIÓN PRELIMINAR: cubre solo aritmética básica, identificadores y
`let`. Los mensajes de error y la semántica completa (cadenas, booleanos,
`si`, comparaciones, profundidad, ...) aún no responden al contrato.
"""

from mini_dsl.errores import ErrorDeSintaxis
from mini_dsl.evaluador import evaluar_programa
from mini_dsl.lexer import tokenizar
from mini_dsl.nodos import Programa
from mini_dsl.parser import parsear
from mini_dsl.tokens import Token

__all__ = [
    "ErrorDeSintaxis",
    "Programa",
    "Token",
    "ejecutar",
    "parsear",
    "tokenizar",
]


def ejecutar(texto: str) -> list:
    """Parsea y evalúa `texto` con un entorno nuevo. Ver TASK.md."""
    programa = parsear(texto)
    return evaluar_programa(programa)
