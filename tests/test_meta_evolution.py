"""Hito 4 — meta-evolución: el ciclo completo, con el loop real y 0 tokens.

Regresión del hallazgo 4: `evolve_from_failures` no tenía callers y los
contadores skills / memory_items / harness_edits estaban a cero. Aquí se
cubre el ciclo declarado en evals/HITO4_PLAN.md — R1 cuenta sin evolucionar,
R2 evoluciona, R3 usa lo evolucionado en proceso, R4 lo rehidrata tras un
reinicio y R5 (limpia) no dispara nada — con runs guionizadas: harness, PFs,
estado y base de datos son los reales, solo se controla la entrada del LLM.
"""
from __future__ import annotations

import json

from bibliotecario.agent import loop as LOOP
from bibliotecario.core import storage
from bibliotecario.harness import pfs as PFS
from bibliotecario.harness import runtime as RT
from bibliotecario.harness.edits import MIN_RUNS, normalize_signature

_TOOL_OK = '```json\n{"tool": "get_status", "args": {}}\n```'
_TOOL_MALA = '```json\n{"tool": "no_existe", "args": {}}\n```'
_CIERRE = "Respuesta final [1:0]."
_SCRIPT_ERROR = [_TOOL_MALA, _TOOL_OK, _CIERRE]
_SCRIPT_LIMPIA = [_TOOL_OK, "Todo en orden.", _CIERRE]
# parse_tool_call devuelve None para tools del catálogo inexistente, así que el
# error real de este guion es el de la rama toolish (no el de validación). La
# firma se deriva del mensaje exacto: es el que run_errors normaliza.
_MENSAJE_ERROR = ('llamada inválida: emite EXACTAMENTE '
                  '{"tool": nombre, "args": {...}} con un tool del catálogo (no sueltes args sin "tool")')
FIRMA = normalize_signature(_MENSAJE_ERROR)


def _run(script: list[str], question: str, monkeypatch) -> dict:
    cola = list(script)
    monkeypatch.setattr(LOOP, "generate",
                        lambda *a, **k: cola.pop(0) if cola else "Fin.")
    return LOOP.run(question, max_turns=4, isolated=True)


def _edits() -> list[dict]:
    with storage.get_conn() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT signature, occurrences, evolved, pf_name, pattern "
            "FROM harness_edits ORDER BY id")]


def _count(tabla: str) -> int:
    with storage.get_conn() as conn:
        return conn.execute(f"SELECT COUNT(*) c FROM {tabla}").fetchone()["c"]


def test_normalize_signature_colapsa_espacios_y_limita():
    assert normalize_signature("  a   b\t c ") == "a b c"
    assert len(normalize_signature("x" * 500)) == 120


def test_meta_evolve_sin_tabla_no_rompe(tmp_path, monkeypatch):
    """DB sin init: avisa y devuelve vacío; la run no puede caerse por esto."""
    monkeypatch.setattr(storage, "db_path", lambda: tmp_path / "sin_init.db")
    h = RT.RuntimeHarness()
    assert h.meta_evolve("q", ["firma rara"]) == []


def test_ciclo_completo_meta_evolucion(tmp_path, monkeypatch):
    """R1-R5: la cadena declarada en HITO4_PLAN §3, de punta a punta."""
    monkeypatch.setattr(storage, "db_path", lambda: tmp_path / "meta.db")
    storage.init_db(tmp_path / "meta.db")
    monkeypatch.setattr(PFS, "_registry", None)
    RT.reset_harness()

    # --- R1: primera aparición de la firma: cuenta, no evoluciona (K=2) ----
    r1 = _run(_SCRIPT_ERROR, "pregunta uno", monkeypatch)
    assert r1["meta_evolved"] == []
    filas = _edits()
    assert len(filas) == 1 and filas[0]["occurrences"] == MIN_RUNS - 1
    assert not filas[0]["evolved"]
    assert PFS.get_pf_registry().stats()["auto_evolved"] == 0
    assert _count("skills") == 0 and _count("memory_items") == 0

    # --- R2: segunda aparición: evoluciona y persiste (H5 + H7) -----------
    r2 = _run(_SCRIPT_ERROR, "pregunta dos", monkeypatch)
    eventos = r2["meta_evolved"]
    assert len(eventos) == 1, eventos
    ev = eventos[0]
    assert ev["signature"] == FIRMA
    assert ev["pf"] == "auto_pf_1" and ev["skill"] == "auto_skill_1"
    assert ev["occurrences"] == 2 and ev["intervention"] == "retry"
    stats = PFS.get_pf_registry().stats()
    assert stats["auto_evolved"] == 1
    filas = _edits()
    assert filas[0]["evolved"] == 1 and filas[0]["pf_name"] == "auto_pf_1"
    assert json.loads(filas[0]["pattern"])["field"] == "last_error"
    assert _count("skills") == 1 and _count("memory_items") == 1
    with storage.get_conn() as conn:
        nombre = conn.execute("SELECT name FROM skills").fetchone()["name"]
        contenido = conn.execute("SELECT content FROM memory_items").fetchone()["content"]
    assert nombre == "auto_skill_1" and "meta-evolución" in contenido

    # --- R3: mismo proceso: lo evolucionado se usa (H6) + hint y outcome --
    r3 = _run(_SCRIPT_ERROR, "pregunta tres", monkeypatch)
    nombres = [f["pf"] for f in r3["pf_fires"]]
    assert "auto_pf_1" in nombres, r3["pf_fires"]
    assert r3["meta_evolved"] == []  # ya evolucionada: no se repite
    harness = RT.get_harness()
    hints = harness.skill_hints("pregunta tres", FIRMA)
    assert hints and hints[0][0].name == "auto_skill_1"
    skill = hints[0][0]
    assert skill.invocation_count == 1 and skill.success_count == 1
    assert skill.success_rate == 1.0

    # --- R4: reinicio de registro y harness: se rehidrata y vuelve a usar (H8)
    monkeypatch.setattr(PFS, "_registry", None)
    RT.reset_harness()
    r4 = _run(_SCRIPT_ERROR, "pregunta cuatro", monkeypatch)
    nombres4 = [f["pf"] for f in r4["pf_fires"]]
    assert "auto_pf_1" in nombres4, r4["pf_fires"]
    reg = PFS.get_pf_registry()
    assert reg.stats()["auto_evolved"] == 1  # contador restaurado, sin reutilizar
    # la capa de skills también se recarga desde la tabla
    hints4 = RT.get_harness().skill_hints("pregunta cuatro", FIRMA)
    assert hints4 and hints4[0][0].name == "auto_skill_1"

    # --- R5: run limpia con el registro rehidratado: 0 fires de auto_pf (C1)
    monkeypatch.setattr(PFS, "_registry", None)
    RT.reset_harness()
    r5 = _run(_SCRIPT_LIMPIA, "pregunta limpia", monkeypatch)
    assert r5["pf_fires"] == [], r5["pf_fires"]
    assert r5["meta_evolved"] == []

    # el contador sigue: el próximo PF auto no reutiliza el nombre
    nombres_nuevos = PFS.get_pf_registry().evolve_from_failures(
        [{"trigger": "otro fallo", "field": "last_error", "intervention": "retry"}])
    assert nombres_nuevos == ["auto_pf_2"]
