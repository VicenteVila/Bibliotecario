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


# --- Hito 6: reparación que no degenere (HITO6 §1) ----------------------------
#
# El intento 2 logró R4+R5 pagando con el documento: PG a 488 chars y
# ReASearch a 440 (razonamiento suelto del modelo) pasaron el juez. Estos
# tests defienden lo que el runner de H13 exige ANTES de aceptar cualquier
# borrador: lo determinista primero (sin LLM, sin reescribir prosa) y la
# validación V1/V2 que rechaza la degradación.

def test_check_attributions_incluye_pos_para_demotear():
    """Hito 6: `pos` es lo que permite demotear in-place desde el informe."""
    bp = "Según el paper, usa AdaptiveHarnessEngine para orquestar. [doc:1:0]"
    v = A.check_attributions(bp, {(1, 0): CHUNK})
    assert v and v[0]["pos"] == bp.index("[doc:1:0]")


def test_mech_repair_normaliza_y_rescata_cita():
    """[doc:1:chunk:0] es invisible para todo el sistema (§7.1): normalizarlo
    la hace resoluble sin tocar la frase — el puntero NO se quita."""
    bp = "Aplica variance-weighted task selection. [doc:1:chunk:0]"
    out, stats = A.mech_repair(bp, {(1, 0): CHUNK})
    assert "[doc:1:0]" in out
    assert stats["normalizados"] == 1
    assert stats["punteros_quitados"] == 0
    assert "variance-weighted task selection" in out


def test_mech_repair_quita_puntero_roto_y_marca_huerfana():
    bp = ("Según el paper, usa variance-weighted task selection. [doc:1:9]\n"
          "El AdaptiveHarnessEngine orquesta los pasos.")
    out, stats = A.mech_repair(bp, {(1, 0): CHUNK})
    assert "[doc:1:9]" not in out
    assert stats["punteros_quitados"] == 1
    assert "variance-weighted task selection" in out     # prosa intacta
    assert ("El AdaptiveHarnessEngine orquesta los pasos. "
            "(propuesta del blueprint)") in out          # marca R6 en su línea
    assert stats["huerfanas_marcadas"] == 1
    assert A.check_orphan_claims(out) == []


def test_mech_repair_marca_termino_ausente():
    bp = "Según el paper, usa AdaptiveHarnessEngine. [doc:1:0]"
    out, stats = A.mech_repair(bp, {(1, 0): CHUNK})
    assert stats["marcados_termino"] == 1
    assert "[doc:1:0]" not in out
    assert "usa AdaptiveHarnessEngine. " in out   # prosa intacta
    assert "(propuesta del blueprint)" in out


def test_mech_repair_no_toca_lo_correcto():
    """Passthrough: con todo correcto, byte a byte idéntico."""
    bp = "Aplica variance-weighted task selection. [doc:1:0]\n\n## Validación"
    out, stats = A.mech_repair(bp, {(1, 0): CHUNK})
    assert out == bp
    assert stats == {"normalizados": 0, "violaciones": 0,
                     "punteros_quitados": 0, "marcados_termino": 0,
                     "huerfanas_marcadas": 0}


def test_validate_structure_v1_caza_el_stub():
    """El caso real de H12: 440 chars sobre una base de 5196."""
    fallos = A.validate_structure("B" * 5196, "B" * 440)
    assert fallos and fallos[0].startswith("V1")
    assert "440" in fallos[0] and "2598" in fallos[0]


def test_validate_structure_v1_vacio_y_emergencia():
    assert A.validate_structure("x", "") == ["V1: la salida está vacía"]
    fallos = A.validate_structure("x" * 100, "(" + ")" * 99)
    assert any("emergencia" in f for f in fallos)


def test_validate_structure_v2_renombrar_encabezado_es_fallo():
    """Igualdad literal (mismo criterio que G2): renombrar = falla."""
    base = "## Bibliografía\n" + "x" * 500
    draft = "## Bibliografía renovada\n" + "x" * 500
    fallos = A.validate_structure(base, draft)
    assert any(f.startswith("V2") and "Bibliografía" in f for f in fallos)


def test_validate_structure_acepta_al_bueno():
    base = "## Título\n" + "x" * 1000
    draft = "## Título\n" + "x" * 1200
    assert A.validate_structure(base, draft) == []


def test_encabezados_misma_definicion_que_g2():
    """Solo `## ` con espacio: `#` y `###` fuera, como en G2 desde HITO5."""
    assert A.encabezados("# Uno\n## Dos\n### Tres\n## Cuatro") == ["Dos", "Cuatro"]


# --- Hito 7: localizador guiado + marcado (HITO7 §1) ---------------------------
#
# Sonda previa: la localización literal frase↔línea no es viable (LCS 8–27
# chars). Estos tests defienden el contrato del localizador: solo devuelve
# números con eco verificable, y la edición es append de marca sobre línea.

BP7 = ("# Título del blueprint\n"
       "El sistema usa variance-weighted task selection. [doc:1:0]\n"
       "El módulo AdaptiveHarnessEngine orquesta los pasos.\n"
       "\n"
       "## Bibliografía\n")

ECO2 = "El sistema usa variance-weighted task selection"


def test_localizador_prompt_numerado_y_formato():
    p = A.localizador_prompt(["Frase fabricada"], BP7)
    assert "[1] Frase fabricada" in p
    assert "1| # Título del blueprint" in p
    assert "5| ## Bibliografía" in p
    assert "N -> M | eco" in p or "<número de frase> -> <número de línea>" in p
    assert "no reescribas nada" in p


def test_parse_localizador_entrada_valida():
    r = A.parse_localizador(f"1 -> 2 | {ECO2}", BP7, 1)
    assert r["validas"] == [2]
    assert r["lineas"] == {1: 2}
    assert r["invalidas"] == []
    assert r["no_localizadas"] == []


def test_parse_localizador_guion_no_localiza_no_invalida():
    r = A.parse_localizador("1 -> -", BP7, 1)
    assert r["validas"] == []
    assert r["no_localizadas"] == [1]
    assert r["invalidas"] == []


def test_parse_localizador_rechaza_fuera_de_rango_y_encabezado():
    r = A.parse_localizador(
        "1 -> 99 | " + ECO2 + "\n"
        "2 -> 1 | " + ECO2 + "\n"
        "3 -> 999 | " + ECO2,
        BP7, 3)
    assert r["validas"] == []
    assert any("fuera de rango" in x for x in r["invalidas"])
    assert any("encabezado" in x for x in r["invalidas"])


def test_parse_localizador_rechaza_eco_malo():
    r = A.parse_localizador(
        "1 -> 2 | esto no esta en la linea de ejemplo no\n"
        "2 -> 3 | El m",  # eco demasiado corto
        BP7, 2)
    assert r["validas"] == []
    assert any("eco no aparece" in x for x in r["invalidas"])
    assert any("eco demasiado corto" in x for x in r["invalidas"])


def test_parse_localizador_sin_entradas_es_invalido():
    r = A.parse_localizador("prosa suelta sin formato", BP7, 1)
    assert r["validas"] == []
    assert any("parseables" in x for x in r["invalidas"])


def test_parse_localizador_correccion_no_queda_bloqueada():
    """Una entrada inválida no tapa la corrección posterior de la misma frase."""
    r = A.parse_localizador(
        f"1 -> 1 | {'x' * 30}\n"        # encabezado: inválida
        f"1 -> 2 | {ECO2}",             # corrección de la misma frase
        BP7, 1)
    assert r["validas"] == [2]


def test_localizador_reintento_lleva_los_fallos():
    p = A.localizador_reintento("BASE", ["frase 1: el eco no aparece"])
    assert p.startswith("BASE")
    assert "frase 1: el eco no aparece" in p


def test_marcar_lineas_marca_sin_tocar_prosa():
    out, stats = A.marcar_lineas(BP7, [2, 3])
    assert stats == {"marcadas": 2, "omitidas": 0}
    assert "selection. [doc:1:0] (propuesta del blueprint)\n" in out
    assert "pasos. (propuesta del blueprint)\n" in out
    assert out.splitlines()[0] == "# Título del blueprint"  # encabezado intacto
    import re as _re
    limpia = _re.sub(r"\s*\(propuesta del blueprint\)", "", out)
    assert limpia == BP7


def test_marcar_lineas_omite_encabezado_vacio_y_repetido():
    out, stats = A.marcar_lineas(BP7, [1, 4, 2, 2, 99])
    assert stats == {"marcadas": 1, "omitidas": 3}
    assert out.splitlines()[0] == "# Título del blueprint"


def test_marcar_lineas_no_duplica_si_ya_marcada():
    bp_m, _ = A.marcar_lineas(BP7, [3])
    out, stats = A.marcar_lineas(bp_m, [3])
    assert stats == {"marcadas": 0, "omitidas": 1}
    assert out == bp_m


# --- Hito 8: edición dirigida de cuerpo, máscara fija (HITO8 §1) --------------
#
# HITO7 midió que la marca R6 no gira el veredicto: aquí la afirmación citada
# sale del texto (plantilla fija + punteros conservados, 0 generación).

BP8 = ("# Título\n"
       "Intro con [doc:1:0] y texto. [doc:2:1]\n"
       "\n"
       "## Sección A\n"
       "Cuerpo A1 con [doc:3:0] puntero.\n"
       "Cuerpo A2 fabricado sin puntero.\n"
       "\n"
       "## Sección B\n"
       "Cuerpo B1 sin puntero.\n")


def test_mascarar_lineas_reemplaza_y_conserva_punteros():
    out, stats = A.mascarar_lineas(BP8, [2])
    assert stats["mascaradas"] == 1
    L = out.splitlines()
    assert L[1] == A.MASCARA + " [doc:1:0] [doc:2:1]"
    assert L[0] == "# Título"
    assert "Cuerpo A1" in out and "Cuerpo B1" in out
    assert out.splitlines(keepends=True)[1].endswith("\n")


def test_mascarar_lineas_omite_encabezado_vacio_rango_y_repetido():
    _, stats = A.mascarar_lineas(BP8, [1, 3, 99, 2, 2])
    assert stats == {"mascaradas": 1, "secciones": 0,
                     "lineas_vaciadas": 0, "omitidas": 3}


def test_mascara_seccion_vacia_cuerpo_e_intacta_encabezado():
    out, stats = A.mascara_seccion(BP8, 4)
    assert stats["secciones"] == 1
    assert stats["lineas_vaciadas"] == 3
    L = out.splitlines()
    assert L[3] == "## Sección A"          # encabezado byte a byte
    assert A.MASCARA in L[4] and "[doc:3:0]" in L[4]
    assert "Cuerpo A1" not in out and "Cuerpo A2" not in out
    assert "## Sección B" in out and "Cuerpo B1" in out


def test_mascara_seccion_idempotente_y_sin_encabezado():
    out1, _ = A.mascara_seccion(BP8, 4)
    out2, stats = A.mascara_seccion(out1, 4)
    assert out2 == out1 and stats == {"mascaradas": 0, "secciones": 0,
                                      "lineas_vaciadas": 0, "omitidas": 1}
    out3, stats3 = A.mascara_seccion(BP8, 99)
    assert out3 == BP8 and stats3["omitidas"] == 1


def test_editar_m5_combo_mascara_y_seccion_en_un_solo_pas():
    out, stats = A.editar_m5(BP8, [9], [4])
    assert stats["mascaradas"] == 1 and stats["secciones"] == 1
    L = out.splitlines()
    assert L[3] == "## Sección A"
    assert L[-1].startswith(A.MASCARA)          # línea 9 (tras vaciar A)
    assert "Cuerpo B1" not in out
    assert "Intro con [doc:1:0] y texto." in out  # línea 2 intacta


def test_parse_flechas_unicode_y_viñetas_se_normalizan():
    r = A.parse_localizador(f"1 → 2 | {ECO2}", BP7, 1)
    assert r["validas"] == [2]
    r2 = A.parse_localizador("- 1 -> 3 | El módulo AdaptiveHarnessEngine",
                             BP7, 1)
    assert r2["validas"] == [3]


def test_parse_frase_sin_entrada_se_acredita():
    r = A.parse_localizador(f"1 -> 2 | {ECO2}", BP7, 2)
    assert r["validas"] == [2]
    assert any("frase 2: sin entrada en la salida" in x
               for x in r["invalidas"])


def test_parse_encabezados_alimenta_a_m5b():
    r = A.parse_localizador("1 -> 4 | Sección A", BP8, 1)
    assert r["validas"] == []
    assert r["encabezados"] == [4]
    assert any("encabezado" in x for x in r["invalidas"])
    out, stats = A.mascara_seccion(BP8, r["encabezados"][0])
    assert stats["secciones"] == 1
    assert "## Sección A" in out and "Cuerpo A1" not in out
