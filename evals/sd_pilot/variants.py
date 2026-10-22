"""Variantes del H_aux (§1.2 del plan HITO19): A1-A5, parámetros congelados.

Todos los arneses comparten el MISMO modelo (§1.5): solo cambian
subsistemas (D1/D3/D4/D5/D7). Ningún parámetro se modifica tras la
ratificación (§3); cambios = enmienda declarada.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Variant:
    name: str
    one_shot: bool
    max_turns: int
    tools: bool
    use_pfs: bool
    use_skills: bool
    use_regulation: bool
    error_digest: bool
    max_tokens: int

    @property
    def subsystems(self) -> dict:
        return {
            "D1_bucle": "one_shot" if self.one_shot else f"loop<{self.max_turns}>",
            "D3_tools": self.tools,
            "D4_memoria_digest": self.error_digest,
            "D5_validacion_pfs": self.use_pfs,
            "D6_orquestacion": False,
            "D7_skills": self.use_skills,
            "regulacion": self.use_regulation,
        }


VARIANT_NAMES = ("A1", "A2", "A3", "A4", "A5")

VARIANTS: dict[str, Variant] = {
    "A1": Variant("A1", one_shot=True, max_turns=1, tools=False, use_pfs=False,
                  use_skills=False, use_regulation=False, error_digest=False,
                  max_tokens=8192),
    "A2": Variant("A2", one_shot=False, max_turns=16, tools=True, use_pfs=False,
                  use_skills=False, use_regulation=False, error_digest=False,
                  max_tokens=4096),
    "A3": Variant("A3", one_shot=False, max_turns=16, tools=True, use_pfs=True,
                  use_skills=False, use_regulation=False, error_digest=False,
                  max_tokens=4096),
    "A4": Variant("A4", one_shot=False, max_turns=16, tools=True, use_pfs=True,
                  use_skills=True, use_regulation=False, error_digest=False,
                  max_tokens=4096),
    "A5": Variant("A5", one_shot=False, max_turns=16, tools=True, use_pfs=True,
                  use_skills=True, use_regulation=True, error_digest=True,
                  max_tokens=4096),
}
