"""Validador de esquemas JSON-like con paths de error exactos."""
from jsonval.paths import index, key
from jsonval.types import KNOWN_TYPES, matches, type_name
from jsonval.validator import validate

__all__ = ["KNOWN_TYPES", "index", "key", "matches", "type_name", "validate"]
