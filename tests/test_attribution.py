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


# --- P4: numeros tecnicos y ficheros (el verificador original no los miraba) ---

def test_caza_numero_tecnico_inventado():
    """λ_t = 0.125 sin estar en el chunk: fabricacion, y el modulo no la cazaba."""
    bp = "Segun el paper, l_t = 0.125 si nunca se resuelve. [doc:1:0]"
    v = A.check_attributions(bp, {(1, 0): "variance-weighted selection over episodes."})
    assert v and v[0]["tipo"] == "termino_ausente"
    assert v[0]["termino"] == "0.125"


def test_no_acusa_numero_que_si_esta_en_el_chunk():
    """El caso real del juez: 0.125 esta en doc3 chunk43 y aun asi lo acuso."""
    chunk = "Weight floor for tasks never solved so far: 0.125. Lambda 0.025."
    bp = "Segun el paper, weight floor = 0.125. [doc:1:0]"
    assert A.check_attributions(bp, {(1, 0): chunk}) == []


def test_caza_fichero_inventado():
    bp = "El objetivo se carga de goal.yaml y metric.yaml. [doc:1:0]"
    v = A.check_attributions(bp, {(1, 0): "the agent re-renders the objective each turn."})
    assert v and any(x["termino"] == "goal.yaml" for x in v)


def test_no_acusa_fichero_que_si_esta():
    chunk = "All lessons are written to lessons.md after each run."
    bp = "Las lecciones se guardan en lessons.md. [doc:1:0]"
    assert A.check_attributions(bp, {(1, 0): chunk}) == []


def test_no_acusa_enteros_pequenos_de_estructura():
    """Un '3 intentos' de disenno propio no es una atribucion tecnica."""
    bp = "Reintenta hasta 3 veces antes de abortar. [doc:1:0]"
    assert A.check_attributions(bp, {(1, 0): "retry the verification step."}) == []


def test_frase_de_propuesta_sin_puntero_no_se_verifica():
    """R1 como suelo: sin puntero no hay atribucion que comprobar, porque no
    se le esta atribuyendo nada a la fuente. Es lo que R6 exige y R1 ampara."""
    bp = "- **Modulo X**: hace Y\n  *(propuesta del blueprint)*"
    assert A.check_attributions(bp, {}) == []


# --- Hito 5: huérfanas (modo A del hallazgo 26) ------------------------------
#
# `check_attributions` solo mira frases con puntero; ReASearch salió
# `verificado=True` con 2/2 resueltas y el juez lo suspendió por inventar
# módulos anclados sin `[doc:id:chunk]`. Estos tests defienden el complemento:
# caza lo que va sin puntero y sin marca R6, y no acusa a lo honesto.

def test_huerfana_sin_puntero_ni_marca():
    bp = "El AdaptiveHarnessExecutionEngine orquesta la ejecución de pasos."
    v = A.check_orphan_claims(bp)
    assert v and v[0]["tipo"] == "huerfana"
    assert v[0]["termino"] == "AdaptiveHarnessExecutionEngine"


def test_huerfana_con_puntero_no_cuenta():
    """Con ancla ya la mira `check_attributions`; aquí no debe duplicar."""
    bp = "El AdaptiveHarnessExecutionEngine orquesta pasos. [doc:1:0]"
    assert A.check_orphan_claims(bp) == []


def test_huerfana_con_marca_r6_no_cuenta():
    """R6 en la propia línea: la afirmación está declarada como propuesta."""
    bp = "El FailureVsSuccessRefiner refina el bucle (propuesta del blueprint)."
    assert A.check_orphan_claims(bp) == []


def test_huerfana_con_marca_en_linea_siguiente_no_cuenta():
    """R6 permite la marca en la línea inmediatamente debajo del punto."""
    bp = "- **Módulo X**: hace Y\n  *(propuesta del blueprint)*"
    assert A.check_orphan_claims(bp) == []


def test_huerfana_declaracion_de_silencio_no_cuenta():
    """Con término técnico presente, pero declarado como silencio (R5/R6):
    la marca es lo que la salva — ese es el caso en que importa."""
    bp = "El paper no especifica el umbral de gating (0.30)."
    assert A.check_orphan_claims(bp) == []


def test_linea_comun_sin_terminos_no_es_huerfana():
    """Sin término técnico no hay nada técnico que atribuir: no se acusa."""
    assert A.check_orphan_claims("El agente valida cada paso antes de cerrar.") == []


def test_encabezado_con_termino_no_es_huerfana():
    assert A.check_orphan_claims("## Módulos AdaptiveHarnessEngine") == []


def test_huerfana_caza_numero_tecnico_suelto():
    bp = "El gate cierra con 0.30 cuando la cobertura baja."
    v = A.check_orphan_claims(bp)
    assert v and "0.30" in v[0]["terminos"]


def test_huerfana_solo_las_lineas_que_tocan():
    """Selección por línea: señala la huérfana y deja limpias las de al lado."""
    bp = ("El agente valida cada paso antes de cerrar.\n"
          "El FailureVsSuccessRefiner refina el bucle.\n"
          "## Validación\n"
          "El umbral es 0.30. [doc:1:0]\n"
          "Otra cosa sin términos.")
    v = A.check_orphan_claims(bp)
    assert len(v) == 1
    assert v[0]["linea"] == 2
    assert v[0]["termino"] == "FailureVsSuccessRefiner"


# ------------------------------------------------------------ ruta 5 (§5.10)
#
# P3 destruyó el documento reescribiéndolo (§5.8.3). La garantía que estos
# tests defienden es la opuesta: **ruta 5 solo toca punteros y marcas, nunca
# la frase.** Si alguno falla, la vía ya no es segura.

BP = "El sistema usa variance-weighted task selection para muestrear. [doc:1:0]\n" \
     "El umbral de gating es 0.125. [doc:1:5]"


def test_demote_quita_puntero_y_marca_sin_tocar_prosa():
    from bibliotecario.agent.attribution import demote_unsupported
    v = [{"tipo": "no_sostenida", "chunk": "1:0", "pos": BP.index("[doc:1:0]"),
          "frase": "x"}]
    out, marks = demote_unsupported(BP, v)
    assert marks == {"no_sostenida": 1, "puntero_roto": 0}
    assert "(propuesta del blueprint)" in out
    assert "[doc:1:0]" not in out
    assert "[doc:1:5]" in out                      # el otro queda intacto
    assert "variance-weighted task selection" in out  # la frase no se toca


def test_demote_puntero_roto_se_quita_sin_marca():
    """Un puntero a un chunk inexistente no se marca: se borra. No hay fuente
    a la que degradar, solo una afirmación que fingía tenerla."""
    from bibliotecario.agent.attribution import demote_unsupported
    v = [{"tipo": "puntero_roto", "chunk": "1:5", "pos": BP.index("[doc:1:5]"),
          "frase": "y"}]
    out, marks = demote_unsupported(BP, v)
    assert marks == {"no_sostenida": 0, "puntero_roto": 1}
    assert "[doc:1:5]" not in out
    assert "0.125" in out


def test_demote_no_cambia_la_prosa():
    """Garantía central de §5.10.3. Quitando punteros y marcas, el texto debe
    ser byte a byte el mismo — es lo que distingue esto de P3."""
    import re

    from bibliotecario.agent.attribution import demote_unsupported
    v = [{"tipo": "no_sostenida", "chunk": "1:0", "pos": BP.index("[doc:1:0]")},
         {"tipo": "puntero_roto", "chunk": "1:5", "pos": BP.index("[doc:1:5]")}]
    out, _ = demote_unsupported(BP, v)
    limpia = lambda t: re.sub(r"\s*\[doc:\d+:\d+\]|\s*\(propuesta del blueprint\)", "", t)
    assert limpia(out) == limpia(BP)


def test_demote_offsets_de_atras_adelante():
    """Dos degradaciones seguidas: la segunda no se puede perder por moverse la
    primera. Se procesa de atrás adelante por eso."""
    from bibliotecario.agent.attribution import demote_unsupported
    v = [{"tipo": "no_sostenida", "chunk": "1:0", "pos": BP.index("[doc:1:0]")},
         {"tipo": "no_sostenida", "chunk": "1:5", "pos": BP.index("[doc:1:5]")}]
    out, marks = demote_unsupported(BP, v)
    assert marks["no_sostenida"] == 2
    assert "[doc:" not in out
    assert out.count("(propuesta del blueprint)") == 2


def test_critic_claim_no_confunde_fallo_de_llamada_con_fabricacion():
    """Errata corregida 2026-10-12: una respuesta vacía del proveedor se
    trataba como 'SIN_FUENTE' y contaba como violación del modelo. Un fallo del
    juez no es una mentira del modelo."""

    import bibliotecario.core.llm as L
    from bibliotecario.agent import attribution as A

    old = L.generate
    try:
        L.generate = lambda *a, **k: ""
        assert A.critic_claim("frase", "chunk") == "FALLO"
        L.generate = lambda *a, **k: "NO_SOSTIENE"
        assert A.critic_claim("frase", "chunk") == "NO_SOSTIENE"
        L.generate = lambda *a, **k: "SOSTIENE"
        assert A.critic_claim("frase", "chunk") == "SOSTIENE"
        L.generate = lambda *a, **k: "  no_sostiene  "
        assert A.critic_claim("frase", "chunk") == "NO_SOSTIENE"
    finally:
        L.generate = old


def test_critic_sin_chunk_es_fallo_no_violacion():
    from bibliotecario.agent import attribution as A
    from bibliotecario.core import llm as L
    old = L.generate
    try:
        L.generate = lambda *a, **k: "SOSTIENE"
        r = A.critic_attributions("Algo. [doc:1:0]", {})
    finally:
        L.generate = old
    # sin chunk cargado el prompt sale vacio -> SOSTIENE; pero si el juez
    # falla, tiene que ir a fallos y no a violaciones
    assert set(r) == {"violaciones", "fallos"}


def test_critic_and_demote_marca_reescrito_false():
    """La señal que distingue ruta 5 de P3: jamás reescribe."""
    from bibliotecario.agent import attribution as A
    viejo = A.critic_claim
    A.critic_claim = lambda s, c, **k: "NO_SOSTIENE"
    try:
        r = A.critic_and_demote(BP, {(1, 0): "x", (1, 5): "y"})
    finally:
        A.critic_claim = viejo
    assert r["reescrito"] is False
    assert r["degradadas"] == 2
    assert "(propuesta del blueprint)" in r["blueprint"]


def test_normalize_pointers_formatos_malos_del_brazo_E():
    """Medido en §7.1: 48 de 197 punteros del brazo E salían como
    [doc:5:chunk:13] y no resolvían nunca."""
    from bibliotecario.knowledge.study import normalize_pointers
    cases = [
        ("x [doc:5:chunk:13]", "x [doc:5:13]"),
        ("x [doc3:14]", "x [doc:3:14]"),
        ("x [doc:7:chunk 8]", "x [doc:7:8]"),
        ("x [doc:2:41]", "x [doc:2:41]"),        # ya canónico: no se toca
        ("x (doc6: chunk 0)", "x (doc6: chunk 0)"),  # prosa, no puntero
        ("x [doc:id:chunk]", "x [doc:id:chunk]"),    # plantilla sin numeros
    ]
    for inp, esperado in cases:
        out, _ = normalize_pointers(inp)
        assert out == esperado, (inp, out)


def test_normalize_pointers_cuenta_los_arreglados():
    from bibliotecario.knowledge.study import normalize_pointers
    out, n = normalize_pointers("a [doc:1:chunk:2] b [doc3:4]")
    assert n == 2
    assert out == "a [doc:1:2] b [doc:3:4]"
