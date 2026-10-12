"""P3 — verificación mecánica de atribución (el brazo D del A/B).

Motivo: el A/B midió que P2+P1' arreglan la forma pero no la sustancia (11/15
blueprints del brazo C atribuían cosas que la fuente no dice). Estos tests
cuentan que el verificador caza el fallo real de H1 — un nombre de módulo
inventado — y que no acusa a lo honesto.
"""

from bibliotecario.agent import attribution as A

CHUNK = "Task-CoEvolve selects a task by variance-weighted task selection. "
CHUNK += "The variance is computed over the last k episodes."


def test_caza_modulo_inventado():
    """H1, en forma mecánica: «AdaptiveHarnessEngine» no está en el chunk."""
    bp = "Según el paper, usa AdaptiveHarnessEngine para orquestar. [doc:1:0]"
    v = A.check_attributions(bp, {(1, 0): CHUNK})
    assert v and v[0]["tipo"] == "termino_ausente"
    assert v[0]["termino"] == "AdaptiveHarnessEngine"


def test_no_acusa_a_lo_que_si_esta():
    bp = "Aplica variance-weighted task selection. [doc:1:0]"
    assert A.check_attributions(bp, {(1, 0): CHUNK}) == []


def test_castellaniza_no_es_fabricacion():
    """R2 permite español con el término técnico original entrecomillado:
    el verificador no debe acusar la traducción si el término original está."""
    bp = "Emplea «variance-weighted task selection» para elegir. [doc:1:0]"
    assert A.check_attributions(bp, {(1, 0): CHUNK}) == []


def test_puntero_roto_es_fallo_distinto():
    """B8: el puntero no resuelve. Se marca aparte, no como término ausente."""
    bp = "Según el paper, usa variance-weighted task selection. [doc:1:9]"
    v = A.check_attributions(bp, {(1, 0): CHUNK})
    assert v and v[0]["tipo"] == "puntero_roto"


def test_sin_puntero_no_se_verifica():
    """Sin `[doc:id:chunk]` no hay a qué comparar; no se inventa una acusación."""
    assert A.check_attributions("El paper propone un bucle de recompensa.", {}) == []


def test_repair_prompt_lista_las_violaciones():
    viol = [{"tipo": "termino_ausente", "chunk": "1:0", "termino": "HistoryProfiler",
             "frase": "usa HistoryProfiler [doc:1:0]"}]
    p = A._repair_prompt("bp", viol)
    assert "HistoryProfiler" in p
    assert "1:0" in p
    assert "propuesta del blueprint" in p   # R6: se puede marcar como propia
