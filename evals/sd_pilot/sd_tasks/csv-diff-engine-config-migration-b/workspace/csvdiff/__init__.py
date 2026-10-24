"""Motor de diff de tablas CSV."""
from .diff import DiffResult, diff_csv, diff_tables
from .errors import (
    CsvDiffError,
    DuplicateColumnError,
    DuplicateKeyError,
    MissingKeyColumnError,
)
from .reader import read_table
from .table import Table

__all__ = [
    "Table",
    "read_table",
    "DiffResult",
    "diff_tables",
    "diff_csv",
    "CsvDiffError",
    "DuplicateColumnError",
    "DuplicateKeyError",
    "MissingKeyColumnError",
]
