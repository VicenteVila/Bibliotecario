"""Errores del motor de diff CSV."""


class CsvDiffError(Exception):
    """Error base de lectura de tablas."""


class DuplicateColumnError(CsvDiffError):
    """La cabecera repite el nombre de una columna."""

    def __init__(self, column: str, line: int) -> None:
        super().__init__(f"columna duplicada {column!r} en la linea {line}")
        self.column = column
        self.line = line


class MissingKeyColumnError(CsvDiffError):
    """Falta una columna clave en la cabecera."""

    def __init__(self, column: str) -> None:
        super().__init__(f"falta la columna clave {column!r}")
        self.column = column


class DuplicateKeyError(CsvDiffError):
    """Dos filas comparten la misma clave compuesta."""

    def __init__(self, key: str, line: int) -> None:
        super().__init__(f"clave duplicada {key!r} en la linea {line}")
        self.key = key
        self.line = line
